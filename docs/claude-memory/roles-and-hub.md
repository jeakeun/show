---
name: roles-and-hub
description: 역할 4칸(수집/규칙/분석/실행) 원칙, 플레이북 승인 게이트(src.approve), ai-daily 가드·streaks, 공유 저장소 D:\hub\hub.sqlite
metadata:
  type: project
---

**2026-09-07 사용자가 Cloud Compass 구조도(읽기 전용 수집 → 고정 규칙 → AI 분석은 제안만 → 승인 → 실행)를 보여주며 "추천 3가지 진행".**
정본 문서: `show\docs\역할구조.md` (깃허브 show 저장소). 원칙: 분석 LLM은 리포트·`*_proposed.md`만 쓴다. 매일 도는 실행(업로드·매매)은 승인 없이 규칙대로.

1. **플레이북 승인 게이트**: insights.py가 `data/playbook_proposed.md`에만 씀 + ntfy 푸시 + 바탕화면 `PLAYBOOK-승인대기.txt`.
   사용자가 "플레이북 적용해" → `cd D:\yt-auto && .venv\Scripts\python -m src.approve` (이전본 data/playbook_history/, 기록 approvals.jsonl, git 커밋).
   "폐기해" → `--reject "사유"`. `--status`로 대기 확인. 3일 방치 시 자가감사 🟡. 첫 제안은 9/13(일) 회고.
2. **역할 문서 + 가드 보강**: ai-daily run-daily.ps1에 코인봇식 가드(프롬프트·run-daily.ps1·streaks.py 해시 보호, 루트 새 파일 격리, 알림).
   채용 카운터는 `채용/tech_counts.jsonl`(LLM이 회차별 counts JSON 한 줄) → `streaks.py`가 `streaks.txt` 계산 → 프롬프트는 그 값을 그대로 씀.
   9/8 07:00부터 jsonl 기록 시작, 2회차 쌓이면(9/9) 자동 계산 동작 — 검증 필요.
3. **공유 저장소**: `D:\hub\hub.sqlite` (깃허브 hub 저장소, DB 파일은 제외). `ingest.py`가 run_insights.bat 끝(23:50)에 적재:
   yt_channel_daily/yt_video_daily/yt_views_10min/yt_slots/api_usage/coin_trades/coin_equity/jobs_counts. 조회 `py -3 D:\hub\query.py "SQL"`.
   아직 소비자(리포트)는 원본 파일을 읽음 — 다음 단계 후보: 회고·대시보드를 hub 기반으로 전환.
관련: [[youtube-auto-pipeline]] [[ax-job-daily-tasks]] [[coin-bot]] [[self-audit-rule]] [[git-repos]]

- **프롬프트 승인 게이트 (2026-09-14, 사용자 "프롬프트 정리·규칙 다 자동화해")**: 매주 일요일 23:50 run_insights.bat 이 회고 뒤에
  ① `src.promptlint --scheduled`(코드, 자동 수정: 프롬프트 문자열의 날짜·회고 라벨과 JSON 양식에 없는 유령 필드 "xxx는 null" 제거.
  백업 data/prompt_history/ → ast → 템플릿 스모크, 실패 시 ROLLBACK 로그) ② `src.promptaudit --scheduled`(opus-5 effort medium, 제안만:
  `data/prompt_proposed.json`(old→new hunk, 원문 1회 일치 검증)·`.md` + ntfy "YouTube prompt audit" + 바탕화면 PROMPT-승인대기.txt.
  대기 제안 있으면 건너뜀). 사용자 "프롬프트 적용해" → `python -m src.approve --prompt` / "프롬프트 폐기해" → `--prompt-reject`.
  자가감사가 3일 방치·ROLLBACK 을 점검. 첫 자동 실행 9/20(일). 린트 검증: 9/14 패치 전 원본에서 8건(날짜 4·유령 4) 정확히 제거됨.
