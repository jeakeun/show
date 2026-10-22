"""설계 규칙 검사기 (4칸 중 ② 규칙 칸).

설계 에이전트가 낸 팀 설계도를 코드가 검사한다. 규칙을 어기면 실행하지 않고 설계 에이전트에게 돌려보낸다.
같은 RULES 목록이 설계 에이전트 지시문에도 그대로 들어가서, 프롬프트와 검사 코드가 어긋나지 않는다.

근거 문서: docs/멀티에이전트/01-개념.md, 02-내-설계결정-기록.md
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .spec import TeamSpec
from .tools import TOOLS

MAX_AGENTS = 6
MAX_STAGES = 5
MAX_PARALLEL = 4
MAX_TURNS = 12
MAX_ROUNDS = 3
MAX_BUDGET_USD = 3.0

TEAM_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


@dataclass(frozen=True)
class Rule:
    code: str
    title: str
    text: str
    why: str


RULES = [
    Rule("R01", "이름 형식",
         "팀 이름은 영문 소문자·숫자·하이픈, 에이전트 이름은 영문 소문자·숫자·밑줄. 이름은 겹치지 않는다.",
         "파일 이름·그래프 노드 이름으로 쓰인다."),
    Rule("R02", "있는 모델·도구만",
         "모델은 opus/sonnet/haiku 중에서, 도구는 도구 목록에 있는 것만. 도구마다 쓸 수 있는 모델을 지킨다.",
         "AI는 도구를 고를 수만 있고 새 권한을 만들 수 없다."),
    Rule("R03", "크기 상한",
         f"에이전트 최대 {MAX_AGENTS}명, 단계 최대 {MAX_STAGES}개, 한 단계에 동시에 최대 {MAX_PARALLEL}명.",
         "에이전트가 늘수록 비용과 맥락 단절이 커진다."),
    Rule("R04", "빠짐·중복 없음",
         "모든 에이전트는 단계 또는 검토자로 정확히 한 번 나온다. 검토자는 단계에 넣지 않는다.",
         "안 쓰는 에이전트, 두 번 일하는 에이전트는 설계 실수다."),
    Rule("R05", "혼자 먼저",
         "2명 이상이면 팀의 why_not_single 과 각 에이전트의 why_separate 를 채운다. "
         "'기획 담당·개발 담당' 같은 직함이 아니라 맥락 분리·다른 도구·견제·병렬 같은 이유로 쓴다.",
         "멀티 에이전트의 본질은 맥락 분리. 직함으로 나누면 넘길 때마다 맥락이 끊긴다 (01-개념 6절)."),
    Rule("R06", "병렬은 읽기만",
         "동시에 일하는 단계(2명 이상)의 에이전트는 읽기 도구만 가진다.",
         "읽기는 나눠도 충돌이 없다. 감사 에이전트 3기 병렬이 안전했던 이유 (ADR-06)."),
    Rule("R07", "쓰기는 한 곳",
         "쓰기·외부 행동 도구를 가진 에이전트는 최대 1명이고, 마지막 단계에 있어야 한다.",
         "생각은 여럿이 보태도 쓰기는 한 줄기로 (Cognition 2026, ADR-03)."),
    Rule("R08", "마무리는 한 명",
         "마지막 단계는 1명이다. 앞 단계 결과를 하나로 합치는 사람이 있어야 한다.",
         "여럿이 같은 결과물을 동시에 쓰면 말투·주장이 어긋난다."),
    Rule("R09", "검토자 분리",
         f"검토자는 쓰기·외부 행동 도구와 웹 검색이 없고, 통과 기준이 1개 이상이며, 검토 횟수는 1~{MAX_ROUNDS}회"
         "(1이면 판정만 하고 다시 쓰지 않음).",
         "만든 쪽과 검사하는 쪽을 나눈다. 같은 맥락에서는 자기 결과에 관대해진다 (ADR-05). "
         "검토 판정은 정해진 형식(JSON)으로 받는데 웹 검색의 인용 기능과 같이 쓸 수 없다."),
    Rule("R10", "반복 상한",
         f"각 에이전트의 max_turns 는 1~{MAX_TURNS}.",
         "끝없이 도는 루프를 막는다."),
    Rule("R11", "예산 상한",
         f"budget_usd 는 0보다 크고 {MAX_BUDGET_USD} 이하.",
         "비용은 호출마다 기록하고 상한을 넘으면 멈춘다 (ADR-08)."),
    Rule("R12", "웹과 내 파일은 따로",
         "web_search 를 가진 에이전트는 작업 폴더 읽기 도구(list_files·read_file·search_files)를 같이 가지지 않는다. "
         "웹 조사와 파일 조사는 다른 에이전트로 나눈다.",
         "웹 페이지에 숨은 지시가 내 파일 내용을 검색어에 실어 밖으로 내보내는 길을 막는다."),
]
WORKSPACE_READ_TOOLS = {"list_files", "read_file", "search_files"}


@dataclass
class Finding:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def rules_text() -> str:
    return "\n".join(f"- {r.code} {r.title}: {r.text} (이유: {r.why})" for r in RULES)


def _writes(team: TeamSpec, name: str) -> bool:
    if not team.has_agent(name):
        return False
    a = team.agent(name)
    return any(TOOLS[t].risk in ("write", "external") for t in a.tools if t in TOOLS)


def check(team: TeamSpec) -> list[Finding]:
    """규칙 위반 목록. 빈 목록이면 통과."""
    out: list[Finding] = []

    def bad(code, msg):
        out.append(Finding(code, msg))

    # R01 이름
    if not TEAM_NAME_RE.match(team.name or ""):
        bad("R01", f"팀 이름 '{team.name}' 은 영문 소문자·숫자·하이픈 2~41자여야 합니다")
    names = [a.name for a in team.agents]
    for n in names:
        if not AGENT_NAME_RE.match(n):
            bad("R01", f"에이전트 이름 '{n}' 은 영문 소문자로 시작하고 소문자·숫자·밑줄만 씁니다")
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        bad("R01", f"이름이 겹칩니다: {', '.join(dup)}")

    # R02 모델·도구
    for a in team.agents:
        for t in a.tools:
            tool = TOOLS.get(t)
            if tool is None:
                bad("R02", f"{a.name}: 없는 도구 '{t}'")
            elif tool.models and a.model not in tool.models:
                bad("R02", f"{a.name}: '{t}' 는 {'/'.join(sorted(tool.models))} 에서만 쓸 수 있습니다 (지금 {a.model})")
        if len(set(a.tools)) != len(a.tools):
            bad("R02", f"{a.name}: 도구가 중복으로 적혀 있습니다")

    # R03 크기
    if not team.agents:
        bad("R03", "에이전트가 한 명도 없습니다")
    if len(team.agents) > MAX_AGENTS:
        bad("R03", f"에이전트 {len(team.agents)}명 — 최대 {MAX_AGENTS}명")
    if not team.stages:
        bad("R03", "단계가 하나도 없습니다")
    if len(team.stages) > MAX_STAGES:
        bad("R03", f"단계 {len(team.stages)}개 — 최대 {MAX_STAGES}개")
    for i, st in enumerate(team.stages, 1):
        if not st.agents:
            bad("R03", f"{i}단계가 비었습니다")
        if len(st.agents) > MAX_PARALLEL:
            bad("R03", f"{i}단계에 동시에 {len(st.agents)}명 — 최대 {MAX_PARALLEL}명")

    # R04 빠짐·중복
    used = [n for st in team.stages for n in st.agents]
    if team.review:
        used.append(team.review.reviewer)
    for n in sorted(set(used)):
        if not team.has_agent(n):
            bad("R04", f"'{n}' 이 단계·검토에 나오지만 에이전트 목록에 없습니다")
    for n in names:
        c = used.count(n)
        if c == 0:
            bad("R04", f"'{n}' 은 어느 단계에도, 검토자로도 쓰이지 않습니다")
        elif c > 1:
            bad("R04", f"'{n}' 이 {c}번 나옵니다 (한 번만)")
    if not team.stages or not team.agents:
        return out  # 빈 팀은 뒤 검사가 의미 없음

    # R05 혼자 먼저
    if len(team.agents) > 1:
        if len(team.why_not_single.strip()) < 15:
            bad("R05", "2명 이상인데 why_not_single(1명으로 안 되는 이유)이 비었거나 너무 짧습니다")
        for a in team.agents:
            if len(a.why_separate.strip()) < 10:
                bad("R05", f"{a.name}: why_separate(따로 맥락을 가져야 하는 이유)가 비었거나 너무 짧습니다")

    # R06 병렬은 읽기만
    for i, st in enumerate(team.stages, 1):
        if len(st.agents) > 1:
            for n in st.agents:
                if _writes(team, n):
                    bad("R06", f"{i}단계는 동시에 일하는 단계인데 {n} 이 쓰기 도구를 가졌습니다")

    # R07 쓰기는 한 곳 / R08 마무리는 한 명
    writers = [a.name for a in team.agents if _writes(team, a.name)]
    if len(writers) > 1:
        bad("R07", f"쓰기 도구를 가진 에이전트가 {len(writers)}명입니다: {', '.join(writers)} (최대 1명)")
    last = team.stages[-1].agents
    for w in writers:
        if w not in last:
            bad("R07", f"{w} 은 쓰기 도구를 가졌는데 마지막 단계가 아닙니다")
    if len(last) != 1:
        bad("R08", f"마지막 단계에 {len(last)}명 — 결과를 합칠 1명이어야 합니다")

    # R09 검토자 분리
    if team.review:
        r = team.review
        if _writes(team, r.reviewer):
            bad("R09", f"검토자 {r.reviewer} 가 쓰기 도구를 가졌습니다")
        if team.has_agent(r.reviewer) and "web_search" in team.agent(r.reviewer).tools:
            bad("R09", f"검토자 {r.reviewer} 는 web_search 를 쓸 수 없습니다 (판정 형식과 함께 못 씀)")
        if not [c for c in r.criteria if c.strip()]:
            bad("R09", "검토 기준(criteria)이 없습니다")
        if not 1 <= r.max_rounds <= MAX_ROUNDS:
            bad("R09", f"검토 횟수 {r.max_rounds} — 1~{MAX_ROUNDS}회")

    # R10 반복 상한
    for a in team.agents:
        if not 1 <= a.max_turns <= MAX_TURNS:
            bad("R10", f"{a.name}: max_turns {a.max_turns} — 1~{MAX_TURNS}")

    # R11 예산
    if not 0 < team.budget_usd <= MAX_BUDGET_USD:
        bad("R11", f"예산 ${team.budget_usd} — 0 초과 ${MAX_BUDGET_USD} 이하")

    # R12 웹과 내 파일은 따로
    for a in team.agents:
        both = WORKSPACE_READ_TOOLS & set(a.tools)
        if "web_search" in a.tools and both:
            bad("R12", f"{a.name}: web_search 와 {', '.join(sorted(both))} 를 같이 가졌습니다. 웹 조사와 파일 조사를 나누세요")

    return out


def warnings(team: TeamSpec) -> list[str]:
    """막지는 않지만 사람이 알아야 할 것."""
    w = []
    if len(team.agents) >= 4:
        w.append(f"에이전트 {len(team.agents)}명: 비용과 맥락 단절이 커집니다. 더 줄일 수 있는지 보세요.")
    opus = [a.name for a in team.agents if a.model == "opus"]
    if len(opus) >= 3:
        w.append(f"opus {len(opus)}명({', '.join(opus)}): 단순한 칸은 sonnet/haiku 로 낮출 수 있는지 보세요.")
    if any("web_search" in a.tools for a in team.agents):
        w.append("웹 검색을 씁니다: 검색 1회 약 $0.01 + 검색 결과만큼 입력 비용이 더 듭니다.")
    if not any("calculate" in a.tools for a in team.agents):
        w.append("계산기(calculate)를 가진 에이전트가 없습니다. 숫자를 다루는 일이면 넣으세요 (숫자는 코드가 계산).")
    return w
