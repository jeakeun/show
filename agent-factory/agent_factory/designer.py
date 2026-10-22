"""상황 → 팀 설계도.

흐름 (설계도 자체도 '만든 쪽 ↔ 검사하는 쪽'을 나눈다)
  ① 설계 에이전트가 설계도(JSON)를 낸다
  ② 코드 규칙 검사(rules.py). 어기면 위반 내용을 붙여 ①로 (최대 max_fixes 번)
  ③ 검토 에이전트가 설계자의 생각을 모른 채 설계도만 보고 반박한다
  ④ 심각한 문제를 지적하면 설계자가 한 번 고치고 다시 ②
  ⑤ 사람이 보고 실행 여부를 정한다 (cli.py)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

from pydantic import BaseModel, Field

from .llm import BaseLLM, LLMError, model_catalog_text
from .rules import Finding, check, rules_text, warnings
from .spec import TeamSpec, team_to_yaml
from .tools import catalog_text

DESIGNER_MODEL = "opus"
CRITIC_MODEL = "opus"

DESIGNER_SYSTEM = """\
너는 '에이전트 팀 설계자'다. 사람이 설명한 상황을 보고, 그 일을 맡을 에이전트 팀 설계도를 만든다.

## 설계 원칙 (위에서부터 중요)
1. 먼저 1명으로 생각한다. 1명으로 충분하면 1명 팀을 낸다. 나누는 것은 아래 이유가 있을 때만이다.
   - 맥락 보호: 읽을 자료가 많아 한 명이 다 보면 산만해질 때 → 자료별로 나눠 읽고 요약만 넘긴다
   - 병렬: 서로 독립적인 읽기 일이 여러 개일 때 → 같은 단계에서 동시에
   - 전문화: 칸마다 맞는 모델·도구가 다를 때 (단순 정리는 haiku, 종합 판단은 opus)
   - 견제: 만든 쪽과 검사하는 쪽을 나눠야 할 때 → review(검토 루프)
2. 직함(기획·개발·QA)으로 나누지 않는다. 같은 자료를 쓰는 일은 한 명에게 묶는다. 넘길 때마다 맥락이 끊긴다.
3. 읽기는 나눠도 되고, 쓰기는 한 곳으로 모은다.
4. 합계·비율 같은 숫자가 필요하면 calculate 도구를 준다. 숫자는 AI가 머리로 세지 않는다.
5. 모델은 칸의 난이도에 맞춘다. 모든 칸에 opus 를 쓰지 않는다.
6. 예산(budget_usd)은 일의 크기에 맞게 잡는다. 보통 0.2~1.0.

## 지켜야 할 규칙 (코드가 검사한다. 어기면 돌려보낸다)
{rules}

## 쓸 수 있는 모델
{models}

## 쓸 수 있는 도구
{tools}

## 구조를 쓰는 법
- stages: 순서대로 실행되는 단계. 한 단계의 agents 가 2명 이상이면 동시에 일한다.
- 바로 앞 단계의 결과만 다음 단계로 넘어간다. 마지막 단계의 1명이 최종 결과를 쓴다.
- review: 마지막 결과를 검토자가 기준(criteria)으로 판정하고, 미통과면 같은 작성자가 다시 쓴다. 검토자는 stages 에 넣지 않는다.
  검토자는 앞 단계 결과(근거)와 최종 결과를 함께 받는다. 견제가 필요한 일(사실 확인, 과장 검사, 규칙 준수)에만 둔다.
- instructions 는 그 에이전트 혼자 읽는 지시문이다. 다른 에이전트의 대화를 모르므로, 무엇을 보고 무엇을 어떤 모양으로 넘길지 구체적으로 쓴다.
- 에이전트가 읽는 파일은 '작업 폴더' 안에만 있다. 경로는 작업 폴더 기준 상대 경로다.
- name, model, tools 등 이름 칸은 영문으로, 설명 칸(role, why_*, instructions, criteria)은 한국어로 쓴다.
"""


class Critique(BaseModel):
    verdict: Literal["ok", "revise"] = Field(description="심각한 문제가 있을 때만 revise")
    problems: list[str] = Field(description="반드시 고칠 것. 없으면 빈 목록")
    notes: list[str] = Field(description="참고할 점 (사소한 것)")
    simpler_alternative: str = Field(description="더 단순한 구조가 있으면 한두 문장으로. 없으면 빈 문자열")


CRITIC_SYSTEM = """\
너는 에이전트 팀 설계 검토자다. 설계자가 왜 그렇게 했는지 모른 채, 설계도만 보고 반박한다.
다음을 차례로 본다.
1. 1명으로도 되는 일을 여럿으로 나누지 않았나? 더 단순한 구조가 있나?
2. 실패하기 쉬운 곳은? (한 명이 읽을 양이 너무 많음, 검증이 없음, 반복 상한 부족, 앞 단계 결과가 다음 단계에 필요한 만큼 안 넘어감)
3. 직함으로 나누지 않았나? 같은 자료를 쓰는 일이 여러 명에게 쪼개지지 않았나?
4. 모델·도구·예산이 칸의 일에 맞나? 필요한 도구가 빠지지 않았나?
5. 각 지시문이 그 에이전트 혼자 읽고 일할 수 있을 만큼 구체적인가?
일을 망칠 문제가 있을 때만 verdict 를 revise 로 한다. 취향 차이나 사소한 것은 notes 에 쓴다.
코드가 이미 검사하는 규칙:
{rules}
"""


class DesignError(Exception):
    def __init__(self, message: str, findings: Optional[list[Finding]] = None):
        super().__init__(message)
        self.findings = findings or []


@dataclass
class Design:
    team: TeamSpec
    warnings: list[str]
    critique: Optional[Critique]
    critique_applied: bool
    log: list[str] = field(default_factory=list)  # 설계 과정 기록 (규칙 위반·수정 내역)


def _findings_text(fs: list[Finding]) -> str:
    return "\n".join(f"- {f}" for f in fs)


class _Conversation:
    """설계자와의 대화. 앞 대화를 고치지 않고 이어 붙이기만 한다."""

    def __init__(self, llm: BaseLLM, situation: str, listing: str):
        self.llm = llm
        self.situation = situation
        self.system = DESIGNER_SYSTEM.format(rules=rules_text(), models=model_catalog_text(), tools=catalog_text())
        first = f"## 상황\n{situation.strip()}\n\n"
        if listing:
            first += f"## 작업 폴더 파일 목록 (일부)\n{listing}\n\n"
        first += "위 상황에 맞는 팀 설계도를 만들어라."
        self.messages: list = [{"role": "user", "content": first}]
        self.attempts = 0

    def ask(self) -> TeamSpec:
        reply = self.llm.chat(
            who="designer", model=DESIGNER_MODEL, system=self.system, messages=self.messages,
            output_schema=TeamSpec, effort="high",
        )
        self.messages.append({"role": "assistant", "content": reply.content})
        if reply.parsed is None:
            raise DesignError(f"설계 에이전트가 설계도를 내지 못했습니다 ({reply.stop_reason}): {reply.text[:300]}")
        team: TeamSpec = reply.parsed
        team.situation = self.situation.strip()  # 상황은 사람이 쓴 그대로
        return team

    def tell(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def until_valid(self, max_fixes: int, log: list[str], say) -> TeamSpec:
        for attempt in range(max_fixes + 1):
            team = self.ask()
            self.attempts += 1
            problems = check(team)
            if not problems:
                log.append(f"설계 {self.attempts}차: 규칙 검사 통과 ({team.shape()})")
                return team
            log.append(f"설계 {self.attempts}차: 규칙 위반 {len(problems)}건\n" + _findings_text(problems))
            say(f"  규칙 위반 {len(problems)}건 → 설계자에게 돌려보냄: " + "; ".join(str(p) for p in problems[:3]))
            if attempt == max_fixes:
                raise DesignError(f"{max_fixes}번 고쳐도 규칙을 통과하지 못했습니다", problems)
            self.tell("코드 규칙 검사에서 아래 위반이 나왔다. 모두 고친 설계도 전체를 다시 내라.\n" + _findings_text(problems))
        raise AssertionError("unreachable")


def critique_team(llm: BaseLLM, team: TeamSpec) -> Critique:
    reply = llm.chat(
        who="critic", model=CRITIC_MODEL, system=CRITIC_SYSTEM.format(rules=rules_text()),
        messages=[{"role": "user", "content": f"## 상황\n{team.situation}\n\n## 설계도 (YAML)\n{team_to_yaml(team)}"}],
        output_schema=Critique, effort="medium",
    )
    if reply.parsed is None:
        raise LLMError(f"검토 에이전트가 판정을 내지 못했습니다 ({reply.stop_reason})")
    return reply.parsed


def design_team(
    llm: BaseLLM,
    situation: str,
    *,
    listing: str = "",
    max_fixes: int = 2,
    use_critic: bool = True,
    on_event: Optional[Callable[[str], None]] = None,
) -> Design:
    say = on_event or (lambda s: None)
    log: list[str] = []
    conv = _Conversation(llm, situation, listing)
    say(f"설계 에이전트({DESIGNER_MODEL})가 팀을 설계하는 중...")
    team = conv.until_valid(max_fixes, log, say)

    critique, applied = None, False
    if use_critic:
        say(f"검토 에이전트({CRITIC_MODEL})가 설계를 반박하는 중...")
        critique = critique_team(llm, team)
        log.append(f"검토 의견: {critique.verdict} / 문제 {len(critique.problems)}건 / 참고 {len(critique.notes)}건")
        if critique.verdict == "revise" and critique.problems:
            say(f"  검토 지적 {len(critique.problems)}건 → 설계자가 고치는 중...")
            msg = "설계 검토자가 아래 문제를 지적했다. 맞는 지적은 반영하고 설계도 전체를 다시 내라.\n" + "\n".join(
                f"- {p}" for p in critique.problems
            )
            if critique.simpler_alternative:
                msg += f"\n- 더 단순한 대안 제안: {critique.simpler_alternative}"
            conv.tell(msg)
            try:
                team = conv.until_valid(max_fixes, log, say)
                applied = True
            except DesignError as e:
                log.append(f"검토 반영본이 규칙을 통과하지 못해 앞 설계를 씁니다: {e}")
                say("  검토 반영본이 규칙을 통과하지 못해 앞 설계를 씁니다")
    return Design(team=team, warnings=warnings(team), critique=critique, critique_applied=applied, log=log)
