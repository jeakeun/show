---
name: daily-brief
description: >
  This skill should be used when the user asks to "리서치 브리프", "데일리 리포트", "오늘 리서치",
  "마케팅 리서치 돌려줘", "리서치 리포트 만들어줘", "daily research brief", or when a scheduled task
  fires asking for the daily marketing research report for the drinking-safety app project.
  Runs all four research areas and produces one PDF.
---

# 데일리 리서치 브리프

네 개 리서치 영역을 한 번에 돌려 하루치 PDF 리포트를 만든다.

## 실행 순서

### 0. 준비

`context/research-profile.md`, `sources.md`, `report-style.md`를 모두 읽는다.

이전 리포트를 찾는다. 사용자의 연결된 폴더나 이 세션의 작업 폴더에 `drink-safe-research_*.pdf`가 있으면 가장 최근 것의 "오늘의 한 줄"과 주요 발견을 확인해, 오늘 리포트에서 중복을 걷어낸다. 이전 리포트를 못 찾으면 첫 회차로 간주하고 그렇게 명시한다.

### 1. 네 영역 조사

각 영역을 순서대로 실행한다. 서로 독립적이므로 병렬로 처리해도 된다.

| 순서 | 영역 | 참조 스킬 | 데일리 분량 |
|---|---|---|---|
| 1 | 경쟁 서비스 변화 | competitor-watch | 변화 있는 항목만. 없으면 한 줄 |
| 2 | 시장·규제 뉴스 | market-trends | 어제 이후 새 자료만 |
| 3 | 고객 목소리 | voice-of-customer | 인용 3~5개 |
| 4 | 키워드 관찰 | keyword-aso | 새 키워드나 수요 변화가 있을 때만 |

**데일리 실행의 핵심 규칙**: 매일 전체 시장을 다시 조사하지 않는다. **어제 이후 달라진 것**을 찾는 게 목적이다. 변화가 없는 영역은 "변화 없음" 한 줄로 끝내고, 억지로 채우지 않는다. 매주 월요일에는 예외적으로 각 영역을 한 단계 더 깊게 조사해 주간 종합을 겸한다.

### 2. 리포트 구성

`report-style.md`의 구조를 따른다.

1. 오늘의 한 줄
2. 경쟁 동향
3. 시장·규제
4. 고객 목소리
5. 키워드 관찰
6. 이번 주 팀 액션 제안 (3개 이내)
7. 출처 목록

변화가 거의 없는 날은 1·6·7만 남기고 1페이지로 만든다.

### 3. PDF 생성

PDF를 만들기 전에 **pdf 스킬을 읽는다** (Skill 도구로 `pdf` 호출).

한글 폰트 처리가 이 단계의 유일한 실패 지점이다. 반드시:

```bash
fc-list :lang=ko family | head
```

로 설치된 한글 폰트를 확인한다. 없으면 설치한다.

```bash
apt-get install -y fonts-nanum 2>/dev/null || pip install --break-system-packages fonts-nanum
fc-cache -f
```

폰트를 확인한 뒤 그 폰트를 명시적으로 지정해 PDF를 만든다. 생성 후 첫 페이지를 Read로 열어 **한글이 네모(□)로 깨지지 않았는지 눈으로 확인한다.** 이 검증을 건너뛰지 않는다.

파일명: `drink-safe-research_YYYY-MM-DD.pdf`

### 4. 전달

1. `SendUserFile`로 PDF를 전달한다.
2. 사용자의 폴더가 연결되어 있으면 `device_commit_files`로 그 폴더에도 저장한다. 다음 회차가 이전 리포트를 찾을 수 있게 하는 장치이므로, 연결된 폴더가 있으면 반드시 저장한다.
3. 채팅에는 **"오늘의 한 줄"과 액션 제안만** 짧게 적는다. PDF 내용을 채팅에 다시 옮겨 쓰지 않는다.

## 자동 실행일 때

스케줄로 실행된 경우 사용자가 답할 수 없다. 질문하지 말고 다음 기본값으로 진행한다.

- 조사 범위: 위 네 영역 전부
- 형식: PDF
- 판단이 필요한 지점은 가장 보수적인 선택(추측 금지, 출처 없는 내용 제외)을 하고, 리포트 하단에 그렇게 판단한 이유를 한 줄 남긴다

조사 중 소스 접근에 실패했으면 리포트에 "확인 실패: [소스명]"으로 남긴다. 실패를 숨기고 리포트를 완결된 것처럼 만들지 않는다.

## 품질 체크 (전달 전 필수)

- [ ] 모든 수치에 출처 URL이 붙어 있다
- [ ] 인용문이 원문 그대로다 (윤문하지 않았다)
- [ ] 어제 리포트와 중복되는 내용이 없다
- [ ] 한글이 깨지지 않았다
- [ ] 액션 제안이 실행 가능한 문장이다 ("경쟁사를 분석한다" ✗ / "Drive Sober 1점 리뷰 20건을 읽고 판별 정확도 불만 유형을 정리한다" ✓)
