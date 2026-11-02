"""부품별 테스트: 문서 자르기, 검색, 근거 번호 검사, 문체 검사, 적합도 계산."""
from jobfit import citations, scoring, style
from jobfit.career import Retriever, ko_tokens, load_chunks
from jobfit.config import Config


def chunks():
    cfg = Config()
    return load_chunks(cfg.sources, cfg.source_root, cfg.chunk_size, cfg.chunk_overlap)


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


def test_keyword_search_misses_korean_spelling():
    # 발견 기록: 공고는 "Python", 운영 문서는 "파이썬"이라 키워드로는 못 잇는다 → 2-2에서 뜻 검색·동의어로 개선할 과제
    from jobfit import scoring
    j = scoring.judge({"id": "R", "kind": "스킬", "text": "Python", "skills": ["Python"]},
                      [{"kind": "운영", "text": "파이썬 3.12 설치"}])
    assert j["status"] == "없음"


def test_style_check_catches_ai_tone_and_spacing():
    # 2026-11-02 지원서 49세트 검수에서 실제로 나온 문장들 (근거 검증은 통과했던 것)
    draft = ("## 자기소개서\n"
             "공고의 '데이터로 일하는 팀'이라는 문장을 보고 지원을 결심했습니다 [E1].\n"
             "로그 수집부터 리포트까지 — 전 과정을 혼자 만들었습니다 [E2].\n"
             "입사하면 팀의 자동화에 기여하겠습니다 [E1].\n"
             "새 도구도 빨리 배울수 있습니다 [E2].\n"
             "## 보강할 증거\n- 열정을 보여줄 숫자 — 메모라 검사 안 함")
    probs = [(i["problem"], i["sentence"][:6]) for i in style.check(draft)]
    assert ("AI 말투", "공고의 '데") in probs
    assert ("AI 말투", "로그 수집부") in probs
    assert ("AI 말투", "입사하면 팀") in probs
    assert ("맞춤법", "새 도구도 ") in probs
    assert not any("메모" in s for _, s in probs)


def test_style_check_passes_plain_writing_and_flags_overuse():
    plain = "## 자기소개서\n쇼츠 179편을 매일 자동으로 발행했습니다 [E1]. 실패하면 폰으로 알림이 옵니다 [E2]."
    assert style.check(plain) == []
    many = "## 자기소개서\n" + " ".join(f"{n}번째 도구를 직접 만들었습니다 [E1]." for n in range(4))
    assert any("'직접' 4번" in i["sentence"] for i in style.check(many))
