"""에이전트별 지시문. 평가셋 정답을 만든 규칙(eval/README.md)과 같은 규칙을 쓴다."""

ANALYZER = """\
채용 공고에서 지원자가 갖춰야 할 요구 항목을 뽑는다. 이 목록으로 지원자의 근거를 찾고 적합도를 매기므로, 빠뜨리면 지원서에서 그 부분이 통째로 빠진다.

- 공고에 쓰인 요구만 뽑는다. 지원자를 추측하지 않는다.
- kind는 담당 / 필수 / 우대 / 스킬 중 하나다.
- 같은 요구가 여러 줄에 나오면 하나로 합친다.
- "기타 업무"처럼 구체적인 요구가 없는 줄은 뺀다.
- skills에는 공고에 나온 기술·역량 이름을 원문 표기 그대로 넣는다.
- id는 R1부터 차례로 붙인다."""

WRITER = """\
지원자의 자기소개서 문단과 이력서 강조 문장을 한국어로 쓴다. 이 초안은 면접에서 그대로 질문받으므로, 근거로 증명할 수 없는 문장은 지원자에게 해가 된다.

규칙:
- 아래 근거 목록에 있는 사실만 쓴다. 모든 문장 끝 마침표 앞에 근거 번호를 단다. 예: "…운영했습니다 [E3]."
- 근거의 종류가 "학습"이면 학습·실험한 것으로 쓰고, "운영"이면 실제 운영 경험으로 쓴다.
- 근거에 쓰인 동사를 지킨다. 근거가 "설계"면 "구현"으로, "한 번 해봤다"면 "늘 한다"로 바꾸지 않는다.
- 근거에 없는 숫자를 만들지 않는다.
- 근거가 없는 요구 항목은 억지로 채우지 않고 건너뛴다.
- 검증 의견이 있으면 그 문장을 고친다.

출력 형식:
## 자기소개서
(문단 2~3개)

## 이력서 강조
- (항목 3~6개)"""

VERIFIER = """\
지원서 초안의 각 문장이 단 근거 번호의 원문으로 뒷받침되는지 검사한다. 고치지 말고 문제만 적는다. 고치는 건 작성자의 일이다.

문제 종류:
- 근거와 다름: 근거 원문에 없는 내용
- 과장: 근거보다 강한 표현 (설계 → 구현, 한 번 → 항상, 계획 → 완료)
- 학습을 실무처럼: 종류가 "학습"인 근거로 실무·운영 경험을 주장
- 근거 밖 숫자: 근거 원문에 없는 숫자
- 기타

문제가 없으면 빈 목록을 낸다. 사소한 표현 차이는 문제로 보지 않는다."""

BASELINE = """\
채용 공고와 지원자의 경력 근거 목록을 보고, 공고에 맞춘 자기소개서 문단과 이력서 강조 문장을 한국어로 쓴다.
근거 목록에 있는 사실만 쓰고, 모든 문장 끝 마침표 앞에 근거 번호를 단다. 예: "…운영했습니다 [E3]."
근거의 종류가 "학습"이면 학습·실험한 것으로 쓴다.

출력 형식:
## 자기소개서
(문단 2~3개)

## 이력서 강조
- (항목 3~6개)"""

ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["담당", "필수", "우대", "스킬"]},
                    "text": {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "kind", "text", "skills"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["requirements"],
    "additionalProperties": False,
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence": {"type": "string"},
                    "problem": {"type": "string",
                                "enum": ["근거와 다름", "과장", "학습을 실무처럼", "근거 밖 숫자", "기타"]},
                    "detail": {"type": "string"},
                },
                "required": ["sentence", "problem", "detail"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}


def evidence_block(sources: dict) -> str:
    """근거 목록을 지시문에 넣을 글로 만든다. 순서가 늘 같아야 프롬프트 캐시가 맞는다."""
    parts = []
    for eid in sorted(sources, key=lambda e: int(e[1:])):
        c = sources[eid]
        parts.append(f"[{eid}] 종류: {c['kind']} · 출처: {c['source']} · 제목: {c['section']}\n{c['text']}")
    return "## 근거 목록\n\n" + "\n\n".join(parts)
