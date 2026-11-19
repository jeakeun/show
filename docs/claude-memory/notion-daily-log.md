---
name: notion-daily-log
description: 취몽(chwimong.com) 데일리 로그 등록법 — MCP(chwijung-mcp)로 submit_daily_log 호출. "취몽에 올려줘" = 이 절차. 노션 아님!
metadata:
  type: reference
---

**취몽 = https://chwimong.com/scrum (AI-X 교육과정 운영 시스템, 데일리 로그/포트폴리오). 노션 아님.** 사용자가 9/7·9/8 두 번 알려줌.
**등록 방법 (2026-09-08 확립)**: 사이트 제공 MCP `chwijung-mcp` (클론 D:\DailyLog-MCP, C:\Users\User\DailyLog-MCP).
- 클로드 설정에 user 스코프로 등록됨: `claude mcp add -s user chwijung -- npx -y chwijung-mcp` → 새 세션에서는 `mcp__chwijung__submit_daily_log` 도구를 직접 호출하면 됨.
- 이 세션(도구 미로드)에서는 스크립트로 호출: `python <scratchpad>/chwijung_submit.py payload.json` (stdio JSON-RPC로 submit_daily_log). 스크립트 원본은 scratchpad라 사라질 수 있음 — 없으면 같은 방식으로 다시 작성(initialize→notifications/initialized→tools/call).
- 로그인 토큰: `~/.chwijung/session.json` (9/8 17:53 연결). 만료되면 사이트 데일리 로그 → "MCP 연결" → "연결 코드 생성" → `npx chwijung-mcp connect <코드>` (일회용, 5분). `npx chwijung-mcp whoami`로 확인.
- 필드 제한: title 40자, feature_name 100자, problems/solution/result 각 200자(필수), content 6000자(마크다운, 3필드 중복 금지·의사결정/막힌 지점/배운 점), category mini|final, status pending|in_progress|completed.
- **사용자 지시: 9/7부터 category=final(파이널 프로젝트)**. 문체는 기존 글처럼 문제→해결→결과, 숫자 구체적으로.
- 웹 폼 직접 입력은 저장 버튼에서 브라우저가 멈춤(확인창) → 쓰지 말 것.
- 9/8 노션에 잘못 만든 초안(무시): (노션 주소 비공개)
