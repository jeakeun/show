"""테스트 공용: 정해진 대본대로 답하는 모델."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agent_factory.llm import BaseLLM, Ledger, Reply, ToolCall, Usage
from agent_factory.spec import AgentSpec, Stage, TeamSpec


def text(t, stop="end_turn"):
    return Reply(content=[{"type": "text", "text": t}], stop_reason=stop, text=t)


def tool_use(name, args, id="t1"):
    call = ToolCall(id=id, name=name, input=args)
    return Reply(content=[{"type": "tool_use", "id": id, "name": name, "input": args}],
                 stop_reason="tool_use", text="", tool_calls=[call])


class ScriptedLLM(BaseLLM):
    """script(who, messages, tools, output_schema, tool_choice_none) -> Reply 또는 (Reply, Usage)."""

    def __init__(self, script, budget=10.0):
        super().__init__(Ledger(budget))
        self.script = script
        self.calls = []

    def _call(self, *, model, system, messages, tools, effort, output_schema, tool_choice_none, who):
        import copy
        self.calls.append(dict(who=who, model=model, system=system, messages=copy.deepcopy(messages),
                               tools=tools, schema=output_schema, tool_choice_none=tool_choice_none))
        r = self.script(who, messages, tools, output_schema, tool_choice_none)
        if isinstance(r, tuple):
            return r
        return r, Usage()


def agent(name, tools=(), model="sonnet", **kw):
    kw.setdefault("why_separate", f"{name} 는 다른 맥락이 필요한 이유가 있다")
    return AgentSpec(name=name, role=f"{name} 역할", model=model, tools=list(tools),
                     instructions=f"{name} 지시문", **kw)


def team(agents, stages, review=None, **kw):
    kw.setdefault("why_not_single", "여러 명이 필요한 충분히 긴 이유를 여기에 쓴다")
    return TeamSpec(name=kw.pop("name", "test-team"), situation=kw.pop("situation", "테스트 상황"),
                    agents=agents, stages=[Stage(agents=s) for s in stages], review=review, **kw)


@pytest.fixture
def ws_dir(tmp_path):
    d = tmp_path / "ws"
    d.mkdir()
    (d / "a.md").write_text("첫째 줄\n조회수 100\n셋째 줄\n", encoding="utf-8")
    (d / "sub").mkdir()
    (d / "sub" / "b.txt").write_text("조회수 200\n", encoding="utf-8")
    (d / ".env").write_text("ANTHROPIC_API_KEY=sk-secret\n", encoding="utf-8")
    (d / "secrets").mkdir()
    (d / "secrets" / "key.txt").write_text("secret\n", encoding="utf-8")
    (d / "my_token.json").write_text("{}", encoding="utf-8")
    return d
