---
name: self-audit-rule
description: 문제를 스스로 발견하면 학습(메모리)하고 보고서를 작성하라는 상시 지시 (2026-08-27)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e6e084c2-f5eb-4182-bb20-f61dc7cd8e39
  modified: 2026-08-27T09:38:56.720Z
---

사용자 지시 (2026-08-27): "니 스스로 이런 문제를 발견하면 학습하고 보고서 작성해"

**Why:** 전 프로젝트 할루시네이션 감사에서 노출된 API 키, 코인봇 수수료 20.5% 과대계상,
AI데일리 유령 데이터 같은 문제를 에이전트 감사로 찾아내자, 이걸 일회성이 아니라
상시 동작으로 만들라고 지시함. 사용자는 냉정한 자기검증 문화를 신뢰의 근거로 삼음.

**How to apply:**
- 어떤 작업 중이든 다른 프로젝트/시스템의 문제(보안 노출, 계산 버그, 죽은 데이터,
  깨진 스케줄)를 발견하면: ①즉시 관련 메모리 파일에 기록(학습) ②사용자에게 보고서로
  정리해 전달(구두 요약이 아니라 아티팩트/문서 형태) ③수정은 허용 범위 확인 후
  (AI데일리류 불가침 영역은 보고만).
- 감사 방법론: 읽기 전용 에이전트 병렬 투입 → 리포트 주장 vs 원본 데이터 대조 →
  발견은 심각도순, 실측 숫자·파일 경로와 함께.
- 관련: [[youtube-auto-pipeline]] (2026-08-27 감사 결과·조치 내역), [[user-profile]] (검토 에이전트 경유 원칙)

**자동화됨 (2026-08-27, 사용자 "이렇게 해줘" 확정)**: `SelfAuditWeekly` 작업 스케줄러 —
매주 일요일 10:00, `D:\self-audit\run-audit.ps1`이 headless claude로 감사 프롬프트
(`D:\self-audit\prompts\audit-prompt.md`) 실행. 감사 범위: yt-auto 로그/슬롯 규칙/회고 수치 대조,
coin-bot 리포트 vs trades.csv 대조/손절 초과/격리 파일, ai-daily 산출물(읽기 전용), 스케줄러 8종 건강.
결과: `D:\self-audit\reports\YYYY-MM-DD-audit.md` + 바탕화면 `주간감사리포트.txt`.
가드: 실행 전 coin-bot/yt-auto src·config·ai-daily 프롬프트 해시 백업 → 변조 시 자동 원복+경고 파일.
실패 시 바탕화면 `WARNING-self-audit-failed.txt`. ps1은 ASCII 전용(한글 파일명 금지 교훈 재확인).
대화 중 감사 결과 얘기가 나오면 최신 audit.md를 읽고 후속 조치를 제안할 것.
대시보드 탭6 "🔍 감사"에서 열람 가능 (snapshot.py auditItems, 2026-08-27 추가 — PC·모바일 공통).

**1회차 시험 감사 (2026-08-27) 결과와 후속 수정**: 감사관이 8건 발견, 검증 후 6건 실수정 —
①insights 일별 데이터가 '추적 50편 표본 합'이라 옛 영상이 밀리면 음수가 나오는 착시(-697 사건의 진범,
8/26 회고의 "집계 기준 변경 오염" 서사 무효) → channel_views를 추세 판정용으로 주입 ②2부작 2부가 저녁
자가테스트 슬롯을 3일마다 잡아먹던 구조 → 2부는 아침에만 소화 ③계열 3연속 금지를 violations로 코드 강제
(diagnosis만 — classic은 포맷 자체가 고전실험이라 제외) ④coin-bot 주간 가드가 root 신규 파일 못 막던 구멍
+ 잔존 _analyze.py 격리 ⑤스케줄러 상태는 run-audit.ps1이 사전 덤프(scheduler_status.txt), 바탕화면 사본
(Weekly-Audit-Report.md)도 스크립트가 복사(headless는 작업폴더 밖 쓰기 불가) ⑥run_insights.bat에 시각 기록.
교훈: **감사 리포트도 검증 대상** — 1건은 내가 "오탐"이라 잘못 반박했다가 로그 재확인으로 정정함(8/27 저녁
슬롯 잠식은 사실이었음). 코인봇 태스크명 = CoinBotCycle/CoinBotWeekly.

**재확인 (2026-09-04 사용자 "매번 내가 시키기 전에 니가 봤을 때 이상하다 싶으면 바로바로 보고")**: 조회수·자막·스케줄 등
무엇이든 이상 징후를 보면 사용자가 묻기 전에 먼저 보고. 영상 결과물(자막 겹침, CTA 노출 시간 같은 시청자 눈에 보이는 것)도 감사 범위에 포함.

**2026-09-06 감사 후속 (사용자 "ntfy 오늘 에러 확인")**: 폰 알림 2건 모두 오탐/잡음이었음.
① Self-audit FAILED — 리포트(28KB)는 정상 생성됐는데 LLM이 'AUDIT-DONE:' 마커를 빼먹어 실패 판정 →
   run-audit.ps1을 코인봇과 같이 "리포트 파일 실존(>800B)+exit 0"이면 성공으로 변경(마커 선택). 바탕화면 경고 파일 삭제, 리포트 복사.
② Coin-bot guard — 주간 회고 LLM이 루트에 _wk.py 임시 분석 스크립트 생성 → 격리(정상 동작). weekly-prompt.md에
   "임시 스크립트 파일 금지, python -c 사용" 규칙 추가.
감사 리포트의 실제 발견: 🔴 channel_views 9/2부터 정지(5일 +14회) → insights.py에 `_daily_trend_lines` 추가
(영상별 차분 합 + ⚠정지 표시)로 23:50 회고 전에 수정. 🔴 코인봇 손절 15/15건 -2% 초과 체결(평균 -2.94%, 10분 사이클 탓,
초과분 21.9만원) → 5분 중간점검 제안, 사용자 결정 대기. audit-prompt.md 낡은 시간·슬롯 규칙 갱신.

**2026-09-08 07:00 장애: 헤드리스 claude.exe OAuth 만료** ("OAuth session expired and could not be refreshed"). ai-daily jobs 실패(0x1),
뉴스·코인 주간회고·자가감사·논문검토 등 헤드리스 작업 전부 영향. 원인은 구독 로그인 세션 만료 — 내가 대신 로그인 불가.
조치: 사용자에게 `claude login` 안내, Monitor로 복구 감시 후 jobs/news 자동 재실행. 후속 과제: run-daily.ps1·run_weekly.ps1·run-audit.ps1
시작부에 인증 사전 점검(`claude -p ok`) → 실패 시 "로그인 필요" 푸시로 원인을 바로 알리기.
