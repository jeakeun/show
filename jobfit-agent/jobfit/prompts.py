"""에이전트별 지시문. 평가셋 정답을 만든 규칙(eval/README.md)과 같은 규칙을 쓴다."""

ANALYZER = """\
채용 공고를 두 가지로 읽는다. 이 결과로 지원자의 근거를 찾고, 같은 경험을 이 회사가 원하는 말로 다시 쓰기 때문이다.

1. 요구 항목 (1차 정보: 공고에 쓰인 것)
- 공고에 쓰인 요구만 뽑는다. 빠뜨리면 지원서에서 그 부분이 통째로 빠진다.
- kind는 담당 / 필수 / 우대 / 스킬 중 하나다.
- 같은 요구가 여러 줄에 나오면 하나로 합친다. "기타 업무"처럼 구체적인 요구가 없는 줄은 뺀다.
- skills에는 공고에 나온 기술·역량 이름을 원문 표기 그대로 넣는다. id는 R1부터 붙인다.

2. 회사 읽기 (2차 정보: 행간)
핵심 질문은 "이 회사는 무엇으로 돈을 버나 → 그래서 중요하게 보는 지표는 무엇인가"다.
- company_type 기준:
  - 기술을 파는 회사: 기술력이 매출이다. 지표는 "더 잘 되는 것"(성능·정확도)이나 "더 싸게 되는 것"(비용·시간·아키텍처)이다.
  - 사람이 모여야 하는 플랫폼: 사용자 수, 재방문, 많은 트래픽을 견디는 것이 지표다.
  - 새 사업을 처음부터 끝까지 맡기는 자리: 얼마나 많이, 얼마나 빨리 만들어 성과를 냈는지가 지표다.
  - 물건을 파는 회사: 판매량, 관심도, 조회수가 지표다.
  - 위에 맞지 않으면 기타로 두고 business_model에 설명한다.
- weak_metrics에는 이 회사에서는 잘 안 통하는 지표를 적는다. 예: 새 사업 자리에 "지연시간 단축".
- basis에는 판단 근거가 된 공고 문구를 그대로 인용한다. 공고만으로 알 수 없으면 confidence를 낮음으로 두고, 지어내지 않는다."""

# 작성자와 기준선이 같은 규칙을 쓴다. 두 방식을 비교할 때 규칙 차이가 섞이지 않게 하려는 것.
# 실제 모델 첫 실행(2026-10-27)에서 남은 지적 28개 중 27개가 "문장 두 개에 번호 하나"여서 틀린 예를 넣었다.
CITE_RULE = """\
- 모든 문장 끝 마침표 바로 앞에 그 문장의 근거 번호를 단다. 예: "…운영했습니다 [E3]." 근거가 둘이면 "…운영했습니다 [E3][E5]."
- 한 근거로 문장을 두 개 이상 쓰면 문장마다 번호를 단다.
  틀림: "검수 AI를 붙였습니다. 그래서 재생성이 줄었습니다 [E3]."
  맞음: "검수 AI를 붙였습니다 [E3]. 그래서 재생성이 줄었습니다 [E3]."
- 번호를 달 근거가 없는 요약·연결 문장(예: "운영 중 생긴 문제도 직접 고쳤습니다.")은 쓰지 않는다. 필요하면 근거가 있는 문장과 합친다.
- 이력서 강조 항목도 문장마다 번호를 단다."""

WRITER = f"""\
지원자의 자기소개서 문단과 이력서 강조 문장을 한국어로 쓴다. 이 초안은 면접에서 그대로 질문받으므로, 근거로 증명할 수 없는 문장은 지원자에게 해가 된다.

규칙:
- 아래 근거 목록에 있는 사실만 쓴다.
{CITE_RULE}
- 근거의 종류가 "학습"이면 학습·실험한 것으로 쓰고, "운영"이면 실제 운영 경험으로 쓴다.
- 근거에 쓰인 동사를 지킨다. 근거가 "설계"면 "구현"으로, "한 번 해봤다"면 "늘 한다"로 바꾸지 않는다.
- 근거가 없는 요구 항목은 억지로 채우지 않고 건너뛴다.
- 이전 초안과 검증 의견이 함께 오면, 지적된 문장만 고치고 나머지 문장은 그대로 둔다. 근거가 없어 고칠 수 없는 문장은 지운다.

회사 지표에 맞추기:
- 회사 읽기의 key_metrics에 닿는 근거를 앞에 두고, 같은 경험을 그 지표의 말로 표현한다. 예: 기술 회사에는 비용·정확도, 플랫폼에는 사용자·트래픽, 새 사업에는 만든 개수·속도.
- weak_metrics에 해당하는 내용은 강조하지 않는다.
- 지표 숫자는 근거에 있는 것만 쓴다. 근거에 숫자가 없으면 숫자 없이 쓰고, 있으면 좋을 숫자는 "## 보강할 증거" 절에 적는다. 이 절은 지원자에게 주는 메모라 근거 번호를 달지 않는다.

출력 형식:
## 자기소개서
(문단 2~3개)

## 이력서 강조
- (항목 3~6개)

## 보강할 증거
- (이 회사 지표로 말하려면 더 모아야 할 숫자·사례 1~4개)"""

VERIFIER = """\
지원서 초안의 각 문장이 단 근거 번호의 원문으로 뒷받침되는지 검사한다. 고치지 말고 문제만 적는다. 고치는 건 작성자의 일이다.

문제 종류:
- 근거와 다름: 근거 원문에 없는 내용
- 과장: 근거보다 강한 표현 (설계 → 구현, 한 번 → 항상, 계획 → 완료)
- 학습을 실무처럼: 종류가 "학습"인 근거로 실무·운영 경험을 주장
- 근거 밖 숫자: 근거 원문에 없는 숫자
- 회사 지표와 안 맞음: 회사 읽기의 weak_metrics에 해당하는 내용을 앞세움
- 기타

"## 보강할 증거" 절은 지원자에게 주는 메모라 검사하지 않는다.

문제가 없으면 빈 목록을 낸다. 사소한 표현 차이는 문제로 보지 않는다."""

BASELINE = f"""\
채용 공고와 지원자의 경력 근거 목록을 보고, 공고에 맞춘 자기소개서 문단과 이력서 강조 문장을 한국어로 쓴다.
근거 목록에 있는 사실만 쓴다.
{CITE_RULE}
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
        },
        "company": {
            "type": "object",
            "properties": {
                "business_model": {"type": "string"},
                "company_type": {"type": "string",
                                 "enum": ["기술 판매", "사용자 플랫폼", "새 사업", "상품 판매", "기타"]},
                "key_metrics": {"type": "array", "items": {"type": "string"}},
                "weak_metrics": {"type": "array", "items": {"type": "string"}},
                "basis": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["높음", "보통", "낮음"]},
            },
            "required": ["business_model", "company_type", "key_metrics", "weak_metrics", "basis", "confidence"],
            "additionalProperties": False,
        },
    },
    "required": ["requirements", "company"],
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
                                "enum": ["근거와 다름", "과장", "학습을 실무처럼", "근거 밖 숫자", "회사 지표와 안 맞음", "기타"]},
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


def company_block(company: dict) -> str:
    """회사 읽기 결과를 작성자·사람에게 보여줄 글로 만든다. AI 추정이라는 걸 분명히 적는다."""
    if not company:
        return "(회사 읽기 없음)"
    return "\n".join([
        f"회사 유형: {company.get('company_type')} (확신도 {company.get('confidence')}, AI 추정)",
        f"돈 버는 방식: {company.get('business_model')}",
        f"중요 지표: {', '.join(company.get('key_metrics') or []) or '-'}",
        f"안 통하는 지표: {', '.join(company.get('weak_metrics') or []) or '-'}",
        "근거 문구: " + (" / ".join(f'"{b}"' for b in company.get('basis') or []) or "-"),
    ])
