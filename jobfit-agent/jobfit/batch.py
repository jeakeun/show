"""지원서 변경 테스트: 여러 공고를 사람 확정 직전까지 돌려 결과를 모은다.

승인·저장·지원 이력 등록은 하지 않는다. 사람이 결과를 읽고 에이전트를 고치기 위한 테스트다.
기준선(에이전트 1개)도 같은 공고로 돌려 여러 에이전트 구조와 비교한다.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from . import citations, prompts, scoring
from .career import Chunk, Retriever
from .config import Config
from .graph import build
from .posting import read_posting


def _cost(llm, start: int) -> float:
    return round(sum(c.get("cost_usd", 0) for c in llm.calls[start:]), 4)


def run_one(llm, retriever: Retriever, cfg: Config, posting_path: Path) -> dict:
    start = len(llm.calls)
    app = build(llm, retriever, cfg, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": posting_path.stem}}
    app.invoke({"posting_id": posting_path.stem, "posting": read_posting(posting_path)}, config)
    s = app.get_state(config).values          # 사람 확정 직전 상태 (승인하지 않음)
    status = Counter(j["status"] for j in s.get("judged") or [])
    return {
        "id": posting_path.stem,
        "company": s.get("company") or {},
        "fit_score": s.get("fit_score"),
        "status": status,
        "judged": s.get("judged") or [],
        "draft": s.get("draft", ""),
        "issues": s.get("issues") or [],
        "attempts": s.get("attempts", 0),
        "cost": _cost(llm, start),
        "writes": sum(1 for c in llm.calls[start:] if c.get("role") == "writer"),
    }


def report_one(r: dict) -> str:
    issues = "\n".join(f"- [{i['problem']}] {i['sentence']} → {i['detail']}" for i in r["issues"]) or "- 없음"
    return "\n\n".join([
        f"# {r['id']} 지원서 변경 테스트",
        f"적합도 {r['fit_score']}점 · 근거 운영 {r['status'].get('운영', 0)} / 학습 {r['status'].get('학습', 0)} / 없음 {r['status'].get('없음', 0)}"
        f" · 작성 {r['writes']}회 · 비용 약 US${r['cost']}",
        "## 회사 읽기 (AI 추정)\n" + prompts.company_block(r["company"]),
        "## 요구 항목별 근거 (코드 판정)\n" + scoring.fit_table(r["judged"]),
        "## 초안 (사람 확정 직전, 승인 안 함)\n" + (r["draft"] or "(없음)"),
        "## 남은 검증 의견\n" + issues,
    ])


def summary(results: list[dict], label: str) -> str:
    rows = [f"| {r['id']} | {r['company'].get('company_type', '-')} ({r['company'].get('confidence', '-')}) | "
            f"{r['fit_score']} | {r['status'].get('운영', 0)}/{r['status'].get('학습', 0)}/{r['status'].get('없음', 0)} | "
            f"{r['writes']} | {len(r['issues'])} | {r['cost']} |" for r in results]
    total = round(sum(r["cost"] for r in results), 4)
    return "\n\n".join([
        f"# 지원서 변경 테스트 요약 ({datetime.now():%Y-%m-%d %H:%M}, {label})",
        "| 공고 | 회사 유형 (확신도) | 적합도 | 근거 운영/학습/없음 | 작성 횟수 | 남은 지적 | 비용(US$) |\n|---|---|---|---|---|---|---|\n" + "\n".join(rows),
        f"합계 비용 약 US${total} (단가표 기준 추정)",
        "읽는 법: 적합도와 근거 판정은 코드, 회사 읽기와 초안은 AI. 안 맞는 공고에서 적합도가 낮고 초안이 부풀리지 않으면 정상이다.",
    ])


# ---------- 기준선: 에이전트 1개가 경력 문서 전부를 받아 한 번에 쓴다 ----------

def all_sources(chunks: list[Chunk]) -> dict:
    """검색 없이 경력 문서 조각 전부를 근거 목록으로 만든다 (E1, E2, ...)."""
    return {f"E{i + 1}": {"id": c.id, "source": c.source, "kind": c.kind, "section": c.section, "text": c.text}
            for i, c in enumerate(chunks)}


def run_baseline_one(llm, sources: dict, posting_path: Path) -> dict:
    """한 번 쓰고 다시 쓰지 않는다. 비교하려고 코드 검사와 AI 검증가를 둘 다 돌린다
    (본 흐름은 코드 검사를 통과해야 AI 검증가로 넘어가지만, 기준선은 첫 초안의 품질을 다 보려는 것)."""
    start = len(llm.calls)
    draft = llm.baseline(read_posting(posting_path), sources)
    return {
        "id": posting_path.stem,
        "draft": draft,
        "code_issues": citations.check(draft, sources.keys()),
        "ai_issues": llm.verify(draft, sources),
        "cost": _cost(llm, start),
    }


def _issue_lines(issues: list[dict]) -> str:
    return "\n".join(f"- [{i['problem']}] {i['sentence']} → {i['detail']}" for i in issues) or "- 없음"


def _kinds(issues: list[dict]) -> str:
    return ", ".join(f"{k} {n}" for k, n in Counter(i["problem"] for i in issues).most_common()) or "-"


def report_baseline_one(r: dict) -> str:
    return "\n\n".join([
        f"# {r['id']} 기준선 (에이전트 1개)",
        f"한 번에 작성 · 코드 지적 {len(r['code_issues'])} · AI 검증 지적 {len(r['ai_issues'])} · 비용 약 US${r['cost']}",
        "## 초안 (다시 쓰기 없음)\n" + (r["draft"] or "(없음)"),
        "## 코드 검사 (근거 번호)\n" + _issue_lines(r["code_issues"]),
        "## AI 검증가 지적\n" + _issue_lines(r["ai_issues"]),
    ])


def summary_baseline(results: list[dict], label: str) -> str:
    rows = [f"| {r['id']} | {len(r['code_issues'])} | {len(r['ai_issues'])} | {_kinds(r['ai_issues'])} | {r['cost']} |"
            for r in results]
    total = round(sum(r["cost"] for r in results), 4)
    return "\n\n".join([
        f"# 기준선 요약 ({datetime.now():%Y-%m-%d %H:%M}, {label})",
        "| 공고 | 코드 지적 (근거 번호) | AI 검증 지적 | AI 지적 종류 | 비용(US$) |\n|---|---|---|---|---|\n" + "\n".join(rows),
        f"합계 비용 약 US${total} (단가표 기준 추정)",
        "읽는 법: 기준선은 검색·적합도·다시 쓰기 없이 한 번에 쓴다. 여러 에이전트 결과(batch-*)와 같은 공고끼리 비교한다.",
    ])
