---
name: ax-job-daily-tasks
description: "AX 취업 준비용 매일 예약 작업 2개 — 아침 7시 채용공고 수집, 7시 30분 논문/뉴스 한글 요약"
metadata: 
  node_type: memory
  type: project
  originSessionId: 38286004-2e4d-4591-8257-fdf76ffa9dad
  modified: 2026-08-27T04:34:04.293Z
---

사용자는 AX(AI Transformation) 분야 취업 준비 중 (관심: Vision AI, 머신러닝/딥러닝, 파인튜닝, Claude/Cursor/GPT 등 AI 툴 활용 직무).

2026-08-03에 예약 작업 2개 생성:
- `daily-ax-job-search` — 매일 아침 7시경, 원티드/사람인/잡코리아/점핏/로켓펀치/링크드인 등에서 AX/AI 채용공고 수집. 새 공고만 정리. 기술스택 누적 분석(tech-stats.md) + 유튜브/인프런 등 공부 자료 추천 포함.
- `daily-ai-news-papers` — 매일 아침 7시 30분경, AI/AX 논문(HF Daily Papers, arXiv)과 뉴스를 쉬운 한글로 번역·정리. 새 항목만.

결과물 저장 위치: **`D:\ai-daily\`** (2026-08-07 사용자 요청으로 OneDrive 밖으로 이전 — 확정 상태.
로컬 예약 작업 2개 활성, SKILL.md 경로 5곳 모두 D:\ai-daily, seen/tech-stats 데이터 이전됨.
옛 OneDrive AI데일리 폴더는 백업본.)

**⛔ 절대 규칙 (2026-08-07 사용자 지시): 이 유튜브 세션에서는 채용공고/AI데일리를 더 이상 건드리지 않는다.**
사용자가 별도 세션("채용공고 건드는 곳")에서 직접 관리함. 제안도 하지 말 것.
(경위: 클라우드 루틴으로 전환했다가 사용자 요청으로 클라우드 전환만 취소함 — 폴더 이전은 유지.
잔재: 비활성화된 클라우드 루틴 2개가 disabled로 남아있음, claude.ai/code/routines에서 삭제 가능 — 무해.)
중복 방지: 각 폴더의 seen-jobs.md / seen-items.md 에 이미 보여준 항목 기록.

**2026-08-11 구조 전환: 윈도우 작업 스케줄러 방식으로 변경 (유튜브와 동일 구조, 클로드 앱 불필요)**
- 이유: 사용자 컴퓨터는 항상 켜져 있지만 클로드 앱이 꺼져 있어 앱 예약 작업이 계속 밀림
- 작업 스케줄러 `AIDailyJobs` 07:00 / `AIDailyNews` **08:00** (8/27에 7:30→8:00으로 변경)
  → `powershell -WindowStyle Hidden -File D:\ai-daily\run-daily.ps1 -Task jobs|news`
- **검수 에이전트 추가 (8/27, 사용자 요청)**: 생성 후 2차 claude가 prompts\review-prompt.md로 검수
  (형식/링크 5개 표본/한글 깨짐/seen 갱신 검사, 문제 직접 수정, "검수완료:" 출력해야 성공).
  검수 로그: logs\<task>-review-<날짜>.log. 검수 시간 추가로 뉴스를 8시로 옮겨 동시 실행 방지.
- ⚠️ 의심 패턴 (8/27): claude.exe 헤드리스 2개가 동시에 돌면 한쪽이 0xC000013A(콘솔 종료)로 죽는 듯
  — 두 번 재현. 예약 시간을 겹치지 않게 유지할 것. 수동 재실행도 하나씩만.
- run-daily.ps1: 최신 claude.exe(앱 번들 CLI, %APPDATA%\Claude\claude-code\<버전>\)를 자동 탐색 후
  `claude -p <프롬프트> --allowedTools "WebSearch,WebFetch,Read,Write,Edit,Glob,Grep"` 헤드리스 실행.
  프롬프트: D:\ai-daily\prompts\jobs-prompt.md / news-prompt.md (SendUserFile 제거, "완료:" 출력으로 성공 판정).
  로그: D:\ai-daily\logs\, 실패 시 바탕화면에 경고 파일 생성, 성공 시 자동 삭제.
  ⚠️ ps1은 UTF-8 BOM 필수 (BOM 없으면 PS5.1이 한글을 깨뜨려 오작동 — 실제 겪음)
  ⚠️ 클로드 앱은 MSIX/Store 앱 → 앱 안에서 보이는 %APPDATA%\Claude\claude-code 경로가 앱 밖(작업
  스케줄러)에서는 존재하지 않음. 실제 경로: %LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\
  Roaming\Claude\claude-code\<버전>\claude.exe — 스크립트가 두 경로 모두 탐색 (2026-08-12 실제 겪음)
  ⚠️ 헤드리스 claude는 작업 폴더 밖에 파일 못 씀 → 스케줄러 기본 cwd가 System32라 저장 전부 차단됐었음.
  ps1에서 Set-Location D:\ai-daily 필수 (2026-08-12 실제 겪음). 성공 판정 실패 시 exit 1 처리도 추가.
- 클로드 앱 내 예약 작업 2개(daily-ax-job-search, daily-ai-news-papers)는 중복 방지 위해 **비활성화**
- 2026-08-27: 두 작업 모두 "Failed to authenticate: OAuth session expired and could not be refreshed"로
  즉시 실패 — 8/26 새벽 앱 업데이트(2.1.221→2.1.237/241) 후 헤드리스 CLI 로그인 만료가 원인으로 추정.
  해결: cmd 창에서 claude.exe를 인터랙티브로 띄워 사용자가 재로그인 (Enter→Enter→브라우저 승인).
  같은 증상 재발 시 동일 절차로 재로그인하면 됨. ps1 버전 선택도 LastWriteTime→[version] 정렬로 개선.
- 2026-08-23: "완료:" 문구 누락으로 성공을 실패로 오판 → 성공 판정을 "오늘 날짜 리포트
  파일 존재(>500B)"로 변경. 프롬프트에 금지사항 추가(logs 폴더 접근 금지, _append_* 임시파일 금지,
  최종 출력에 리포트 전문 재출력 금지). 모델이 남긴 임시파일 4개 정리함.
- 2026-08-12: 스케줄러 환경에서 뉴스 작업 완전 검증 성공 (위 두 함정 수정 후 리포트 정상 생성).
  리포트는 파일로만 저장, 채팅 전송은 없음
- 시작프로그램 `Claude.lnk`는 남아있음(무해, 앱 자동 시작용)

참고: [[user-profile]], [[youtube-auto-pipeline]] (기존 아침 7시 유튜브 자동화와 별개)

**2026-09-06 불가침 해제 (사용자 "채용공고도 이제 건드려도 돼")**: ai-daily prompts/·run-daily.ps1 수정 가능. 첫 작업 = 자가감사 발견
"연속 0건 카운터 부풀림"(ComfyUI 기록 12일/실제 9일, 8/27 증가일에 리셋 안 함) 수정 — 회차별 실측 이력으로 재계산 + 프롬프트에
"손으로 +1 금지, 마지막 변동 회차 기준 재계산" 규칙. 여전히 수정 후엔 다음 날 결과물로 검증.
9/6 실행 내역: tech-stats.md ComfyUI 12→9일(감사 검증), CVAT 6→7일(마지막 변동 8/30), Copilot 14일(8/23 변동, 일치),
MCP·AI-POT는 기산일 미확인으로 표기(재검산 필요). jobs-prompt.md 5번에 「마지막 변동 회차」 기준 재계산 규칙 추가.
**검증 필요: 9/7 07:00 채용공고 결과물에서 카운터 줄에 「마지막 변동」이 붙는지 확인.**
**2026-09-06 사용자 지시 (jobs-prompt.md 반영)**: ①검색 범위에 마케팅·마케팅 자동화, 영상(AI 영상 제작/편집·숏폼) 추가 — 범위 확장일 뿐 우선순위 아님.
②추천 ⭐ 우선순위 = 학력무관 → 신입 가능 → 근무지 서울 구로·금천·관악·영등포·동작(5개 구). 셋 다 만족하면 「🎯 최우선 추천」 묶음으로 맨 위.
후순위 사유 한 단어 표시, 조건 미확인 시 「미확인」(추정 금지). 9/7 07:00 첫 적용 — 결과물 확인 필요.
**논문 적용 검토 (2026-09-07 사용자 "매일 논문 중 내 프로젝트에 쓸 만한 것 회고 때마다 보고")**: `prompts/papers-prompt.md` + run-daily.ps1 `-Task papers`
(검수 단계 없음, 결과 `뉴스논문/YYYY-MM-DD-논문적용검토.md`). 스케줄러 `AIDailyPapers` 매주 일 09:00 (뉴스 08:00 뒤, 자가감사 10:00 앞).
소비처: 자가감사 audit-prompt 1-3절 「이번 주 적용 후보」 + 유튜브 회고 insights 데이터 8 「🧪 논문 기반 실험 후보」.
판정 4요소: 프로젝트·적용 가능 여부(지금/조건부/불가)·기대 이익(API 비용/영상 품질/조회·참여/매매/수집 정확도, 숫자)·난이도/리스크 + 첫 실행 단계.
회고 결과를 사용자에게 전할 때 이 절을 반드시 포함할 것.
⚠️ 교훈 2026-09-08: run-daily.ps1 가드는 자기 자신도 보호 → **수집이 돌고 있는 동안 run-daily.ps1/prompts/streaks.py를 수정하면 오탐 경보 + 내 수정이 원복됨**
(9/8 뉴스 재실행 중 streaks 로그 분리 편집 → 원복 → 재적용). 수정은 작업 종료 확인(claude.exe 프로세스 없음) 후에만.
로그인 만료 복구 절차: 터미널 `claude login` → 테마 Enter → 로그인 방법 1번 Enter → 브라우저 승인. 자격증명은 ~/.claude/.credentials.json 갱신으로 확인.
