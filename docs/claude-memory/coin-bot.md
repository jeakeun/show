---
name: coin-bot
description: "코인 모의투자 자동매매 봇 — C:\\coin-bot, 10분 사이클, 매일 07:10 리포트, 대시보드 🪙 탭"
metadata: 
  node_type: memory
  type: project
  originSessionId: da745ac0-da03-46ea-836a-d20d63dd7a74
  modified: 2026-08-21T09:31:18.221Z
---

# 코인 모의투자 봇 (2026-08-21 구축)

- 위치: **`D:\coin-bot`** (OneDrive 밖, 표준 라이브러리만 사용 — pip 설치 불필요, `py -3 -m src.trade_cycle`)
- **모의투자 전용**: 가상 자금 1,000만 원, 업비트 공개 API(인증 불필요) 시세. 사용자 결정:
  거래소 계좌 없음 → 모의투자부터, 실전 전환은 몇 주 검증 후 재논의 (API 키는 사용자가 직접 입력해야 함)
- 구조: market(업비트 시세) / news(RSS 3개+공포탐욕지수, 30분 캐시, 최신·신뢰도 가중 점수) /
  strategy(5분봉 EMA20/60·RSI·변동성돌파, 진입 2종: 돌파매수·과매도반등, 청산 6종) /
  portfolio(state.json·trades.csv·equity.csv) / learn(7일 성과→블랙리스트·신호통계 weights.json) /
  report(md+html, data/summary.json)
- 안전장치: 손절 -2% / 익절 +3% / 트레일링 / 1회 10% / 최대 3종목 / 하루 -3% 한도 /
  BTC -3% 급락 가드 / 악재뉴스 차단 / 쿨다운 90분 / 24h 시간청산 / **STOP.txt = 신규매수 중지**
- 스케줄러: `CoinBotCycle` 10분마다, `CoinBotReport` 매일 07:10 (vbs 래퍼로 창 숨김, bat은 ASCII만)
- 모든 매매에 한글 이유 기록 (매도 기록에 매수근거+매도사유 함께). 리포트에 냉정 피드백(승률·손익비·학습 노트)
- **대시보드 통합**: [[youtube-auto-pipeline]]의 D:\yt-auto\src\snapshot.py에 탭5 "🪙 코인" 추가 —
  D:\coin-bot\reports\*_coin.md + data\summary.json 읽기 전용 표시 (탭4 AX 패턴과 동일).
  summary.json은 매 사이클(10분) trade_cycle이 갱신 — 카드·자산차트(equity_curve 288pt)가 준실시간
- 죽은 RSS 주의: 코인텔레그래프KR rss는 410 → 크립토뉴스KR·인베스팅KR로 대체함
- **주간 심층 회고** (2026-08-21 구축, 사용자 승인): `CoinBotWeekly` 매주 일 21:30 —
  run_weekly.ps1(100% ASCII, ai-daily의 claude.exe 탐색 패턴 복제)이 헤드리스 claude로
  prompts/weekly-prompt.md 실행 → reports/날짜_coinweekly.md 생성 (성공 마커 "WEEKLY-DONE:").
  대시보드 코인 탭에 📊 주간 회고로 함께 표시. 첫 시험 실행 성공 — 회고가 실제 결함
  (트레일링 1.5/1.5는 본전 청산 구조)을 발견해 config를 trigger 2.0/drop 1.0으로 수정함(2026-08-21).
  회고는 config 제안만 하고 직접 수정 금지가 규칙 — 적용은 대화에서 판단
- 모바일 아티팩트(대시보드)는 [[youtube-auto-pipeline]]의 URL에 재발행함 (2026-08-21, 코인 탭 포함)
- 다음 단계 후보: 몇 주 성과 검증 → (검증되면) 실전 소액 전환 논의. 관찰 포인트:
  상승장 4사이클에 매수 후보 0건이 이어지는지(진입 조건 과보수 가능성 — 첫 회고 지적)

참고: [[user-profile]]
