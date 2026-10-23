"""에이전트 흐름 (LangGraph).

공고 → [공고 분석가] → [근거 검색가 × 요구 항목 수, 병렬] → [적합도 계산(코드)]
     → [작성자 1명] → [검증가] ─ 문제 있음, 상한 전 → 작성자로
                               └ 통과 또는 상한 → [사람 확정] ─ 승인 → [저장]
                                                             ├ 수정 요청 → 작성자로
                                                             └ 폐기 → 끝
"""
import operator
from datetime import datetime
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from . import citations, scoring
from .career import Retriever
from .config import Config


class State(TypedDict, total=False):
    posting_id: str
    posting: str
    requirements: list[dict]
    found: Annotated[list[dict], operator.add]   # 병렬 검색 결과를 덧붙여 합친다
    sources: dict          # 근거 번호 → 조각  ("E1": {...})
    judged: list[dict]     # 요구 항목별 근거 판정 (코드)
    fit_score: int         # 가중 적합도 0~100 (코드)
    draft: str
    issues: list[dict]
    attempts: int          # 이번 라운드에 쓴 횟수
    revisions: int         # 사람이 수정 요청한 횟수
    feedback: str
    decision: str          # 승인 | 수정 | 폐기
    output_path: str


def build(llm, retriever: Retriever, cfg: Config, checkpointer=None):
    # ① 공고 분석가: 공고만 보고 요구 항목을 뽑는다 (경력과 섞이지 않은 맥락, J-02)
    def analyze(state: State) -> dict:
        reqs = llm.analyze(state["posting"])[: cfg.max_requirements]
        return {"requirements": reqs}

    # 요구 항목 수만큼 검색가를 보낸다. 몇 개로 나눌지 실행 중에 정해진다 (J-03)
    def fan_out(state: State):
        reqs = state.get("requirements") or []
        if not reqs:
            return "score"
        return [Send("retrieve", {"req": r}) for r in reqs]

    # ② 근거 검색가: 읽기만 한다. 그래서 동시에 여러 개 돌려도 안전하다
    def retrieve(task: dict) -> dict:
        req = task["req"]
        query = " ".join([req["text"], *req.get("skills", [])])
        hits = retriever.search(query, cfg.top_k)
        return {"found": [{"req": req, "chunks": [{"id": c.id, "source": c.source, "kind": c.kind,
                                                   "section": c.section, "text": c.text, "score": round(s, 2)}
                                                  for c, s in hits]}]}

    # ③ 적합도 계산: 코드가 한다 (J-04). 근거 번호(E1, E2 …)도 여기서 붙인다
    def score(state: State) -> dict:
        sources, chunk_to_eid, judged = {}, {}, []
        order = {r["id"]: i for i, r in enumerate(state.get("requirements") or [])}
        for item in sorted(state.get("found") or [], key=lambda f: order.get(f["req"]["id"], 0)):
            for c in item["chunks"]:
                if c["id"] not in chunk_to_eid:
                    eid = f"E{len(sources) + 1}"
                    chunk_to_eid[c["id"]] = eid
                    sources[eid] = c
            judged.append(scoring.judge(item["req"], item["chunks"]))
        return {"sources": sources, "judged": judged, "fit_score": scoring.overall(judged)}

    # ④ 작성자: 한 명만 쓴다 (J-05)
    def write(state: State) -> dict:
        draft = llm.write(state["posting"], scoring.fit_table(state.get("judged") or []),
                          state.get("sources") or {}, state.get("feedback", ""))
        return {"draft": draft, "attempts": state.get("attempts", 0) + 1}

    # ⑤ 검증가: 코드 검사 먼저, 통과하면 AI 검사. 지적만 하고 고치지 않는다 (J-06)
    def verify(state: State) -> dict:
        issues = citations.check(state["draft"], (state.get("sources") or {}).keys())
        if not issues:
            issues = llm.verify(state["draft"], state.get("sources") or {})
        feedback = "\n".join(f"- [{i['problem']}] {i['sentence']} → {i['detail']}" for i in issues)
        return {"issues": issues, "feedback": feedback}

    def after_verify(state: State) -> str:
        if not state.get("issues"):
            return "confirm"
        if state.get("attempts", 0) <= cfg.max_rewrites:
            return "write"
        return "confirm"   # 상한에 걸리면 문제를 표시한 채로 사람에게 넘긴다

    # ⑥ 사람 확정 (J-07). 재개하면 이 노드가 처음부터 다시 실행되므로, interrupt 앞에는 부수효과를 두지 않는다
    def confirm(state: State) -> dict:
        answer = interrupt({
            "fit_score": state.get("fit_score"),
            "fit_table": scoring.fit_table(state.get("judged") or []),
            "draft": state.get("draft"),
            "issues": state.get("issues") or [],
            "how": "승인 / 폐기 / 그 밖의 말은 수정 요청으로 처리",
        })
        answer = (answer or "").strip()
        if answer == "승인":
            return {"decision": "승인"}
        if answer == "폐기":
            return {"decision": "폐기"}
        return {"decision": "수정", "feedback": f"- [사람 수정 요청] {answer}",
                "attempts": 0, "revisions": state.get("revisions", 0) + 1}

    def after_confirm(state: State) -> str:
        if state.get("decision") == "승인":
            return "save"
        if state.get("decision") == "수정" and state.get("revisions", 0) <= cfg.max_human_revisions:
            return "write"
        return END

    # ⑦ 저장: 승인 뒤에만 파일을 쓴다. 지원 이력 등록(레거시 API)은 2-5 단계에서 이 자리에 붙인다
    def save(state: State) -> dict:
        out_dir = Path(cfg.output_dir) / state.get("posting_id", "posting")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"초안-{datetime.now():%Y%m%d-%H%M%S}.md"
        src_lines = [f"- [{e}] {c['kind']} · {c['source']} · {c['section']}"
                     for e, c in sorted((state.get("sources") or {}).items(), key=lambda x: int(x[0][1:]))]
        path.write_text("\n\n".join([
            f"# 지원서 초안 ({state.get('posting_id')})",
            f"적합도 {state.get('fit_score')}점 (코드 계산, 운영 근거 1점 · 학습 근거 0.5점 · 담당/필수 2배 가중)",
            scoring.fit_table(state.get("judged") or []),
            state.get("draft", ""),
            "## 근거 목록\n" + "\n".join(src_lines),
        ]), encoding="utf-8")
        return {"output_path": str(path)}

    g = StateGraph(State)
    for name, fn in [("analyze", analyze), ("retrieve", retrieve), ("score", score), ("write", write),
                     ("verify", verify), ("confirm", confirm), ("save", save)]:
        g.add_node(name, fn)
    g.add_edge(START, "analyze")
    g.add_conditional_edges("analyze", fan_out, ["retrieve", "score"])
    g.add_edge("retrieve", "score")
    g.add_edge("score", "write")
    g.add_edge("write", "verify")
    g.add_conditional_edges("verify", after_verify, ["write", "confirm"])
    g.add_conditional_edges("confirm", after_confirm, ["save", "write", END])
    g.add_edge("save", END)
    return g.compile(checkpointer=checkpointer)
