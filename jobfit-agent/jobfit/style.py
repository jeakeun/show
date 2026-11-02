"""문체 검사 (코드). 오타·맞춤법·AI 말투를 비용 없이 먼저 거른다.

2026-11-02 추가. 지원서 49세트를 사람이 검수해 보니 근거 검증은 통과했는데
긴 줄표 "—" 208번, 상투구("지원을 결심", "기여하겠습니다"), "직접" 남발 같은 AI 티가 그대로 남아 있었다.
그때 실제로 나온 문제를 규칙으로 옮겼다. 애매한 건 AI 검증가(VERIFIER)가 본다.
"""
import re

from .citations import sentences

# (찾을 패턴, 문제 종류, 고칠 방향)
RULES = [
    (re.compile(r"[—―]"), "AI 말투", "긴 줄표는 한국어 자기소개서에서 거의 안 쓴다. 문장으로 풀거나 쉼표·콜론·괄호로 바꿀 것"),
    (re.compile(r"지원을 결심|보고 지원하게 되었"), "AI 말투", "상투적인 지원 동기. 구체적인 계기와 할 일을 쓸 것"),
    (re.compile(r"기여하(고 싶|겠)습니다"), "AI 말투", "추상적인 다짐. 입사해서 할 구체적인 행동으로 쓸 것"),
    (re.compile(r"빠르게 익혀|빠르게 습득"), "AI 말투", "상투구. 실제로 익힌 기간·방법을 쓸 것"),
    (re.compile(r"조용히"), "AI 말투", "번역투 수식어. 빼거나 구체적으로 쓸 것"),
    (re.compile(r"누구보다|끊임없이|열정|시너지|함께 성장"), "AI 말투", "근거 없는 미사여구. 빼거나 사실로 바꿀 것"),
    (re.compile(r"단순히 .{1,25}?(이|가) 아니라"), "AI 말투", "'단순히 A가 아니라 B' 틀은 AI 티가 남. 하고 싶은 말만 바로 쓸 것"),
    (re.compile(r"가치를 (만들|창출)|역량을 바탕으로"), "AI 말투", "추상 명사 표현. 무엇을 했는지로 바꿀 것"),
    (re.compile(r"[가-힣]  +[가-힣]|\s[.,]|\.\.(?!\.)"), "맞춤법", "띄어쓰기·문장부호 이상 (두 칸 띄움, 마침표 앞 공백, 마침표 두 개)"),
]
SU = re.compile(r"([가-힣])수\s?있")  # "할수 있다" → "할 수 있다" (앞 글자가 ㄹ받침일 때만)


def _sticky_su(s: str) -> bool:
    return any((ord(m.group(1)) - 0xAC00) % 28 == 8 for m in SU.finditer(s))


# 한 초안 안에서 이만큼 넘게 나오면 남발로 본다
OVERUSE = {"직접": 2, "실제로": 2, "특히": 2, "핵심": 2}


def check(draft: str) -> list[dict]:
    """초안의 문체 문제 목록. "## 보강할 증거" 절은 지원자 메모라 검사하지 않는다(citations.sentences 와 같은 범위)."""
    issues = []
    sents = sentences(draft)
    for s in sents:
        for pat, problem, detail in RULES:
            if pat.search(s):
                issues.append({"sentence": s, "problem": problem, "detail": detail})
        if _sticky_su(s):
            issues.append({"sentence": s, "problem": "맞춤법", "detail": "의존명사 '수'는 띄어 쓴다 (할 수 있다)"})
    body = " ".join(sents)
    for word, limit in OVERUSE.items():
        n = body.count(word)
        if n > limit:
            issues.append({"sentence": f"(초안 전체) '{word}' {n}번", "problem": "AI 말투",
                           "detail": f"'{word}'를 {limit}번 넘게 씀. 꼭 필요한 곳만 남길 것"})
    return issues
