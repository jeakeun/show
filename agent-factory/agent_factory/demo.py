"""데모 모드: API 키 없이, 돈 안 들이고 흐름만 보는 가짜 모델.

정해진 규칙대로 답한다.
- 설계자: 상황 글의 낱말을 보고 견본 팀 3개 중 하나를 고른다. '여럿 조사' 견본은 일부러 첫 설계에서
  규칙(R06 병렬은 읽기만)을 어겨서, 코드 검사가 잡아내고 설계자가 고치는 과정을 보여준다.
- 검토 에이전트: 늘 '좋음'.
- 일하는 에이전트: 첫 호출에서 list_files 도구를 쓰고, 두 번째 호출에서 결과를 쓴다.
- 결과 검토자: 1회차는 '수정 필요', 2회차는 '통과' (검토 루프를 보여주려고).
"""
from __future__ import annotations

import re

from .designer import Critique
from .llm import BaseLLM, Ledger, Reply, ToolCall, Usage
from .spec import AgentSpec, ReviewSpec, Stage, TeamSpec
from .team import ReviewVerdict

READ = ["list_files", "read_file", "search_files"]


def _single(situation: str) -> TeamSpec:
    return TeamSpec(
        name="single-helper",
        situation=situation,
        agents=[AgentSpec(
            name="helper", role="자료를 읽고 정리하는 도우미", model="sonnet", effort="medium",
            tools=READ + ["calculate"], max_turns=6,
            instructions="작업 폴더의 자료를 읽고 상황에서 요청한 내용을 정리한다. 숫자는 calculate 로 계산한다.",
        )],
        stages=[Stage(agents=["helper"])],
        budget_usd=0.3,
    )


def _parallel(situation: str, broken: bool) -> TeamSpec:
    scout_tools = READ + (["save_file"] if broken else [])
    return TeamSpec(
        name="parallel-research",
        situation=situation,
        why_not_single="자료 묶음이 서로 독립적이라 나눠 읽으면 빠르고, 각자 요약만 넘겨 작성자의 맥락이 가벼워진다.",
        agents=[
            AgentSpec(name="scout_a", role="자료 앞쪽 절반 조사", model="haiku", effort="low", tools=scout_tools,
                      why_separate="읽을 자료가 많아 맥락 보호를 위해 절반만 읽고 요약만 넘긴다.", max_turns=5,
                      instructions="작업 폴더 파일 목록의 앞쪽 절반을 읽고 핵심 사실을 출처와 함께 요약한다."),
            AgentSpec(name="scout_b", role="자료 뒤쪽 절반 조사", model="haiku", effort="low", tools=READ,
                      why_separate="scout_a 와 겹치지 않는 자료를 동시에 읽어 시간을 줄인다(병렬).", max_turns=5,
                      instructions="작업 폴더 파일 목록의 뒤쪽 절반을 읽고 핵심 사실을 출처와 함께 요약한다."),
            AgentSpec(name="writer", role="두 요약을 합쳐 최종 정리", model="sonnet", effort="medium",
                      tools=["calculate", "save_file"], max_turns=4,
                      why_separate="쓰기는 한 곳. 두 요약만 받아 하나의 결과로 합친다.",
                      instructions="두 조사 결과를 비교·종합해 최종 정리를 쓰고 report.md 로 저장한다."),
        ],
        stages=[Stage(agents=["scout_a", "scout_b"]), Stage(agents=["writer"])],
        budget_usd=0.5,
    )


def _review(situation: str) -> TeamSpec:
    return TeamSpec(
        name="write-and-check",
        situation=situation,
        why_not_single="작성자는 자기 글에 관대해지므로, 근거 없는 문장과 과장을 다른 맥락의 검토자가 잡아야 한다.",
        agents=[
            AgentSpec(name="writer", role="자료를 읽고 초안 작성", model="sonnet", effort="medium",
                      tools=READ + ["calculate"], max_turns=6,
                      why_separate="자료를 직접 읽고 쓰는 유일한 작성자다.",
                      instructions="작업 폴더 자료를 읽고 요청한 글을 쓴다. 모든 사실 문장 끝에 출처를 붙인다."),
            AgentSpec(name="checker", role="근거·과장 검토", model="haiku", effort="low",
                      tools=["read_file", "search_files"], max_turns=4,
                      why_separate="작성 과정을 모르는 맥락에서 결과만 보고 견제한다.",
                      instructions="초안의 각 문장이 출처와 맞는지 확인하고 과장 표현을 찾는다."),
        ],
        stages=[Stage(agents=["writer"])],
        review=ReviewSpec(reviewer="checker", criteria=["모든 사실 문장에 출처가 있다", "과장 표현이 없다"],
                          max_rounds=2),
        budget_usd=0.4,
    )


def demo_design(situation: str, attempt: int) -> TeamSpec:
    if re.search(r"검토|검수|리뷰|틀린|사실 확인|팩트", situation):
        return _review(situation)
    if re.search(r"비교|조사|여러|각각|모아|전부|모든", situation):
        return _parallel(situation, broken=(attempt == 1))
    return _single(situation)


def _first_user_text(messages: list) -> str:
    c = messages[0]["content"]
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict))


class DemoLLM(BaseLLM):
    demo = True

    def __init__(self, ledger: Ledger):
        super().__init__(ledger)
        self._review_calls: dict[str, int] = {}
        self._n = 0

    def _text(self, text: str, stop="end_turn") -> Reply:
        return Reply(content=[{"type": "text", "text": text}], stop_reason=stop, text=text)

    def _call(self, *, model, system, messages, tools, effort, output_schema, tool_choice_none, who):
        usage = Usage()  # 데모는 비용 0
        assistant_turns = sum(1 for m in messages if m["role"] == "assistant")

        if output_schema is TeamSpec:
            first = _first_user_text(messages)
            m = re.search(r"## 상황\n(.*?)(\n\n## |\Z)", first, re.S)
            situation = m.group(1).strip() if m else first
            team = demo_design(situation, attempt=assistant_turns + 1)
            return self._text(team.model_dump_json()), usage

        if output_schema is Critique:
            c = Critique(verdict="ok", problems=[], notes=["(데모) 실제 검토 에이전트는 여기서 설계의 약점을 반박합니다."],
                         simpler_alternative="")
            return self._text(c.model_dump_json()), usage

        if output_schema is ReviewVerdict:
            n = self._review_calls.get(who, 0) + 1
            self._review_calls[who] = n
            if n == 1:
                v = ReviewVerdict(passed=False, issues=["(데모) 출처가 없는 문장이 있다고 가정한 지적"],
                                  summary="1회차는 일부러 수정 요청")
            else:
                v = ReviewVerdict(passed=True, issues=[], summary="지적이 반영됨")
            return self._text(v.model_dump_json()), usage

        tool_names = {t.get("name") for t in tools}
        if assistant_turns == 0 and "list_files" in tool_names and not tool_choice_none:
            self._n += 1
            call = ToolCall(id=f"demo_{self._n}", name="list_files", input={"path": "."})
            block = {"type": "tool_use", "id": call.id, "name": call.name, "input": call.input}
            return Reply(content=[block], stop_reason="tool_use", text="", tool_calls=[call]), usage

        seen = ""
        for m in messages:
            if m["role"] == "user" and isinstance(m["content"], list):
                for b in m["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        seen = str(b.get("content", ""))
        files = len([ln for ln in seen.splitlines() if ln.strip() and not ln.startswith("...")])
        prev = len(re.findall(r"<결과 에이전트=", _first_user_text(messages)))
        rewrite = "검토자가 고치라고 한 점" in _first_user_text(messages)
        text = (
            f"(데모 응답) 에이전트 '{who}' 결과입니다.\n"
            f"- 작업 폴더에서 파일 {files}개를 확인했습니다.\n- 앞 단계 결과 {prev}개를 받았습니다.\n"
            + ("- 검토 지적을 반영해 다시 썼습니다.\n" if rewrite else "")
            + "실제 모드에서는 여기에 AI가 쓴 결과가 들어갑니다."
        )
        return self._text(text), usage
