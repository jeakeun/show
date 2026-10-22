"""명령어 화면.

  python -m agent_factory                       메뉴로 진행 (처음이면 이것)
  python -m agent_factory design "상황 설명"     상황에 맞는 팀 설계 → 저장 → (물어보고) 실행
  python -m agent_factory run 팀이름 [--task ..] 저장된 팀 실행
  python -m agent_factory check 팀이름            설계 규칙 검사만
  python -m agent_factory show 팀이름             설계도 요약 보기
  python -m agent_factory list                   팀·도구·모델 목록

공통 옵션: --demo (API 키 없이 가짜 모델로 흐름만), --workspace 폴더 (에이전트가 읽을 폴더)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import rules
from .designer import Design, DesignError, design_team
from .llm import MODELS, AnthropicLLM, BaseLLM, BudgetExceeded, Ledger, LLMError, find_api_key
from .spec import SpecError, TeamSpec, load_team, save_team, team_to_yaml
from .team import new_run_dir, run_team, team_mermaid
from .tools import TOOLS, Workspace, list_files

ROOT = Path(__file__).resolve().parent.parent
TEAMS_DIR = ROOT / "teams"
RUNS_DIR = ROOT / "runs"
SAMPLE_WS = ROOT / "sample-workspace"
DESIGN_BUDGET_USD = 1.0
LINE = "-" * 60


def make_llm(demo: bool, budget: float, ledger_path: Optional[Path] = None) -> BaseLLM:
    ledger = Ledger(budget, ledger_path)
    if demo:
        from .demo import DemoLLM

        return DemoLLM(ledger)
    return AnthropicLLM(ledger)


# ---------------------------------------------------------------- 보여주기

def describe(team: TeamSpec) -> str:
    out = [f"팀: {team.name}", f"구조: {team.shape()}", f"상황: {team.situation.strip()[:300]}"]
    if len(team.agents) > 1:
        out.append(f"1명으로 안 되는 이유: {team.why_not_single.strip()}")
    for i, st in enumerate(team.stages, 1):
        out.append(f"\n[{i}단계]" + (" 동시에 실행" if len(st.agents) > 1 else ""))
        for n in st.agents:
            out.append(_agent_line(team, n))
    if team.review:
        r = team.review
        out.append(f"\n[검토] 최대 {r.max_rounds}회, 미통과면 마지막 작성자가 다시 씀")
        out.append(_agent_line(team, r.reviewer))
        out.append("    기준: " + " / ".join(r.criteria))
    out.append(f"\n예산 상한: ${team.budget_usd:.2f} (넘으면 자동으로 멈춤)")
    return "\n".join(out)


def _agent_line(team: TeamSpec, name: str) -> str:
    try:
        a = team.agent(name)
    except KeyError:
        return f"  - {name} (에이전트 목록에 없음)"
    tools = ", ".join(a.tools) or "도구 없음"
    s = f"  - {a.name} [{a.model}, 생각 {a.effort}, 최대 {a.max_turns}회] {a.role}\n    도구: {tools}"
    if a.why_separate.strip() and len(team.agents) > 1:
        s += f"\n    따로 둔 이유: {a.why_separate.strip()}"
    return s


def show_check(team: TeamSpec) -> bool:
    problems = rules.check(team)
    if problems:
        print(f"\n규칙 검사: 위반 {len(problems)}건 (실행하지 않습니다)")
        for p in problems:
            print(f"  {p}")
    else:
        print(f"\n규칙 검사: 통과 ({len(rules.RULES)}개 규칙)")
    for w in rules.warnings(team):
        print(f"  주의: {w}")
    return not problems


def ask_yes(question: str) -> bool:
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes", "ㅇ", "네", "예")
    except EOFError:
        return False


def approver(agent: str, tool: str, args: dict) -> bool:
    print(f"\n{LINE}\n{agent} 가 되돌릴 수 없는 행동을 하려고 합니다: {tool}\n입력: {args}")
    return ask_yes("허락할까요?")


def resolve_team_path(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        return p
    cand = TEAMS_DIR / (arg if arg.endswith(".yaml") else f"{arg}.yaml")
    return cand


def workspace_listing(ws_root: Path, limit: int = 60) -> str:
    try:
        text = list_files(Workspace(ws_root, ws_root), {"path": "."})
    except Exception:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[:limit]) + (f"\n... (전체 {len(lines)}개 중 {limit}개)" if len(lines) > limit else "")


def unique_team_path(name: str) -> Path:
    p = TEAMS_DIR / f"{name}.yaml"
    n = 2
    while p.exists():
        p = TEAMS_DIR / f"{name}-{n}.yaml"
        n += 1
    return p


def check_key(demo: bool) -> bool:
    if demo:
        return True
    key, where = find_api_key()
    if key:
        print(f"(API 키: {where} 에서 찾음)")
        return True
    print("API 키를 찾지 못했습니다. agent-factory/.env 파일에 ANTHROPIC_API_KEY=... 한 줄을 넣거나,")
    print("돈 안 드는 데모로 먼저 보려면 --demo 를 붙이세요.")
    return False


# ---------------------------------------------------------------- 명령

def cmd_design(situation: str, ws_root: Path, demo: bool, yes: bool, run_after: Optional[bool], critic: bool) -> int:
    if not situation.strip():
        print("상황 설명이 비었습니다.")
        return 2
    if not check_key(demo):
        return 2
    rec_dir = new_run_dir(RUNS_DIR, "design")
    llm = make_llm(demo, DESIGN_BUDGET_USD, rec_dir / "ledger.jsonl")
    print(LINE)
    try:
        d: Design = design_team(llm, situation, listing=workspace_listing(ws_root), use_critic=critic, on_event=print)
    except DesignError as e:
        print(f"\n설계 실패: {e}")
        for f in e.findings:
            print(f"  {f}")
        return 1
    except (LLMError, BudgetExceeded) as e:
        print(f"\n설계 중 오류: {e}")
        return 1

    team = d.team
    path = unique_team_path(team.name)
    if path.stem != team.name:
        team.name = path.stem
    save_team(team, path)
    rec_dir.mkdir(parents=True, exist_ok=True)
    crit = ""
    if d.critique:
        c = d.critique
        crit = (f"\n## 검토 의견 ({c.verdict}{', 반영함' if d.critique_applied else ''})\n"
                + "".join(f"- 문제: {x}\n" for x in c.problems) + "".join(f"- 참고: {x}\n" for x in c.notes)
                + (f"- 더 단순한 대안: {c.simpler_alternative}\n" if c.simpler_alternative else ""))
    (rec_dir / "design_log.md").write_text(
        f"# 설계 기록 — {team.name}\n\n## 상황\n{situation}\n\n## 과정\n" + "\n".join(f"- {x}" for x in d.log)
        + f"\n{crit}\n## 최종 설계도\n```yaml\n{team_to_yaml(team)}```\n",
        encoding="utf-8",
    )

    print(f"\n{LINE}\n설계 결과\n{LINE}")
    print(describe(team))
    show_check(team)
    if d.critique:
        c = d.critique
        tag = "고칠 점을 지적 → 반영함" if d.critique_applied else ("좋음" if c.verdict == "ok" else "지적 있음")
        print(f"\n검토 에이전트 의견: {tag}")
        for x in c.problems:
            print(f"  - 문제: {x}")
        for x in c.notes:
            print(f"  - 참고: {x}")
        if c.simpler_alternative:
            print(f"  - 더 단순한 대안: {c.simpler_alternative}")
    print(f"\n설계 비용: ${llm.ledger.total_usd:.4f}{' (데모라 0)' if demo else ''}")
    print(f"저장한 설계도: {path}")
    print(f"설계 기록: {rec_dir / 'design_log.md'}")

    if run_after is False:
        return 0
    if run_after is None and not yes and not ask_yes("\n이 팀으로 지금 실행할까요?"):
        print(f"나중에 실행: python -m agent_factory run {team.name}")
        return 0
    return cmd_run(str(path), None, ws_root, demo, yes=True, checked=True)


def cmd_run(team_arg: str, task: Optional[str], ws_root: Path, demo: bool, yes: bool, checked: bool = False) -> int:
    try:
        team = load_team(resolve_team_path(team_arg))
    except SpecError as e:
        print(e)
        return 2
    if rules.check(team) if checked else not show_check(team):  # 방금 설계에서 검사 결과를 보여줬으면 다시 출력하지 않음
        return 1
    if not check_key(demo):
        return 2
    task = (task or team.situation).strip()
    if not yes:
        print(f"\n작업: {task[:200]}\n읽을 폴더: {ws_root}\n예산 상한: ${team.budget_usd:.2f}")
        if not ask_yes("실행할까요?"):
            return 0
    llm = make_llm(demo, team.budget_usd)
    print(f"\n{LINE}\n실행: {team.name} ({team.shape()})\n{LINE}")
    try:
        res = run_team(team, task, llm, read_root=ws_root, runs_root=RUNS_DIR, approver=approver, on_event=print)
    except ValueError as e:
        print(e)
        return 1
    print(f"\n{LINE}")
    if res.stopped:
        print(f"중간에 멈춤: {res.stopped}")
    review = ""
    if team.review:
        review = {True: "통과", False: "미통과(결과 파일에 표시)", None: "판정 없음"}[res.review_passed]
        review = f" / 검토 {review} ({res.review_rounds}회)"
    print(f"끝: {res.seconds:.1f}초 / 비용 ${res.ledger.total_usd:.4f}{' (데모라 0)' if demo else ''}{review}")
    print(f"결과 파일: {res.run_dir / 'result.md'}")
    print(f"실행 기록 폴더: {res.run_dir}")
    preview = res.final_text.strip().splitlines()
    if preview:
        print(f"\n--- 결과 앞부분 ({res.final_agent}) ---")
        print("\n".join(preview[:30]) + ("\n..." if len(preview) > 30 else ""))
    return 0 if not res.stopped else 1


def cmd_check(team_arg: str) -> int:
    try:
        team = load_team(resolve_team_path(team_arg))
    except SpecError as e:
        print(e)
        return 2
    print(describe(team))
    return 0 if show_check(team) else 1


def cmd_show(team_arg: str) -> int:
    try:
        team = load_team(resolve_team_path(team_arg))
    except SpecError as e:
        print(e)
        return 2
    print(describe(team))
    show_check(team)
    if not rules.check(team):
        print("\n팀 그림 (mermaid — 깃허브·노션에 붙이면 그림으로 보임):")
        print(team_mermaid(team))
    return 0


def cmd_list() -> int:
    print("저장된 팀 (teams/):")
    files = sorted(TEAMS_DIR.glob("*.yaml"))
    for f in files:
        try:
            t = load_team(f)
            ok = "통과" if not rules.check(t) else "규칙 위반"
            print(f"  - {f.stem}: {t.shape()} [{ok}] — {t.situation.strip().splitlines()[0][:60]}")
        except SpecError:
            print(f"  - {f.stem}: (형식 오류)")
    if not files:
        print("  (없음)")
    print("\n도구:")
    for t in TOOLS.values():
        print(f"  - {t.name} [{t.risk}] {t.summary}")
    print("\n모델:")
    for m in MODELS.values():
        print(f"  - {m.alias} ({m.id}): {m.note}, 100만 토큰당 ${m.input_usd}/${m.output_usd}")
    print("\n설계 규칙:")
    for r in rules.RULES:
        print(f"  - {r.code} {r.title}: {r.text}")
    return 0


def interactive(demo: bool) -> int:
    print(LINE)
    print("에이전트 공장 — 상황을 설명하면 그 일에 맞는 에이전트 팀을 설계하고 실행합니다.")
    if demo:
        print("(데모 모드: 가짜 모델, 비용 0)")
    print(LINE)
    print("1) 새 팀 설계 (상황 설명)\n2) 저장된 팀 실행\n3) 목록 보기 (팀·도구·모델·규칙)\nq) 끝내기")
    try:
        choice = input("번호: ").strip()
    except EOFError:
        return 0
    if choice == "3":
        return cmd_list()
    if choice not in ("1", "2"):
        return 0
    ws = input(f"에이전트가 읽을 폴더 (엔터 = 예제 폴더 {SAMPLE_WS.name}): ").strip().strip('"')
    ws_root = Path(ws) if ws else SAMPLE_WS
    if not ws_root.is_dir():
        print(f"폴더가 없습니다: {ws_root}")
        return 2
    if choice == "1":
        print("어떤 상황인가요? 한 줄로 쓰고 엔터. 예: 이 폴더의 주간 리포트들을 비교해서 잘된 점·못된 점을 정리해줘")
        situation = input("> ").strip()
        return cmd_design(situation, ws_root, demo, yes=False, run_after=None, critic=True)
    files = sorted(TEAMS_DIR.glob("*.yaml"))
    for i, f in enumerate(files, 1):
        print(f"  {i}) {f.stem}")
    pick = input("팀 번호: ").strip()
    if not pick.isdigit() or not 1 <= int(pick) <= len(files):
        return 0
    task = input("작업 내용 (엔터 = 설계도의 상황 그대로): ").strip() or None
    return cmd_run(str(files[int(pick) - 1]), task, ws_root, demo, yes=False)


def main(argv: Optional[list] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 윈도우 콘솔 한글
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="agent_factory", description="상황에 맞는 에이전트 팀을 설계하고 실행합니다.")
    ap.add_argument("--demo", action="store_true", help="API 키 없이 가짜 모델로 흐름만 보기 (비용 0)")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--demo", action="store_true", default=argparse.SUPPRESS, help="가짜 모델 (비용 0)")
        p.add_argument("--workspace", default=str(SAMPLE_WS), help="에이전트가 읽을 폴더")

    p = sub.add_parser("design", help="상황에 맞는 팀 설계")
    p.add_argument("situation")
    common(p)
    p.add_argument("--yes", action="store_true", help="묻지 않고 바로 실행")
    p.add_argument("--no-run", action="store_true", help="설계만 하고 실행하지 않음")
    p.add_argument("--no-critic", action="store_true", help="설계 검토 에이전트 건너뛰기")
    p = sub.add_parser("run", help="저장된 팀 실행")
    p.add_argument("team")
    p.add_argument("--task", default=None, help="작업 내용 (없으면 설계도의 상황)")
    common(p)
    p.add_argument("--yes", action="store_true", help="묻지 않고 실행")
    p = sub.add_parser("check", help="설계 규칙 검사")
    p.add_argument("team")
    p = sub.add_parser("show", help="설계도 요약·흐름도")
    p.add_argument("team")
    sub.add_parser("list", help="팀·도구·모델·규칙 목록")

    a = ap.parse_args(argv)
    demo = bool(getattr(a, "demo", False))
    if a.cmd is None:
        return interactive(demo)
    if a.cmd == "list":
        return cmd_list()
    if a.cmd == "check":
        return cmd_check(a.team)
    if a.cmd == "show":
        return cmd_show(a.team)
    ws_root = Path(a.workspace)
    if not ws_root.is_dir():
        print(f"읽을 폴더가 없습니다: {ws_root}")
        return 2
    if a.cmd == "design":
        run_after = False if a.no_run else (True if a.yes else None)
        return cmd_design(a.situation, ws_root, demo, a.yes, run_after, critic=not a.no_critic)
    if a.cmd == "run":
        return cmd_run(a.team, a.task, ws_root, demo, a.yes)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
