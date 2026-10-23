"""흐름 테스트: 가짜 모델로 그래프 전체를 돌려 본다 (API 키 없음, 비용 없음)."""
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from jobfit.career import Retriever, load_chunks
from jobfit.config import ROOT, Config
from jobfit.fake import FakeLLM
from jobfit.graph import build
from jobfit.posting import read_posting

POSTING = read_posting(ROOT / "eval" / "postings" / "001.md")


def make(tmp_path, llm):
    cfg = replace(Config(), output_dir=tmp_path)
    retriever = Retriever(load_chunks(cfg.sources, cfg.source_root, cfg.chunk_size, cfg.chunk_overlap))
    app = build(llm, retriever, cfg, checkpointer=InMemorySaver())
    return app, {"configurable": {"thread_id": "t"}}


def start(app, config):
    return app.invoke({"posting_id": "001", "posting": POSTING}, config)


def test_happy_path_waits_for_human_then_saves(tmp_path):
    llm = FakeLLM()
    app, config = make(tmp_path, llm)
    result = start(app, config)
    assert "__interrupt__" in result                       # 사람 확정에서 멈춤
    assert list(Path(tmp_path).rglob("*.md")) == []        # 승인 전에는 아무것도 저장하지 않음
    payload = result["__interrupt__"][0].value
    assert payload["issues"] == [] and "[E" in payload["draft"]

    app.invoke(Command(resume="승인"), config)
    state = app.get_state(config).values
    assert state["decision"] == "승인"
    assert Path(state["output_path"]).exists()


def test_parallel_retrieval_one_per_requirement(tmp_path):
    app, config = make(tmp_path, FakeLLM())
    start(app, config)
    state = app.get_state(config).values
    assert len(state["found"]) == len(state["requirements"]) > 0   # 요구 항목마다 검색가 하나
    assert len(state["judged"]) == len(state["requirements"])
    assert 0 <= state["fit_score"] <= 100


def test_missing_citation_triggers_rewrite(tmp_path):
    bad = "## 자기소개서\n근거 없이 잘했습니다."
    llm = FakeLLM(drafts=[bad])            # 첫 초안은 근거 번호가 없음 → 코드 검사에서 걸림 → 다시 쓰기
    app, config = make(tmp_path, llm)
    start(app, config)
    state = app.get_state(config).values
    writes = [c for c in llm.calls if c["role"] == "writer"]
    assert len(writes) == 2 and writes[1]["feedback"]   # 두 번째 쓰기는 검증 의견을 받음
    assert state["issues"] == []


def test_rewrite_cap_hands_over_with_issues(tmp_path):
    bad = "## 자기소개서\n근거 없이 잘했습니다."
    llm = FakeLLM(drafts=[bad] * 10)        # 계속 나쁜 초안 → 상한(처음 1 + 다시 2) 뒤 사람에게 문제와 함께 넘김
    app, config = make(tmp_path, llm)
    result = start(app, config)
    assert len([c for c in llm.calls if c["role"] == "writer"]) == 3
    assert result["__interrupt__"][0].value["issues"]


def test_ai_verifier_issue_triggers_rewrite(tmp_path):
    issue = [{"sentence": "x", "problem": "과장", "detail": "설계를 구현으로 씀"}]
    llm = FakeLLM(verdicts=[issue])         # 코드 검사는 통과, AI 검증에서 과장 지적 → 다시 쓰기
    app, config = make(tmp_path, llm)
    start(app, config)
    assert len([c for c in llm.calls if c["role"] == "writer"]) == 2


def test_human_revision_then_discard(tmp_path):
    llm = FakeLLM()
    app, config = make(tmp_path, llm)
    start(app, config)
    result = app.invoke(Command(resume="RAG 경험을 더 강조해줘"), config)   # 수정 요청 → 다시 쓰고 다시 멈춤
    assert "__interrupt__" in result
    app.invoke(Command(resume="폐기"), config)
    state = app.get_state(config).values
    assert state["decision"] == "폐기" and "output_path" not in state
    assert list(Path(tmp_path).rglob("*.md")) == []
