"""모델 호출 (공식 Anthropic SDK). 에이전트 흐름(LangGraph)과 분리해 두어 가짜 모델로 바꿔 끼울 수 있다.

왜 LangChain 모델 래퍼 대신 공식 SDK인가 (설계 결정 J-10):
- 생각 강도(effort), 구조화된 출력, 거절 시 대체 모델(fallbacks) 같은 최신 기능을 래퍼 지원을 기다리지 않고 바로 쓴다.
- LangGraph는 흐름 관리, LangChain은 문서 분할 부품, 모델 호출은 SDK. 각자 잘하는 일만 맡긴다.
"""
import json

import anthropic

from . import prompts
from .config import PRICE_PER_MTOK, Config, Role, api_key

# 안전 분류기가 거절하면 서버가 알아서 다른 모델로 다시 돌린다 ("default" = 거절 종류에 맞는 모델을 Anthropic이 고름).
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


class ClaudeLLM:
    def __init__(self, cfg: Config, client: anthropic.Anthropic | None = None):
        self.cfg = cfg
        self.client = client or anthropic.Anthropic(api_key=api_key())   # JOBFIT_API_KEY, 없으면 ANTHROPIC_API_KEY
        self.calls: list[dict] = []                     # 호출마다 토큰·비용 기록 (운영 시스템의 apicost 와 같은 원칙)

    # ---------- 공통 ----------
    def _record(self, role_name: str, role: Role, resp) -> None:
        u = resp.usage
        price = PRICE_PER_MTOK.get(role.model, PRICE_PER_MTOK["claude-opus-5-5"])
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
        cost = (u.input_tokens * price["input"] + u.output_tokens * price["output"]
                + cache_read * price["cache_read"] + cache_write * price["cache_write"]) / 1_000_000
        self.calls.append({"role": role_name, "model": resp.model, "input": u.input_tokens,
                           "output": u.output_tokens, "cache_read": cache_read, "cache_write": cache_write,
                           "cost_usd": round(cost, 4)})

    @staticmethod
    def _check(resp) -> None:
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            cat = getattr(details, "category", None) if details else None
            raise LLMError(f"모델이 요청을 거절함 (분류: {cat})")
        if resp.stop_reason == "max_tokens":
            raise LLMError("출력 한도(max_tokens)에 걸려 답이 잘림. 생각 토큰도 한도에 포함되니 config.py 에서 올릴 것")

    @staticmethod
    def _text(resp) -> str:
        return "".join(b.text for b in resp.content if b.type == "text")

    def _json(self, role_name: str, role: Role, system, user: str, schema: dict) -> dict:
        resp = self.client.beta.messages.create(
            model=role.model,
            max_tokens=role.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": role.effort, "format": {"type": "json_schema", "schema": schema}},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        self._check(resp)
        self._record(role_name, role, resp)
        return json.loads(self._text(resp))

    def _long_text(self, role_name: str, role: Role, system, user: str) -> str:
        # 출력 한도가 크면 스트리밍으로 받아야 요청 시간 초과가 안 난다.
        with self.client.beta.messages.stream(
            model=role.model,
            max_tokens=role.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": role.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            resp = stream.get_final_message()
        self._check(resp)
        self._record(role_name, role, resp)
        return self._text(resp)

    @staticmethod
    def _cached_system(instructions: str, evidence: str) -> list[dict]:
        # 지시문 + 근거 목록은 다시 쓰기 때마다 똑같으므로 캐시해서 재사용한다 (반복 호출 비용 절감).
        return [{"type": "text", "text": instructions},
                {"type": "text", "text": evidence, "cache_control": {"type": "ephemeral"}}]

    # ---------- 에이전트별 ----------
    def analyze(self, posting: str) -> dict:
        """요구 항목(1차 정보)과 회사 읽기(2차 정보: 돈 버는 방식 → 중요 지표)를 함께 돌려준다."""
        return self._json("analyzer", self.cfg.analyzer, prompts.ANALYZER,
                          f"<공고>\n{posting}\n</공고>", prompts.ANALYZE_SCHEMA)

    def write(self, posting: str, fit_table: str, sources: dict, feedback: str = "", company: dict | None = None) -> str:
        user = (f"<공고>\n{posting}\n</공고>\n\n<회사 읽기 (AI 추정)>\n{prompts.company_block(company or {})}\n</회사 읽기>"
                f"\n\n<적합도 표 (코드가 계산)>\n{fit_table}\n</적합도 표>")
        if feedback:
            user += f"\n\n<검증 의견: 이 문제들을 고쳐서 다시 쓸 것>\n{feedback}\n</검증 의견>"
        return self._long_text("writer", self.cfg.writer,
                               self._cached_system(prompts.WRITER, prompts.evidence_block(sources)), user)

    def verify(self, draft: str, sources: dict, company: dict | None = None) -> list[dict]:
        data = self._json("verifier", self.cfg.verifier,
                          self._cached_system(prompts.VERIFIER, prompts.evidence_block(sources)),
                          f"<회사 읽기 (AI 추정)>\n{prompts.company_block(company or {})}\n</회사 읽기>\n\n<초안>\n{draft}\n</초안>",
                          prompts.VERIFY_SCHEMA)
        return data["issues"]

    def baseline(self, posting: str, sources: dict) -> str:
        """에이전트 1개짜리 기준선: 공고와 모든 근거를 한 번에 주고 바로 쓰게 한다."""
        return self._long_text("baseline", self.cfg.writer,
                               self._cached_system(prompts.BASELINE, prompts.evidence_block(sources)),
                               f"<공고>\n{posting}\n</공고>")

    def cost_summary(self) -> str:
        if not self.calls:
            return "모델 호출 없음"
        lines = [f"- {c['role']}: 입력 {c['input']:,} · 출력 {c['output']:,} · 캐시 읽기 {c['cache_read']:,}"
                 f" · 캐시 쓰기 {c.get('cache_write', 0):,} 토큰 · 약 US${c['cost_usd']}"
                 for c in self.calls]
        total = sum(c["cost_usd"] for c in self.calls)
        return "\n".join(lines + [f"- 합계: 약 US${total:.4f} (단가표 기준 추정, 실제 청구는 콘솔 확인)"])
