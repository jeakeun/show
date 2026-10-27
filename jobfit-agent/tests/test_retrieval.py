"""근거 검색 채점 테스트 (2-2). 모델 호출 없음.

검색 방식을 바꾸다 이전보다 나빠지면 여기서 걸린다. 숫자는 2026-10-27 채점 결과(eval/results/retrieval-*.md).
"""
from jobfit.retrieval_eval import VARIANTS, compare, load_gold, matches


def test_gold_labels_cover_every_answer_requirement():
    gold = load_gold()
    assert len(gold) == 117
    assert all(g["gold"]["status"] in {"운영", "학습", "없음"} for g in gold)
    assert all(g["gold"]["운영"] for g in gold if g["gold"]["status"] == "운영")   # 운영이면 근거 위치가 있어야 함


def test_reference_matching():
    chunk = {"source": "docs/멀티에이전트/02-내-설계결정-기록.md", "section": "ADR-01. 만드는 AI와 검사하는 AI를 나눈다"}
    assert matches(chunk, "02#ADR-01") and matches(chunk, "02#") and not matches(chunk, "03#")
    assert not matches({"source": "README.md", "section": "한눈에 보기"}, "02#한눈에 보기")


def test_current_search_beats_old_search():
    (_, old), (_, now) = compare([VARIANTS[0], VARIANTS[-1]])
    assert old["ops_hit"] <= 13 and now["ops_hit"] >= 28          # 운영 근거 적중 13/40 → 28/40
    assert now["learn_hit"] >= old["learn_hit"]                     # 운영을 찾느라 학습 근거를 잃지 않음
    assert now["agree"] >= 88 and len(now["under"]) <= 20
    # 가짜 운영은 2 → 5로 늘었다. 원인은 "키워드 하나만 맞아도 운영" 규칙 (2-3에서 고칠 것). 더 늘면 실패
    assert len(now["fake_ops"]) <= 5
