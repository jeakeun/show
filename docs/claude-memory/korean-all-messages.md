---
name: korean-all-messages
description: "작업 중 중간 안내·명령 설명까지 모든 화면 문구를 한글로 (영어 금지, 2026-11-19 지시)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-18T23:23:04.805Z
---

최종 답변뿐 아니라 작업 중에 화면에 보이는 모든 문장을 쉬운 한국어로 쓴다:
중간 안내 문장("Now editing...", "Merging." 같은 것), 도구 실행 설명(Bash/PowerShell description), 진행 한 줄 보고.
영어는 코드·파일명·명령어 자체에만 쓴다.

**Why:** 2026-11-19 사용자가 화면 캡처로 영어 중간 문구("Now a quick test that...", "Tested audit permissions headlessly")를 가리키며 "이런 부분도 한글로 설명 불가능해?? 가능하면 규칙으로 걸어둬". 사용자는 비개발자라 영어 중간 문구를 따라가기 어렵다.
**How to apply:** 모든 세션·모든 저장소에서 적용. show/CLAUDE.md 에도 규칙으로 적어 둠.
같은 날 긴 작업 중에 또 어겨서(중간 안내·사용량 보고·최종 답변까지 영어) 주인이 "규칙으로 한글로 설명하라고 말했었는데" 재지적.
긴 작업·도구 호출이 이어질수록 영어로 미끄러지기 쉬우니, 매 문장 쓰기 전에 한국어인지 확인할 것. 최종 답변도 예외 없음.

관련: [[user-profile]]
