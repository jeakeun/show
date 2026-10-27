"""부품별 테스트: 문서 자르기, 검색, 근거 번호 검사, 적합도 계산."""
from jobfit import citations, scoring
from jobfit.career import Retriever, ko_tokens, load_career
from jobfit.config import Config


def chunks():
    return load_career(Config())


def test_chunks_have_kind_and_section():
    cs = chunks()
    assert len(cs) > 20
    assert {c.kind for c in cs} == {"운영", "학습"}
    assert any("ADR-07" in c.section for c in cs)


def test_ko_tokens_bigrams():
    assert ko_tokens("사람 승인") == ["사람", "람승", "승인"]


def test_retrieval_finds_section_by_its_title():
    # 04-RAG 실험 3의 회귀 테스트: 제목에 있는 말로 물어도 그 절을 찾아야 한다
    hits = Retriever(chunks()).search("사람 승인 위치 되돌릴 수 있는가", k=3)
    assert hits and "ADR-07" in hits[0][0].section


def test_citation_check():
    draft = "## 자기소개서\n유튜브를 운영했습니다 [E1]. 근거 없는 문장입니다.\n- 없는 번호를 썼습니다 [E9].\n| 표 | 무시 |"
    issues = citations.check(draft, {"E1"})
    assert [i["problem"] for i in issues] == ["근거 번호 없음", "없는 근거 번호"]


def test_citation_after_period_belongs_to_previous_sentence():
    assert citations.check("운영했습니다. [E1]", {"E1"}) == []


def test_citation_list_in_one_bracket():
    # 기준선 첫 실행에서 [E33, E34] 를 번호 없음으로 잘못 잡았다 (59개 중 11개)
    assert citations.check("운영했습니다 [E1, E2]. 만들었습니다. [E1,E2]", {"E1", "E2"}) == []
    issues = citations.check("운영했습니다 [E1, E7].", {"E1"})
    assert [(i["problem"], i["detail"]) for i in issues] == [("없는 근거 번호", "E7")]


def test_writer_and_baseline_share_citation_rule():
    from jobfit import prompts
    assert prompts.CITE_RULE in prompts.WRITER and prompts.CITE_RULE in prompts.BASELINE


def test_numbered_items_are_not_split_at_the_number():
    # 처음 만든 검사기는 "5. 제목"의 "5."를 문장으로 잘라 근거 없음으로 잘못 판정했다 (테스트가 잡은 버그)
    draft = "1. 직접 짠 것 vs LangGraph 경험 [E1].\n2) ADR-07. 사람 승인 기준 [E2]."
    assert citations.check(draft, {"E1", "E2"}) == []


def test_scoring_kinds_and_weights():
    req = {"id": "R1", "kind": "담당", "text": "RAG 구현", "skills": ["RAG", "Vector"]}
    run = [{"kind": "운영", "text": "RAG를 운영"}, {"kind": "학습", "text": "Vector 검색 실험"}]
    j = scoring.judge(req, run)
    assert j["status"] == "운영" and j["matched"] == ["RAG", "Vector"] and j["missing"] == []
    j2 = scoring.judge({"id": "R2", "kind": "우대", "text": "x", "skills": ["Kafka"]}, run)
    assert j2["status"] == "없음"
    assert scoring.overall([j, j2]) == round(100 * (2 * 1.0 + 1 * 0.0) / 3)


def test_posting_frontmatter_is_removed():
    from jobfit.config import ROOT
    from jobfit.posting import read_posting
    body = read_posting(ROOT / "eval" / "postings" / "001.md")
    assert body.startswith("담당업무") and "source:" not in body


def test_synonyms_link_posting_words_to_ops_words():
    # 2-1 발견: 공고는 "Python", 운영 문서는 "파이썬"이라 키워드로는 못 이었다 → 2-2에서 동의어 사전으로 잇는다
    req = {"id": "R", "kind": "스킬", "text": "Python", "skills": ["Python"]}
    ops = [{"kind": "운영", "text": "파이썬 3.12 설치"}]
    assert scoring.judge(req, ops, match_words=False)["status"] == "없음"      # 예전 방식
    assert scoring.judge(req, ops)["status"] == "운영"
    assert scoring.judge(req, [{"kind": "운영", "text": "계산은 streaks.py 가 한다"}])["status"] == "운영"


def test_english_keywords_match_whole_words():
    # 영어를 글자 조각으로 맞추면 "GA" 가 "ZipGa" 에, "SQL" 이 "SQLite" 에 맞는다
    from jobfit.words import contains
    assert not contains("집가(ZipGa) 마케팅", "GA")
    assert not contains("공유 저장소(SQLite)", "SQL")
    assert contains("LangGraph로 만든 루프", "LangGraph")
    assert contains("감사 Agents 3기", "Agents") and not contains("Agent Action", "LLM")


def test_cleaning_removes_non_evidence():
    # 001 재현: LangChain 질문에 가장 높게 잡힌 "운영" 조각이 "아직 약한 곳"과 이 프로젝트 자신이었다
    cs = chunks()
    assert not any("아직 약한 곳" in c.section or "이 저장소 구조" in c.section for c in cs)
    assert not any("jobfit-agent" in c.text or "마지막 갱신" in c.text for c in cs)
    assert {c.kind for c in cs if "ADR-10" in c.section or "market-compass" in c.section} == {"학습"}
    assert any("ADR-01" in c.section and c.kind == "운영" for c in cs)


def test_per_kind_search_brings_operating_evidence():
    # 001 R1: 상위 3개는 늘 LangChain 학습 문서. 종류별로 더 찾아야 운영 경험(에이전트 운영)이 들어온다
    r = Retriever(chunks())
    req = "LangChain (LangGraph, LangFlow 포함)와 LLM을 이용한 AI Agent의 개발"
    skills = ["LangChain", "LangGraph", "LangFlow", "LLM", "AI Agent"]
    top = r.search(req, k=3, skills=skills)
    assert {c.kind for c, _, _ in top} == {"학습"}
    more = r.search(req, k=3, per_kind=2, skills=skills)
    ops = [(c, extra) for c, _, extra in more if c.kind == "운영"]
    assert len(ops) == 2 and all(extra for _, extra in ops)


def test_empty_skills_ignore_extra_chunks():
    # 키워드 없는 항목은 아직 "검색 결과가 있으면 근거" 규칙(2-3에서 고침). 더 붙인 조각으로 더 부풀면 안 된다
    req = {"id": "R", "kind": "필수", "text": "백엔드 개발 경력 3년 이상", "skills": []}
    got = [{"kind": "학습", "text": "x"}, {"kind": "운영", "text": "y", "extra": True}]
    assert scoring.judge(req, got)["status"] == "학습"


def test_fit_table_shows_kind_per_keyword():
    req = {"id": "R1", "kind": "담당", "text": "LLM 에이전트", "skills": ["LLM", "LangChain"]}
    got = [{"kind": "운영", "text": "클로드로 대본을 쓴다"}, {"kind": "학습", "text": "LangChain 예제"}]
    assert "LLM(운영), LangChain(학습)" in scoring.fit_table([scoring.judge(req, got)])


def test_api_key_prefers_jobfit_name(monkeypatch):
    from jobfit.config import api_key
    monkeypatch.delenv("JOBFIT_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert api_key() is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "b")
    assert api_key() == "b"                      # 메인 PC 예전 .env 도 계속 동작
    monkeypatch.setenv("JOBFIT_API_KEY", "a")
    assert api_key() == "a"                      # 클라우드에서는 이 이름이 우선
