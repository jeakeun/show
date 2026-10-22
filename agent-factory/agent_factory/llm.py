"""모델 호출과 비용 장부.

- 모든 호출은 Ledger 에 기록한다 (누가, 어떤 모델, 토큰, 비용). 비용은 코드가 계산한다.
- 예산을 넘으면 다음 호출 전에 BudgetExceeded 로 멈춘다.
- 실제 모델(AnthropicLLM)과 가짜 모델(demo.py 의 DemoLLM, 테스트용)이 같은 모양(chat)을 쓴다.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ValidationError


# ---------------------------------------------------------------- 모델과 가격

@dataclass(frozen=True)
class ModelInfo:
    alias: str
    id: str
    input_usd: float  # 100만 토큰당
    output_usd: float
    cache_read_usd: float
    note: str
    server_fallback: bool = True  # 안전 분류기 거절 시 서버가 다른 모델로 다시 실행 (haiku 는 미지원)
    long_threshold: Optional[int] = None  # 이 토큰을 넘는 긴 입력이면 다른 가격
    long_input_usd: Optional[float] = None
    long_output_usd: Optional[float] = None


MODELS: dict[str, ModelInfo] = {
    "opus": ModelInfo("opus", "claude-opus-5-5", 4.00, 20.00, 0.20, "어려운 판단·설계·종합"),
    "sonnet": ModelInfo("sonnet", "claude-sonnet-5-5", 2.00, 10.00, 0.20, "일반 작성·분석"),
    "haiku": ModelInfo(
        "haiku", "claude-haiku-5-5", 0.10, 0.50, 0.01, "단순 정리·분류·검사",
        server_fallback=False, long_threshold=100_000, long_input_usd=0.50, long_output_usd=2.50,
    ),
}
# 거절 시 서버가 대신 실행할 수 있는 모델의 가격 (입력, 출력)
SERVED_PRICES = {"claude-opus-5": (5.00, 25.00), "claude-opus-4-8": (5.00, 25.00), "claude-sonnet-5": (2.00, 10.00)}
CACHE_WRITE_MULT = 1.25  # 5분 캐시 쓰기
WEB_SEARCH_USD = 0.01  # 검색 1회
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TOKENS = 16_000


def model_catalog_text() -> str:
    return "\n".join(
        f"- {m.alias} ({m.id}): {m.note}. 100만 토큰당 입력 ${m.input_usd} / 출력 ${m.output_usd}"
        for m in MODELS.values()
    )


# ---------------------------------------------------------------- 사용량과 장부

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    web_searches: int = 0


def cost_usd(alias: str, served_model: str, u: Usage) -> float:
    info = MODELS[alias]
    inp, out, cread = info.input_usd, info.output_usd, info.cache_read_usd
    if served_model != info.id and served_model in SERVED_PRICES:  # 거절 후 다른 모델이 대신 답한 경우 (대략)
        inp, out = SERVED_PRICES[served_model]
        cread = inp * 0.1
    prompt_total = u.input_tokens + u.cache_read + u.cache_write
    if info.long_threshold and prompt_total > info.long_threshold:
        inp, out, cread = info.long_input_usd, info.long_output_usd, info.long_input_usd * 0.1
    usd = (
        u.input_tokens * inp
        + u.cache_write * inp * CACHE_WRITE_MULT
        + u.cache_read * cread
        + u.output_tokens * out
    ) / 1_000_000
    return usd + u.web_searches * WEB_SEARCH_USD


class Stopped(Exception):
    """실행을 멈추게 하는 이유 (예산 초과, 사용자 중단)."""


class BudgetExceeded(Stopped):
    pass


class Cancelled(Stopped):
    pass


class LLMError(Exception):
    pass


class FormatError(LLMError):
    """모델이 정해진 형식(JSON)으로 답하지 않음. API 는 정상."""


OUTPUT_ESTIMATE_TOKENS = 4_000


def estimate_usd(alias: str, system: str, messages: list, tools: list) -> float:
    """호출 전 대략 비용 (동시에 나가는 호출끼리 예산을 나눠 잡는 데만 씀). 글자 2개 ≈ 토큰 1개로 넉넉히."""
    chars = len(system) + len(json.dumps(messages, ensure_ascii=False, default=str)) + len(json.dumps(tools, default=str))
    info = MODELS[alias]
    return (chars / 2 * info.input_usd + OUTPUT_ESTIMATE_TOKENS * info.output_usd) / 1_000_000


class Ledger:
    """호출마다 한 줄씩 기록. 여러 에이전트가 동시에 써도 안전하게 잠금.

    예산: 호출 전에 '지금까지 쓴 돈 + 동시에 진행 중인 호출의 예상 비용' 이 예산 이상이면,
    진행 중인 호출이 끝나기를 기다렸다가 다시 본다. 실제로 쓴 돈이 예산 이상이면 멈춘다.
    → 넘더라도 마지막 호출 1번 비용만큼만 넘는다 (병렬이라고 여러 번 넘지 않음).
    """

    def __init__(self, budget_usd: float, path: Optional[Path] = None):
        self.budget_usd = budget_usd
        self.path = Path(path) if path else None
        self.rows: list[dict] = []
        self.cancelled = threading.Event()
        self._pending = 0.0
        self._cond = threading.Condition()

    @property
    def total_usd(self) -> float:
        return sum(r["usd"] for r in self.rows)

    def cancel(self) -> None:
        self.cancelled.set()
        with self._cond:
            self._cond.notify_all()

    def reserve(self, who: str, est: float) -> None:
        with self._cond:
            while True:
                if self.cancelled.is_set():
                    raise Cancelled(f"사용자가 멈춰서 '{who}' 호출을 하지 않았습니다")
                spent = self.total_usd
                if spent >= self.budget_usd:
                    raise BudgetExceeded(
                        f"예산 ${self.budget_usd:.2f} 를 다 써서 '{who}' 호출 전에 멈췄습니다 (지금까지 ${spent:.4f})"
                    )
                if self._pending == 0 or spent + self._pending < self.budget_usd:
                    self._pending += est
                    return
                self._cond.wait(timeout=1.0)  # 동시에 도는 호출이 끝나면 다시 본다

    def release(self, est: float) -> None:
        with self._cond:
            self._pending = max(0.0, self._pending - est)
            self._cond.notify_all()

    def ensure_room(self, who: str) -> None:
        self.reserve(who, 0.0)

    def record(self, who: str, alias: str, served_model: str, u: Usage, stop_reason: str,
               reserved: float = 0.0, parts: Optional[list] = None) -> dict:
        if parts:  # 거절 → 대체 모델처럼 한 호출 안에서 여러 모델이 돈 경우, 모델별로 계산
            usd = sum(cost_usd(alias, m, pu) for m, pu in parts) + u.web_searches * WEB_SEARCH_USD
        else:
            usd = cost_usd(alias, served_model, u)
        row = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "who": who,
            "model": alias,
            "served_model": served_model,
            **asdict(u),
            "stop_reason": stop_reason,
            "usd": round(usd, 6),
        }
        with self._cond:
            self.rows.append(row)
            self._pending = max(0.0, self._pending - reserved)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._cond.notify_all()
        return row

    def by_agent(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in self.rows:
            a = out.setdefault(r["who"], {"calls": 0, "usd": 0.0, "input": 0, "output": 0})
            a["calls"] += 1
            a["usd"] += r["usd"]
            a["input"] += r["input_tokens"] + r["cache_read"] + r["cache_write"]
            a["output"] += r["output_tokens"]
        return out


# ---------------------------------------------------------------- 호출 결과

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class Reply:
    content: list  # 다음 호출에 그대로 돌려줄 블록들 (고치지 않고 그대로 = 캐시·사고 블록 보존)
    stop_reason: str
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    parsed: Any = None
    served_model: str = ""
    cost_parts: list = field(default_factory=list)  # [(모델 ID, Usage)] 한 호출 안 여러 모델일 때


class BaseLLM:
    """chat() 하나로 모든 호출을 한다. 장부 기록과 예산 확인은 여기서."""

    demo = False

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def chat(
        self,
        *,
        who: str,
        model: str,
        system: str,
        messages: list,
        tools: Optional[list] = None,
        effort: str = "medium",
        output_schema: Optional[type[BaseModel]] = None,
        tool_choice_none: bool = False,
    ) -> Reply:
        est = 0.0 if self.demo else estimate_usd(model, system, messages, tools or [])
        self.ledger.reserve(who, est)
        try:
            reply, usage = self._call(
                model=model, system=system, messages=messages, tools=tools or [], effort=effort,
                output_schema=output_schema, tool_choice_none=tool_choice_none, who=who,
            )
        except BaseException:
            self.ledger.release(est)
            raise
        self.ledger.record(who, model, reply.served_model or MODELS[model].id, usage, reply.stop_reason,
                           reserved=est, parts=reply.cost_parts)
        if output_schema is not None and reply.stop_reason == "end_turn" and reply.parsed is None:
            try:
                reply.parsed = output_schema.model_validate_json(reply.text)
            except ValidationError as e:
                raise FormatError(f"{who}: 정해진 형식(JSON)으로 답하지 않았습니다: {e.errors()[:2]}") from None
        return reply

    def _call(self, **kw) -> tuple[Reply, Usage]:  # pragma: no cover - 하위 클래스가 구현
        raise NotImplementedError


# ---------------------------------------------------------------- 실제 모델

def _read_env_value(path: Path, name: str) -> Optional[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        k, sep, v = line.partition("=")
        if not sep or k.strip() != name:
            continue
        v = v.strip()
        if v[:1] in ("'", '"') and v[:1] in v[1:]:
            v = v[1 : v.index(v[0], 1)]
        else:
            v = v.split(" #", 1)[0].strip()
        if v:
            return v
    return None


def find_api_key(paths: Optional[list] = None) -> tuple[Optional[str], str]:
    """(키, 어디서 찾았는지). 키 값은 절대 출력하지 않는다. 키가 None 이어도 위치가 '없음'이 아니면 SDK 가 알아서 인증."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "환경변수 ANTHROPIC_API_KEY"
    if paths is None:
        here = Path(__file__).resolve().parent.parent
        paths = [here / ".env", Path("D:/yt-auto/secrets/.env")]
    for p in paths:
        v = _read_env_value(Path(p), "ANTHROPIC_API_KEY")
        if v:
            return v, str(p)
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return None, "환경변수 ANTHROPIC_AUTH_TOKEN"
    return None, "없음"


class AnthropicLLM(BaseLLM):
    def __init__(self, ledger: Ledger, client=None):
        super().__init__(ledger)
        if client is None:
            import anthropic

            key, _ = find_api_key()
            client = anthropic.Anthropic(api_key=key, max_retries=3) if key else anthropic.Anthropic(max_retries=3)
        self.client = client

    def _call(self, *, model, system, messages, tools, effort, output_schema, tool_choice_none, who):
        import anthropic

        info = MODELS[model]
        output_config: dict = {"effort": effort}
        if output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": anthropic.transform_schema(output_schema)}
        params: dict = dict(
            model=info.id,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            output_config=output_config,
        )
        if tools or len(messages) > 1:  # 같은 앞부분을 다시 보낼 호출만 캐시 (한 번뿐인 호출은 쓰기 비용만 늘어남)
            params["cache_control"] = {"type": "ephemeral"}
        if tools:
            params["tools"] = tools
            if tool_choice_none:
                params["tool_choice"] = {"type": "none"}
        if info.server_fallback:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        try:
            resp = self.client.beta.messages.create(**params)
        except anthropic.AuthenticationError:
            raise LLMError("API 키가 틀렸거나 없습니다. agent-factory/.env 에 ANTHROPIC_API_KEY=... 를 넣으세요") from None
        except anthropic.PermissionDeniedError as e:
            raise LLMError(f"권한이 없습니다: {e.message}") from None
        except anthropic.NotFoundError as e:
            raise LLMError(f"모델이나 주소를 찾지 못했습니다: {e.message}") from None
        except anthropic.RateLimitError:
            raise LLMError("호출 한도에 걸렸습니다 (잠시 후 다시)") from None
        except anthropic.BadRequestError as e:
            raise LLMError(f"요청 형식 오류: {e.message}") from None
        except anthropic.APIStatusError as e:
            raise LLMError(f"API 오류 {e.status_code}: {e.message}") from None
        except anthropic.APIConnectionError:
            raise LLMError("인터넷 연결 문제로 API 에 닿지 못했습니다") from None
        except TypeError as e:
            if "api_key" in str(e) or "auth" in str(e).lower():
                raise LLMError("API 키가 없습니다. agent-factory/.env 에 ANTHROPIC_API_KEY=... 를 넣으세요") from None
            raise

        u = resp.usage
        stu = getattr(u, "server_tool_use", None)
        usage = Usage(
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
            web_searches=(getattr(stu, "web_search_requests", 0) or 0) if stu else 0,
        )
        parts = []
        for it in getattr(u, "iterations", None) or []:  # 거절 → 대체 모델이면 시도마다 따로 청구됨
            parts.append((getattr(it, "model", None) or info.id, Usage(
                input_tokens=it.input_tokens or 0, output_tokens=it.output_tokens or 0,
                cache_read=it.cache_read_input_tokens or 0, cache_write=it.cache_creation_input_tokens or 0,
            )))
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input or {})) for b in resp.content if b.type == "tool_use"]
        reply = Reply(
            content=list(resp.content), stop_reason=resp.stop_reason or "", text=text,
            tool_calls=calls, served_model=resp.model, cost_parts=parts if len(parts) > 1 else [],
        )
        if resp.stop_reason == "refusal":
            cat = getattr(getattr(resp, "stop_details", None), "category", None)
            reply.text = f"(모델이 이 요청을 거절했습니다. 분류: {cat})"
        return reply, usage
