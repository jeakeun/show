---
name: claude-code-mode
description: 2026-11-18 Claude Code 실험 기능 Code Mode(토큰 절약) 켬 - ~/.claude/settings.json env, 되돌리기 방법
metadata:
  type: project
---
2026-11-18 주인 요청("내꺼에 토큰절약 설정해")으로 ~/.claude/settings.json 의 env 에 CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1 추가 (백업 settings.json.bak-20261118).
이 기능은 앱 내장 Claude Code 2.1.325 실행 파일에 있음 확인(문자열 확인). 터미널용 ~/.local/bin/claude(2.1.302)에는 없음 → 거기선 효과 없음.
**Why:** 해외에서 "토큰 37% 절감" 주장(검증 안 됨). 실험 기능이라 헤드리스 자동화(AI데일리·자가감사 등, [[claude-cli-path]])에도 같이 적용됨.
**How to apply:** 11/18 이후 헤드리스 자동화가 이상하게 실패하면 먼저 이 설정을 의심 → env 에서 그 줄 삭제(또는 백업 복원).
