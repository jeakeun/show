---
name: headless-prompt-quotes
description: "PowerShell 5.1이 claude -p 지시문을 큰따옴표에서 쪼개 AI데일리 채용 13%·뉴스 25%·검수 2%만 전달되던 사고와 수정, 구독 한도 자동 재실행 (2026-11-02)"
metadata:
  node_type: memory
  type: project
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-01T19:47:02.906Z
---

**사고:** Windows PowerShell 5.1은 외부 exe에 인자를 넘길 때 안쪽 큰따옴표를 이스케이프하지 않는다. 지시문 안에 `"객체 탐지 채용"`처럼 띄어쓰기 든 따옴표 구절이 있으면 거기서 인자가 쪼개져 claude는 앞부분만 받았다. AI데일리 채용 13%, 뉴스 25%, 검수 2%, 자가감사 65%만 전달 (자가감사가 4주 연속 "지시문 잘림" 보고 → 2026-11-02 원인 확인). 실험: 고치기 전 claude는 "Search terms like object"까지만 받음, 고친 뒤 끝까지 받음.

**수정 (2026-11-02):** `D:\ai-daily\run-daily.ps1`·`D:\self-audit\run-audit.ps1`에 `ConvertTo-NativeArg`(따옴표 앞 백슬래시 두 배 + `\"`) 추가, `& $exe -p (ConvertTo-NativeArg $prompt)`. 같은 날 함께 고친 것: 두 스크립트의 로그인 만료 알림 경로가 옛 편집 사고로 `D:` + 줄바꿈 + `otify\push.ps1`로 끊겨 있던 것, audit-prompt.md의 `D:\ai-daily`가 `D:<BEL>i-daily`로 깨진 것(heredoc에서 `\n`·`\a`가 변환된 흔적).

**구독 한도 자동 재실행:** 헤드리스 claude가 `You've hit your ... limit · resets 3am`이면 초기화 10분 뒤 1회용 예약(`AIDailyRetry-<작업>`, `SelfAuditRetry`)을 만들어 같은 날짜로 1번만 다시 돈다(검수만 걸렸으면 `-ReviewOnly`). 재실행도 걸리면 폰 알림만.

**How to apply:** 헤드리스 claude 출력이 엉뚱하거나 "지시문이 잘렸다"는 말이 나오면 인자 전달부터 의심. 새 PowerShell 런처를 만들 때 긴 지시문은 반드시 `ConvertTo-NativeArg`로 넘길 것. 스크립트 패치는 bash heredoc 말고 Write 도구로 만든 파이썬 파일로(백슬래시가 변환됨). self-audit는 깃 저장소가 아니라 수정 전 `.bak-날짜` 백업을 남겼음. 관련 [[claude-cli-path]], [[context-mode-plugin]].
