---
name: vtuber-monggeul
description: "버추얼 스트리머 \"몽글이\" 프로젝트 — 웹캠 트래킹 고양이 캐릭터, 숲/치지직 방송용"
metadata: 
  node_type: memory
  type: project
  originSessionId: e8057d38-e239-4e1d-9b23-c243b1b799dd
  modified: 2026-08-02T07:03:56.726Z
---

Desktop/show/vtuber 폴더에 버추얼 스트리머 프로그램 제작 (2026-08-02).

- 주황 고양이 캐릭터 "몽글이", 브라우저(HTML+MediaPipe) 기반, 캔버스 직접 드로잉
- 얼굴(고개/눈/입/눈썹/미소) + 손 추적, 캠에 사람 없으면 2.5초 뒤 수면 모드(눈감음+Zzz+자리비움 팻말)
- 실행: `몽글이 시작.bat` → node server.js (포트 8977) → localhost:8977, `?demo=1`은 카메라 없이 확인
- 크로마키 초록 배경 → OBS 윈도우 캡처 + 크로마키 → 숲(SOOP)/치지직 송출
- 단축키: H(UI 숨김), P(캠 미리보기), 1~4(배경색)
- 사용자는 [[user-profile]] 비개발자 — 안내는 단계별로

관련: [[youtube-auto-pipeline]]
