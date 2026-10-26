"""근거 번호 검사 (코드). AI 검증 전에, 싸고 확실한 검사부터 한다 (설계 결정 J-06 1차)."""
import re

CITE = re.compile(r"\[(E\d+)\]")
# 문장 끝: 한글·닫는 괄호 바로 뒤의 마침표만 본다. "5. 제목", "ADR-07." 같은 숫자 뒤 마침표에서 자르지 않기 위해서다.
SENTENCE_END = re.compile(r"(?<=[가-힣)\]][.!?])\s+")
ONLY_CITES = re.compile(r"^(\[E\d+\]\s*,?\s*)+[.!?]?$")
LIST_MARK = re.compile(r"^(?:[-*•]|\d+[.)])\s+")


def sentences(draft: str) -> list[str]:
    """제목(#)·표(|)·빈 줄을 빼고 문장 단위로 나눈다. 목록 항목(-)도 문장으로 본다."""
    out = []
    for line in draft.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|"):
            continue
        line = LIST_MARK.sub("", line).strip()   # "- ", "1. ", "2) " 같은 목록 표시를 뗀다
        for s in SENTENCE_END.split(line):
            s = s.strip()
            if not s:
                continue
            if ONLY_CITES.match(s) and out:   # "…했습니다. [E3]" 처럼 마침표 뒤에 붙은 번호는 앞 문장 것
                out[-1] = f"{out[-1]} {s}"
            else:
                out.append(s)
    return out


def check(draft: str, known_ids) -> list[dict]:
    known = set(known_ids)
    issues = []
    for s in sentences(draft):
        ids = CITE.findall(s)
        if not ids:
            issues.append({"sentence": s, "problem": "근거 번호 없음", "detail": "모든 문장에 [E번호]를 달아야 함"})
            continue
        unknown = sorted(set(ids) - known)
        if unknown:
            issues.append({"sentence": s, "problem": "없는 근거 번호", "detail": ", ".join(unknown)})
    return issues
