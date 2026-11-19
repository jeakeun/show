---
name: context-mode-plugin
description: "context-mode 플러그인은 show 폴더 local 범위만 켬 — user 범위로 켜져 AI데일리 WebFetch를 막던 것을 2026-11-02 끔"
metadata:
  node_type: memory
  type: project
  originSessionId: 562ed70c-c145-44df-8db3-81405ea0a070
  modified: 2026-10-28T06:25:51.911Z
---

2026-10-28 사용자가 mksglu/context-mode 플러그인을 설치함. show 폴더 전용 local 범위(.claude/settings.local.json, 깃 제외).
처음 project 범위로 깔았다가 공개 저장소에 .claude/settings.json 이 커밋될 위험 때문에 local 로 옮김.

**Why:** 이 플러그인은 도구 호출마다 훅으로 끼어들고 반복 검색을 막기도 해서, 헤드리스 클로드로 도는 자동화(AI데일리·코인 주간 회고·자가감사)에 깔리면 조용히 멈출 수 있음 ([[claude-cli-path]] 사고와 같은 종류).
**How to apply:** user 범위(전체 PC)로 넓히자는 말이 나오면 자동화 영향부터 경고. 자동화 이상 시 이 플러그인을 먼저 의심하지 말고, 적용 범위가 show 뿐인지 확인. 제거: `claude plugin uninstall context-mode@context-mode --scope local`.

**2026-11-02 사고·조치:** 실제로는 user 범위(~/.claude/settings.json)에도 설치·활성화돼 있어 PC 전체에 적용됐음 → 헤드리스 AI데일리·자가감사에서 WebFetch·curl이 막혀 뉴스가 검색 요약만으로 쓰이고 검수가 링크를 못 열었음(10/28~11/1, 자가감사 11/2 발견). `claude plugin disable context-mode@context-mode --scope user`로 user 범위만 끔. 확인: D:i-daily·D:\self-audit 에서 disabled, show 에서만 enabled(local). user 범위를 다시 켜지 말 것.
