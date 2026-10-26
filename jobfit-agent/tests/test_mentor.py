"""멘토 기준 반영 테스트: 회사 읽기 전달, 보강할 증거 절, 분석가 채점."""
from dataclasses import replace

from langgraph.checkpoint.memory import InMemorySaver

from jobfit import citations, evaluate as ev
from jobfit.career import Retriever, load_chunks
from jobfit.config import ROOT, Config
from jobfit.fake import FakeLLM
from jobfit.graph import build
from jobfit.posting import read_posting


def test_reinforce_section_is_not_citation_checked():
    draft = "## 자기소개서\n운영했습니다 [E1].\n\n## 보강할 증거\n- 지연시간 개선 수치가 필요함\n- 사용자 수 기록"
    assert citations.check(draft, {"E1"}) == []


def test_company_reading_reaches_writer_and_human(tmp_path):
    llm = FakeLLM()
    cfg = replace(Config(), output_dir=tmp_path)
    app = build(llm, Retriever(load_chunks(cfg.sources, cfg.source_root)), cfg, checkpointer=InMemorySaver())
    result = app.invoke({"posting_id": "006", "posting": read_posting(ROOT / "eval" / "postings" / "006.md")},
                        {"configurable": {"thread_id": "m"}})
    writer_call = next(c for c in llm.calls if c["role"] == "writer")
    assert writer_call["company"]["company_type"] == "기타"          # 분석가의 회사 읽기가 작성자에게 전달됨
    assert "회사 유형" in result["__interrupt__"][0].value["company"]  # 사람 확정 화면에도 보임


def test_requirement_matching_recall_precision():
    gold = [{"text": "RAG 구현", "skills": ["RAG"]},
            {"text": "Legacy System 연계", "skills": ["레거시 연계"]},
            {"text": "Python", "skills": ["Python"]}]
    pred = [{"text": "RAG 구성 및 구현", "skills": ["RAG"]},
            {"text": "Python 개발", "skills": ["python"]},
            {"text": "Kubernetes 운영", "skills": ["Kubernetes"]}]
    s = ev.requirement_scores(gold, pred)
    assert s["matched"] == 2 and s["recall"] == 2 / 3 and s["precision"] == 2 / 3
    assert s["missed"] == ["Legacy System 연계"] and s["extra"] == ["Kubernetes 운영"]


def test_company_type_scored_only_when_mentor_labeled():
    assert ev.company_type_hit({"mentor_reading": {"company_type": "기술 판매"}}, {"company_type": "기술 판매"}) is True
    assert ev.company_type_hit({"mentor_reading": {"company_type": "새 사업"}}, {"company_type": "기술 판매"}) is False
    assert ev.company_type_hit({"mentor_reading": {"discussed": "해석 없음"}}, {"company_type": "기타"}) is None
