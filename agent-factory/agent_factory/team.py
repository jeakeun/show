"""팀 설계도(TeamSpec) → LangGraph 흐름도 → 실행.

- 단계는 순서대로. 앞 단계 결과만 다음 단계로 넘긴다 (맥락 보호: 각자 필요한 것만 본다).
- 2명 이상 단계는 LangGraph Send 로 동시에 실행하고, 합류 노드(sN_join)에서 모두 끝나길 기다린 뒤
  다음 단계가 결과를 모아 받는다. (합류 노드가 없으면 병렬→병렬 구조에서 다음 단계가 앞 단계 인원수만큼 중복 실행된다)
- 검토가 있으면 마지막 단계 결과를 검토자가 판정 → 고칠 게 있으면 같은 작성자가 다시 쓴다 (최대 횟수까지).
- 실행 기록은 runs/<시각>-<팀이름>/ 폴더에 남긴다.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from .agent import AgentResult, run_agent
from .llm import BaseLLM, FormatError, Ledger, LLMError, Stopped
from .rules import check
from .spec import TeamSpec, save_team
from .tools import Workspace


class ReviewVerdict(BaseModel):
    passed: bool = Field(description="모든 기준을 통과하면 true")
    issues: list[str] = Field(description="고쳐야 할 점. 어느 부분이 왜 문제인지 구체적으로. 통과면 빈 목록")
    summary: str = Field(description="한 줄 판정 이유")


def _merge(a: Optional[dict], b: Optional[dict]) -> dict:
    return {**(a or {}), **(b or {})}


class TeamState(TypedDict, total=False):
    task: str
    outputs: Annotated[dict, _merge]  # 에이전트 이름 → 최신 결과 글
    round: int  # 검토 횟수
    passed: Optional[bool]
    issues: list


class WorkerInput(TypedDict):
    agent: str
    task: str
    inputs: dict


@dataclass
class RunResult:
    run_dir: Path
    final_text: str
    final_agent: str
    final_ok: bool
    review_passed: Optional[bool]
    review_rounds: int
    stopped: Optional[str]
    ledger: Ledger
    seconds: float
    results: dict = field(default_factory=dict)


def compose_input(task: str, inputs: dict, draft: str = "", issues: Optional[list] = None) -> str:
    parts = [f"## 작업\n{task.strip()}"]
    if inputs:
        parts.append("## 앞 단계 결과")
        for name, (role, text) in inputs.items():
            parts.append(f'<결과 에이전트="{name}" 역할="{role}">\n{text.strip()}\n</결과>')
    if draft:
        parts.append(f"## 네가 쓴 직전 결과\n{draft.strip()}")
        parts.append("## 검토자가 고치라고 한 점\n" + "\n".join(f"- {x}" for x in issues or []))
        parts.append("위 지적을 모두 반영해서 결과 전체를 다시 써라.")
    return "\n\n".join(parts)


class TeamRunner:
    def __init__(
        self,
        team: TeamSpec,
        llm: BaseLLM,
        ws: Workspace,
        run_dir: Path,
        *,
        approver: Optional[Callable[[str, str, dict], bool]] = None,
        on_event: Optional[Callable[[str], None]] = None,
    ):
        self.team = team
        self.llm = llm
        self.ws = ws
        self.run_dir = run_dir
        self.approver = approver
        self.say = on_event or (lambda s: None)
        problems = check(team)
        if problems:  # 검사를 안 거친 설계도가 들어와도 실행하지 않는다
            raise ValueError("설계 규칙 위반:\n" + "\n".join(str(p) for p in problems))
        self.results: dict[str, AgentResult] = {}
        self._lock = threading.Lock()
        self._seq = 0
        self.app = self._build()

    # ------------------------------------------------------------ 기록

    def _save_agent(self, label: str, res: AgentResult, user_content: str) -> None:
        with self._lock:
            self._seq += 1
            seq = self._seq
            self.results[res.name] = res
        d = self.run_dir / "agents"
        d.mkdir(parents=True, exist_ok=True)
        trace = "\n".join(f"- {t}" for t in res.trace) or "- (도구 안 씀)"
        body = (
            f"# {label}\n\n- 상태: {'정상' if res.ok else '문제 있음'} ({res.stop_reason}), 모델 호출 {res.turns}회\n\n"
            f"## 도구 사용\n{trace}\n\n## 결과\n{res.text}\n\n"
            f"<details><summary>받은 입력</summary>\n\n```\n{user_content}\n```\n</details>\n"
        )
        (d / f"{seq:02d}-{label}.md").write_text(body, encoding="utf-8")

    def _inputs_for(self, stage_idx: int, outputs: dict) -> dict:
        if stage_idx == 0:
            return {}
        prev = self.team.stages[stage_idx - 1].agents
        return {n: (self.team.agent(n).role, outputs.get(n, "(결과 없음)")) for n in prev}

    # ------------------------------------------------------------ 노드

    def _run_one(self, name: str, task: str, inputs: dict, label: str, draft="", issues=None) -> AgentResult:
        spec = self.team.agent(name)
        self.say(f"[{label}] {name} 시작 ({spec.model}, {spec.role})")
        content = compose_input(task, inputs, draft, issues)
        try:
            res = run_agent(self.llm, spec, content, self.ws, approver=self.approver, on_event=self.say)
        except (Stopped, LLMError) as e:  # 멈춰도 여기까지 받은 입력은 기록에 남긴다
            self._save_agent(label, AgentResult(name, f"(중단됨: {e})", False, 0, "stopped"), content)
            raise
        self._save_agent(label, res, content)
        self.say(f"[{label}] {name} 끝 (모델 호출 {res.turns}회{'' if res.ok else ', 문제: ' + res.stop_reason})")
        return res

    def _single_node(self, stage_idx: int, name: str):
        is_last = stage_idx == len(self.team.stages) - 1

        def node(state: TeamState) -> dict:
            inputs = self._inputs_for(stage_idx, state.get("outputs", {}))
            draft, issues, label = "", None, f"{stage_idx + 1}단계-{name}"
            if is_last and state.get("round", 0) > 0 and state.get("passed") is False:
                draft = state["outputs"].get(name, "")
                issues = state.get("issues", [])
                label = f"{stage_idx + 1}단계-{name}-다시쓰기{state['round']}"
            res = self._run_one(name, state["task"], inputs, label, draft, issues)
            return {"outputs": {name: res.text}}

        return node

    def _parallel_worker(self, stage_idx: int):
        def worker(inp: WorkerInput) -> dict:
            res = self._run_one(inp["agent"], inp["task"], inp["inputs"], f"{stage_idx + 1}단계-{inp['agent']}")
            return {"outputs": {inp["agent"]: res.text}}

        return worker

    def _fan_out(self, stage_idx: int, node_name: str):
        def fan(state: TeamState) -> list:
            inputs = self._inputs_for(stage_idx, state.get("outputs", {}))
            return [
                Send(node_name, {"agent": n, "task": state["task"], "inputs": inputs})
                for n in self.team.stages[stage_idx].agents
            ]

        return fan

    def _review_node(self):
        rv = self.team.review
        last_stage = len(self.team.stages) - 1
        writer = self.team.stages[-1].agents[0]

        def node(state: TeamState) -> dict:
            rnd = state.get("round", 0) + 1
            spec = self.team.agent(rv.reviewer)
            evidence = self._inputs_for(last_stage, state.get("outputs", {}))
            content = compose_input(state["task"], evidence) + (
                "\n\n## 검토 기준\n" + "\n".join(f"- {c}" for c in rv.criteria)
                + f"\n\n## 검토할 결과 ({writer} 작성)\n{state['outputs'].get(writer, '')}"
                + "\n\n기준마다 확인하고 passed / issues / summary 형식으로 판정하라. "
                  "고칠 점은 작성자가 바로 고칠 수 있게 구체적으로 쓴다."
            )
            label = f"검토{rnd}-{rv.reviewer}"
            self.say(f"[검토 {rnd}회차] {rv.reviewer} 시작 ({spec.model})")
            try:
                res = run_agent(self.llm, spec, content, self.ws, approver=self.approver,
                                output_schema=ReviewVerdict, on_event=self.say)
            except FormatError as e:  # 판정 형식 오류 → 결과는 내보내되 표시 (fail-open)
                res = AgentResult(rv.reviewer, f"(검토 판정 형식 오류: {e})", False, 0, "format_error")
            except (Stopped, LLMError) as e:
                self._save_agent(label, AgentResult(rv.reviewer, f"(중단됨: {e})", False, 0, "stopped"), content)
                raise
            self._save_agent(label, res, content)
            if rv.reviewer in self.results:
                del self.results[rv.reviewer]  # 검토자의 문제는 판정 칸에서 따로 보여준다
            v: Optional[ReviewVerdict] = res.parsed
            if v is None:  # 검토가 형식대로 답하지 못함 → 결과는 내보내되 표시 (fail-open)
                self.say(f"[검토 {rnd}회차] 판정을 읽지 못함 → 검토 없이 마무리")
                return {"round": rnd, "passed": None, "issues": ["검토자가 판정을 내지 못했습니다"]}
            mark = "통과" if v.passed else f"수정 필요 {len(v.issues)}건"
            self.say(f"[검토 {rnd}회차] {mark} — {v.summary}")
            return {"round": rnd, "passed": v.passed, "issues": list(v.issues)}

        return node

    # ------------------------------------------------------------ 그래프

    def _build(self):
        t = self.team
        g = StateGraph(TeamState)
        prev = START
        last_node = None
        for i, st in enumerate(t.stages):
            if len(st.agents) == 1:
                node = f"s{i + 1}_{st.agents[0]}"
                g.add_node(node, self._single_node(i, st.agents[0]))
                g.add_edge(prev, node)
            else:
                par = f"s{i + 1}_parallel"
                g.add_node(par, self._parallel_worker(i))
                g.add_conditional_edges(prev, self._fan_out(i, par), [par])
                node = f"s{i + 1}_join"  # 동시에 돈 일이 모두 끝나야 한 번 지나가는 합류 지점
                g.add_node(node, lambda state: {})
                g.add_edge(par, node)
            prev = node
            last_node = node
        if t.review:
            rnode = f"review_{t.review.reviewer}"
            g.add_node(rnode, self._review_node())
            g.add_edge(last_node, rnode)
            max_rounds = t.review.max_rounds

            def route(state: TeamState) -> str:
                if state.get("passed") is False and state.get("round", 0) < max_rounds:
                    return "again"
                return "done"

            g.add_conditional_edges(rnode, route, {"again": last_node, "done": END})
        else:
            g.add_edge(last_node, END)
        return g.compile()

    def mermaid(self) -> str:
        return self.app.get_graph().draw_mermaid()

    # ------------------------------------------------------------ 실행

    def run(self, task: str) -> RunResult:
        t0 = time.time()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        save_team(self.team, self.run_dir / "team.yaml")
        (self.run_dir / "flow.md").write_text(
            f"# {self.team.name} 흐름도\n\n구조: {self.team.shape()}\n\n## 팀 그림\n\n```mermaid\n{team_mermaid(self.team)}\n```\n\n"
            f"## LangGraph 가 실제로 만든 그래프\n\n"
            f"병렬 단계는 노드 하나(sN_parallel)를 Send 로 여러 번 동시에 실행합니다.\n\n```mermaid\n{self.mermaid()}\n```\n",
            encoding="utf-8",
        )
        stopped = None
        state: dict = {}
        try:
            # 단계가 끝날 때마다 상태를 받아 두면, 중간에 멈춰도 그때까지의 검토 횟수·결과가 남는다
            for snapshot in self.app.stream({"task": task, "outputs": {}, "round": 0}, {"recursion_limit": 50},
                                            stream_mode="values"):
                state = snapshot
        except Stopped as e:
            stopped = str(e)
        except LLMError as e:
            stopped = f"모델 호출 오류: {e}"
        except KeyboardInterrupt:
            self.llm.ledger.cancel()  # 동시에 도는 에이전트도 다음 호출 전에 멈춤
            stopped = "사용자가 멈춤 (Ctrl+C). 진행 중이던 호출은 끝까지 기다렸다가 멈춥니다"
        final_agent = self.team.stages[-1].agents[0] if self.team.stages else ""
        final = self.results.get(final_agent)
        final_text = final.text if final else ""
        passed = state.get("passed") if self.team.review else None
        rounds = state.get("round", 0)
        res = RunResult(
            run_dir=self.run_dir, final_text=final_text, final_agent=final_agent,
            final_ok=bool(final and final.ok),
            review_passed=passed, review_rounds=rounds, stopped=stopped, ledger=self.llm.ledger,
            seconds=time.time() - t0, results=dict(self.results),
        )
        self._write_result(task, res, state)
        return res

    def _write_result(self, task: str, res: RunResult, state: dict) -> None:
        warn = []
        if res.stopped:
            warn.append(f"> ⚠ 중간에 멈춤: {res.stopped}")
        if self.team.review and not res.stopped:
            if res.review_passed is False:
                left = "\n".join(f">   - {x}" for x in state.get("issues", []))
                warn.append(f"> ⚠ 검토 {res.review_rounds}회 모두 통과하지 못한 결과입니다. 남은 지적:\n{left}")
            elif res.review_passed is None:
                warn.append("> ⚠ 검토자가 판정을 내지 못해 검토 없이 나온 결과입니다.")
        not_ok = [n for n, r in res.results.items() if not r.ok]
        if not_ok:
            warn.append(f"> ⚠ 정상적으로 끝나지 않은 에이전트: {', '.join(not_ok)} (agents/ 폴더 기록 참고)")
        if self.llm.demo:
            warn.append("> (데모 모드: 실제 AI가 아니라 정해진 가짜 답입니다)")
        head = "\n".join(warn) + ("\n\n" if warn else "")
        (self.run_dir / "result.md").write_text(
            f"# 결과 — {self.team.name}\n\n{head}{res.final_text or '(결과 없음)'}\n", encoding="utf-8"
        )
        rows = [f"| {who} | {a['calls']} | {a['input']:,} | {a['output']:,} | ${a['usd']:.4f} |"
                for who, a in res.ledger.by_agent().items()]
        review = "없음"
        if self.team.review:
            review = {True: "통과", False: "미통과", None: "판정 없음"}[res.review_passed] + f" ({res.review_rounds}회)"
        summary = (
            f"# 실행 요약 — {self.team.name}\n\n"
            f"- 작업: {task.strip()[:300]}\n- 구조: {self.team.shape()}\n"
            f"- 걸린 시간: {res.seconds:.1f}초\n- 검토: {review}\n"
            f"- 총비용: ${res.ledger.total_usd:.4f} (예산 ${self.team.budget_usd:.2f})"
            + (" — 데모라 0" if self.llm.demo else "") + "\n"
            + (f"- 멈춘 이유: {res.stopped}\n" if res.stopped else "")
            + "\n| 에이전트 | 호출 | 입력 토큰 | 출력 토큰 | 비용 |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
        )
        (self.run_dir / "summary.md").write_text(summary, encoding="utf-8")


def team_mermaid(team: TeamSpec) -> str:
    """사람이 보는 팀 그림 (단계·병렬·검토 루프). 노드 id 는 ag_ 를 붙여 mermaid 예약어(end 등)와 겹치지 않게."""
    def nid(name: str) -> str:
        return f"ag_{name}"

    def box(name: str) -> str:
        a = team.agent(name)
        role = a.role.replace('"', "'")[:20]
        return f'{nid(name)}["{name}<br/>{a.model} · {role}"]'

    lines = ["graph TD", '  start(["시작"])']
    prev = ["start"]
    for i, st in enumerate(team.stages, 1):
        if len(st.agents) > 1:
            lines.append(f'  subgraph s{i} ["{i}단계 · 동시에"]')
            lines += [f"    {box(n)}" for n in st.agents]
            lines.append("  end")
        else:
            lines.append(f"  {box(st.agents[0])}")
        lines += [f"  {p_} --> {nid(n)}" for p_ in prev for n in st.agents]
        prev = [nid(n) for n in st.agents]
    lines.append('  finish(["끝"])')
    if team.review:
        r = nid(team.review.reviewer)
        lines.append(f'  {r}{{{{"{team.review.reviewer}<br/>검토 · 최대 {team.review.max_rounds}회"}}}}')
        lines += [f"  {prev[0]} --> {r}", f"  {r} -- 수정 필요 --> {prev[0]}", f"  {r} -- 통과 --> finish"]
    else:
        lines += [f"  {p_} --> finish" for p_ in prev]
    return "\n".join(lines)


def new_run_dir(runs_root: Path, team_name: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    d = runs_root / f"{stamp}-{team_name}"
    n = 2
    while d.exists():
        d = runs_root / f"{stamp}-{team_name}-{n}"
        n += 1
    return d


def run_team(
    team: TeamSpec,
    task: str,
    llm: BaseLLM,
    *,
    read_root: Path,
    runs_root: Path,
    approver=None,
    on_event=None,
) -> RunResult:
    run_dir = new_run_dir(runs_root, team.name)
    if llm.ledger.path is None:
        llm.ledger.path = run_dir / "ledger.jsonl"
    ws = Workspace(read_root=read_root, out_dir=run_dir)
    runner = TeamRunner(team, llm, ws, run_dir, approver=approver, on_event=on_event)
    return runner.run(task)
