---
name: nudy-automation-stopped
description: "nudy(가상 메이크업) 자동 작업 영구 중단 — 2026-11-02 사용자 지시 \"절대 다시 실행할 수 없게\", 예약 삭제·실행 파일 .disabled"
metadata:
  node_type: memory
  type: project
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-01T19:08:01.658Z
---

2026-11-02 사용자 지시("누디 매일 수집하는거 아예 멈춰" → "누디 자동으로 돌아가는거 다 끄고" → "코인봇이랑 누디는 절대 다시 실행할 수 없게 만들어")로 nudy 자동 작업을 영구 중단했다.
- 예약 작업 3개 **삭제**: `nudy-marketing-daily`(매일 09:40, show\support-yr-makeup-marketing 수집·분석 — Claude 구독 한도로 10/28·11/1 실패 중이었음), `nudy-marketing-post`, `nudy-lora-train-once`. XML 백업은 `D:\disabled-automation-backup-2026-11-02\`.
- 실행 파일 이름 변경: `support-yr-makeup-marketing\run-daily.ps1`·`run-post.ps1`, `D:\nudy-lora\start_train_scheduled.bat` → `.disabled`.
- 코드·수집 데이터는 그대로 보관.

**Why:** 사용자가 nudy 자동 수집을 더 이상 원하지 않고, 구독 사용 한도도 소모하고 있었음.

**How to apply:** 어떤 이유로도 다시 켜거나 재등록·재실행을 제안하지 말 것. 사용자가 직접 명시적으로 되살려 달라고 할 때만. 자동화 상태 보고 시 "영구 중단(사용자 결정)"으로 표시. nudy 프로젝트 경력(마케팅 영상 14편 등)은 이력서·지원서에 계속 써도 됨. **팀 프로젝트 자체도 2026-11-02 종료** (사용자 확인) → 이력서·포트폴리오 기간은 "2026.09 – 2026.11", 태그 "완료", 과거형으로 쓸 것. 같은 날 [[coin-bot]]도 영구 중단.
