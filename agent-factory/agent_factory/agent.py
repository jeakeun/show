"""에이전트 1명 = 모델 + 지시문 + 도구 + 반복 루프.

설계도(AgentSpec)를 받아 실제로 일하는 루프를 돌린다. 이 파일이 '에이전트를 만드는 공장'의 본체다.
루프: 모델 호출 → 도구를 쓰겠다고 하면 코드가 실행 → 결과를 돌려줌 → 다시 호출 … 끝났다고 하면 멈춤.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pydantic import BaseModel

from .llm import BaseLLM
from .spec import AgentSpec
from .tools import TOOLS, ToolPolicy, Workspace

COMMON_RULES = """\
- 결과는 한국어로 쓴다.
- 파일이나 앞 단계 결과에서 가져온 사실에는 출처를 붙인다. 예: (weekly.md:12), (data_scout 결과)
- 확인하지 못한 것은 추측하지 말고 "확인 못 함"이라고 쓴다.
- 마지막 답에는 다음 사람이 바로 쓸 결과만 쓴다. 과정 설명은 짧게."""


def build_system(spec: AgentSpec) -> str:
    tools = [TOOLS[t] for t in spec.tools if t in TOOLS]
    rules = COMMON_RULES
    if "calculate" in spec.tools:
        rules += "\n- 합계·비율·증감률 같은 숫자는 머리로 세지 말고 calculate 도구로 계산한다."
    if any(t.name in ("list_files", "read_file", "search_files") for t in tools):
        rules += "\n- 파일 경로는 작업 폴더 기준 상대 경로로 쓴다. 먼저 list_files 로 무엇이 있는지 본다."
    tool_lines = "\n".join(f"- {t.name}: {t.summary}" for t in tools) or "- (도구 없음. 받은 자료만 보고 답한다)"
    return (
        f"너는 '{spec.role}' 역할을 맡은 에이전트 '{spec.name}' 이다. 여러 에이전트가 나눠 일하는 팀의 한 명이다.\n\n"
        f"## 너의 지시문\n{spec.instructions.strip()}\n\n"
        f"## 공통 규칙\n{rules}\n\n"
        f"## 쓸 수 있는 도구\n{tool_lines}\n"
    )


@dataclass
class AgentResult:
    name: str
    text: str
    ok: bool
    turns: int
    stop_reason: str
    trace: list[str] = field(default_factory=list)  # 도구 사용 기록 (사람이 읽는 용)
    parsed: Optional[BaseModel] = None


def _short(x, n=200) -> str:
    s = str(x).replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def run_agent(
    llm: BaseLLM,
    spec: AgentSpec,
    user_content: str,
    ws: Workspace,
    *,
    approver: Optional[Callable[[str, str, dict], bool]] = None,
    output_schema: Optional[type[BaseModel]] = None,
    on_event: Optional[Callable[[str], None]] = None,
) -> AgentResult:
    say = on_event or (lambda s: None)
    policy = ToolPolicy(allowed=list(spec.tools), approver=approver)
    api_tools = [TOOLS[t].api_def() for t in spec.tools if t in TOOLS]
    system = build_system(spec)
    messages: list = [{"role": "user", "content": user_content}]
    trace: list[str] = []

    def call(tool_choice_none: bool = False):
        return llm.chat(
            who=spec.name, model=spec.model, system=system, messages=messages, tools=api_tools,
            effort=spec.effort, output_schema=output_schema, tool_choice_none=tool_choice_none,
        )

    for turn in range(1, spec.max_turns + 1):
        reply = call()
        # 받은 블록을 고치지 않고 그대로 이어 붙인다 (사고 블록·캐시 보존)
        messages.append({"role": "assistant", "content": reply.content})

        if reply.stop_reason == "refusal":
            return AgentResult(spec.name, reply.text, False, turn, "refusal", trace)
        if reply.stop_reason == "pause_turn":  # 서버 도구(웹 검색)가 길어져 잠시 멈춤 → 그대로 이어서
            trace.append("(웹 검색이 길어져 이어서 진행)")
            continue
        if reply.stop_reason == "tool_use" and reply.tool_calls:
            results = []
            for tc in reply.tool_calls:
                out, is_err = policy.execute(spec.name, tc.name, tc.input, ws)
                trace.append(f"{tc.name}({_short(tc.input, 120)}) → {'오류: ' if is_err else ''}{_short(out)}")
                say(f"  {spec.name}: {tc.name} {_short(tc.input, 80)}")
                block = {"type": "tool_result", "tool_use_id": tc.id, "content": out}
                if is_err:
                    block["is_error"] = True
                results.append(block)
            messages.append({"role": "user", "content": results})  # 결과는 한 번에 모아서
            continue
        ok = reply.stop_reason in ("end_turn", "stop_sequence")
        return AgentResult(spec.name, reply.text, ok, turn, reply.stop_reason, trace, reply.parsed)

    # 반복 상한에 닿음: 도구 없이 지금까지 정보로 마무리하게 한다 (호출 1번 추가)
    note = {"type": "text", "text": "도구 사용 횟수 한도에 닿았다. 더 조사하지 말고 지금까지 정보로 최종 답을 써라."}
    last = messages[-1]
    if last["role"] == "user" and isinstance(last["content"], list):
        last["content"].append(note)
    else:
        messages.append({"role": "user", "content": [note]})
    trace.append(f"(반복 상한 {spec.max_turns}회에 닿아 마무리 요청)")
    reply = call(tool_choice_none=True)
    messages.append({"role": "assistant", "content": reply.content})
    ok = reply.stop_reason in ("end_turn", "stop_sequence")
    return AgentResult(spec.name, reply.text, ok, spec.max_turns + 1, "turn_limit", trace, reply.parsed)
