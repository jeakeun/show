---
name: branch-workflow
description: 코드·설정·프롬프트 변경은 work/<작업명> 브랜치(별도 worktree)에서 검증 후 main 병합 - tools/gitwork.sh (2026-10-01)
metadata:
  type: feedback
---

모든 자동화 저장소(yt-auto, coin-bot, ai-daily, market-compass, hub)의 코드·설정·프롬프트 수정은 main에서 바로 하지 않는다.
`bash C:/Users/User/OneDrive/Desktop/show/tools/gitwork.sh start <repo> <name>` → D:\wt\<repo>-<name>(secrets·.venv 정션 링크)에서 수정·테스트 →
`finish <repo> <name>`(main에 --no-ff 병합·푸시·worktree/브랜치 정리, 예약 작업 실행 중이면 거부; 상시 src.server는 제외). 포기는 `drop`.

**Why:** 사용자 "작업할 때는 맞는 브랜치에 가서 작업하고 검증 테스트 다 끝나면 그때 메인에 머지". 라이브 폴더는 스케줄러가 바로 실행하므로 브랜치를 바꾸면 안 됨.

**How to apply:** 라이브 폴더(D:\yt-auto 등)는 항상 main. 데이터·리포트 일상 커밋은 main 그대로. 정션 제거는 Directory.Delete(비재귀)만 — worktree remove --force 전에 반드시 unlink. README 갱신 규칙 [[readme-always-current]]도 같은 브랜치에서.
