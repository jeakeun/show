# 실행해 본 예제

모두 **API 키 없이** 돌아갑니다. 모델 대신 정해진 순서로 답하는 시험용 가짜 모델이나 단순 함수를 써서, 흐름만 확인합니다.
2026-10-22에 [requirements.txt](requirements.txt)의 버전으로 실행해 결과를 확인했습니다.

| 파일 | 무엇 | 관련 문서 |
|---|---|---|
| `01_review_loop.py` | 검수 루프: 작성 → 검수 → 통과/재작성/예비 (LangGraph 갈림길) | 03, ADR-01 |
| `02_human_approval.py` | 사람 승인: `interrupt` 로 멈췄다가 `Command(resume)` 로 재개 | 03, ADR-07 |
| `03_parallel_audit.py` | 읽기는 병렬(`Send`), 쓰기는 하나 | 03, ADR-06 |
| `04_create_agent.py` | LangChain `create_agent` 의 도구 호출 루프 | 03 |
| `05_rag_chunking.py` | 청킹 방법 비교, 가짜 임베딩 vs 키워드 검색, 제목 붙이기 효과 | 04 |
| `06_legacy_tools.py` | 레거시 DB: 읽기 도구는 바로, 쓰기 도구는 승인 뒤에 | 05 |

## 메인 PC에서 실행하는 법

```
cd C:\Users\User\OneDrive\Desktop\show\docs\멀티에이전트\예제
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python 01_review_loop.py
```

공부할 때는 결과만 보지 말고, 코드에서 한 줄씩 바꿔보며 결과가 어떻게 달라지는지 봅니다.
예: `01` 에서 재시도 상한 `2` 를 `1` 로 바꾸면 어디로 가는지, `05` 에서 `chunk_size` 를 바꾸면 조각 수가 어떻게 되는지.
