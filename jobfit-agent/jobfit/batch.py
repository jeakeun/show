"""지원서 변경 테스트: 여러 공고를 사람 확정 직전까지 돌려 결과를 모은다.

승인·저장·지원 이력 등록은 하지 않는다. 사람이 결과를 읽고 에이전트를 고치기 위한 테스트다.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from . import prompts, scoring
from .career import Retriever
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
