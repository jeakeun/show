---
name: readme-always-current
description: 저장소 README는 항상 최신 — 기능·설정·스케줄을 바꾸는 커밋마다 해당 README도 같이 갱신 (2026-09-28 지시)
metadata:
  type: feedback
---

코드·설정·스케줄·운영 방식을 바꿔 커밋할 때는 **같은 커밋(또는 바로 다음 커밋)에서 그 저장소 README.md도 고친다.** README 맨 위 "마지막 갱신: YYYY-MM-DD"도 바꾼다.

**Why:** 2026-09-28 사용자 지시 "리드미 내용도 항상 최신화로 변경해". 5개 README가 9/5~9/7 이후 3주간 방치돼 실제와 달라졌었음(선조치 후보고, 프롬프트 감사, 쉬운 설명본, 코인 규칙 변경 등 미반영). show는 공개 저장소라 README가 외부에 보이는 얼굴이기도 함.

**How to apply:** 대상 = D:\yt-auto, D:\coin-bot, D:\ai-daily, D:\market-compass, show(전체 개요), D:\hub. 사용자에게 보고할 때 "README도 갱신함"을 한 줄 포함. 데이터·리포트만 쌓이는 일상 커밋(daily reports, stats)은 README 갱신 불필요. show README는 공개라 비밀·계정 ID 금지([[git-repos]]). 관련: [[act-first-report-after]]
