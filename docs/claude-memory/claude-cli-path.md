---
name: claude-cli-path
description: 헤드리스 claude.exe 경로가 앱 업데이트로 바뀌어 ai-daily·코인 주간·자가감사가 10/2~10/4 멈춘 사고와 대처 (2026-10-05)
metadata:
  type: project
---

2026-10-02부터 Claude 앱 업데이트로 claude.exe 위치가 claude-code\<버전>\<해시>\claude.exe 로 한 단계 깊어짐.
옛 탐색(버전 폴더 바로 아래 claude.exe)이 실패 → ai-daily 채용·뉴스·논문(10/2~10/4), 코인 주간 회고(10/4), 자가감사(10/4) 전부 "claude.exe not found"로 즉시 종료.
알림도 없어서 사용자가 "10/4 감사 대시보드에 안 올라왔어"로 발견.

**Why:** 탐색이 폴더 구조 한 가지에만 의존했고, 못 찾을 때 폰 푸시가 없었음.

**How to apply:** D:\self-audit\run-audit.ps1, D:\ai-daily\run-daily.ps1, D:\coin-bot\run_weekly.ps1 는 이제 -Recurse -Depth 3 로 찾고, 실패 시 C:\Users\User\.local\bin\claude.exe(네이티브 설치본)로 대체, 그래도 없으면 폰 푸시. 헤드리스 작업이 갑자기 전부 실패하면 먼저 claude.exe 경로와 로그인(OAuth)부터 확인. [[self-audit-rule]] [[ax-job-daily-tasks]] [[coin-bot]]
