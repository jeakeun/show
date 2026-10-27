"""멘토 기준 반영 테스트: 회사 읽기 전달, 보강할 증거 절, 분석가 채점."""
from dataclasses import replace

from langgraph.checkpoint.memory import InMemorySaver

from jobfit import citations, evaluate as ev
from jobfit.career import Retriever, load_career
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
    app = build(llm, Retriever(load_career(cfg), cfg.match_words), cfg, checkpointer=InMemorySaver())
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


def test_batch_runs_until_human_confirm_without_saving(tmp_path):
    from jobfit.batch import report_one, run_one, summary
    cfg = replace(Config(), output_dir=tmp_path)
    llm = FakeLLM()
    r = run_one(llm, Retriever(load_career(cfg), cfg.match_words), cfg, ROOT / "eval" / "postings" / "004.md")
    assert r["draft"] and r["writes"] == 1 and r["fit_score"] is not None
    assert list(tmp_path.rglob("*.md")) == []           # 테스트 실행은 승인·저장하지 않음
    assert "회사 읽기" in report_one(r) and "| 004 |" in summary([r], "가짜")


def test_baseline_writes_once_and_runs_both_checks():
    from jobfit.batch import all_sources, report_baseline_one, run_baseline_one, summary_baseline
    cfg = Config()
    sources = all_sources(load_career(cfg))
    draft = "## 자기소개서\n근거 없이 쓴 문장입니다.\n운영했습니다 [E1]."
    llm = FakeLLM(drafts=[draft], verdicts=[[{"sentence": "운영했습니다", "problem": "과장", "detail": "x"}]])
    r = run_baseline_one(llm, sources, ROOT / "eval" / "postings" / "004.md")
    assert [c["role"] for c in llm.calls].count("verifier") == 1        # 코드 지적이 있어도 AI 검증가까지 돈다
    assert len(r["code_issues"]) == 1 and len(r["ai_issues"]) == 1
    assert "과장 1" in summary_baseline([r], "가짜") and "다시 쓰기 없음" in report_baseline_one(r)
