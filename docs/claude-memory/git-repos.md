---
name: git-repos
description: 4개 프로젝트 깃 저장소 상태 — show는 PUBLIC(2026-09-05), 나머지 3개 비공개. 프로필 리드미·핀·포크 정리 완료. 메모리 동기화 시 비밀정보 제거 필수
metadata:
  type: project
---

**2026-09-04 사용자 요청**: 다른 컴퓨터에서 클로드로 이어서 작업하려고 깃허브 비공개 저장소에 올리기.
- 로컬 저장소 4개 생성·첫 커밋 완료(브랜치 main): show(OneDrive\Desktop\show, 202파일), D:\yt-auto(58), D:\ai-daily(60), D:\coin-bot(71).
- 제외: .venv, output/영상/mp3/zip, logs, secrets/·토큰·topic.txt·uploader/config.json(쓰레드 토큰), assets/bgm, .claude/settings.local.json.
  커밋 후 키 문자열·비밀 파일명 스캔으로 0건 확인.
- 각 저장소에 CLAUDE.md(다른 PC 클로드용 안내) 작성. show/docs/claude-memory/ 에 메모리 사본 복사 — 사용자가
  "메모리 동기화"라고 하면 최신 메모리를 그 폴더로 다시 복사하고 커밋·푸시할 것.
- 깃허브 계정 jeakeun, 자격증명은 GitHub Desktop의 credential manager. gh CLI 미설치.
- **2026-09-04 10:45 푸시 완료**: https://github.com/jeakeun/{show,yt-auto,ai-daily,coin-bot} (전부 PRIVATE, 브랜치 main, origin 연결됨).
- GitHub CLI(gh 2.100) winget 설치 + `gh auth login --web` 로그인 완료(계정 jeakeun) → 이후 저장소 생성·푸시는 내가 직접 가능.
  ⚠️ 로그인 함정: Authorize 단계에서 깃허브 'Confirm access(sudo mode)'가 이메일 확인 코드를 요구 → 버튼이 안 눌리는 것처럼 보임.
  코드는 사용자가 직접 입력해야 함(내가 대신 입력 금지). Claude-in-Chrome으로 코드 입력 페이지까지는 내가 진행 가능.
- 이후 변경 반영: 각 폴더에서 `git add -A && git commit && git push` (사용자가 "깃에 올려줘"라고 하면 4개 저장소 순회).
- 규칙: 자동화(작업 스케줄러)는 메인 PC에서만. 다른 PC는 코드 수정·분석용. 이중 실행 금지.
관련: [[youtube-auto-pipeline]] [[coin-bot]] [[ax-job-daily-tasks]] [[zipga-marketing]]

**2026-09-05 깃 정리 (사용자 요청)**:
- show 저장소: 옛 유튜브 백업·AI데일리 초기 결과물을 archive/로 이동, 전체 프로젝트 개요 README 작성. yt-auto·ai-daily·coin-bot도 README 작성·푸시.
- **show를 PUBLIC으로 전환**(사용자 결정). 전환 전 docs/claude-memory/zipga-marketing.md 에서 집가 이메일·메타 앱ID·쓰레드 user_id 제거
  (메인 메모리 원본도 같이 제거 → "uploader/config.json 참고"로 대체). 히스토리 전체 스캔: 실제 토큰 0건.
  ⚠️ **메모리 동기화 규칙**: show/docs/claude-memory/ 로 복사하기 전에 이메일·앱ID·계정ID·토큰이 있는지 grep 확인. 공개 저장소임.
- yt-auto에 "1분호기심 업로더.txt"(구글 OAuth 클라이언트 시크릿)가 초기 커밋부터 들어 있었음 → 추적 해제+gitignore(2026-09-05).
  과거 커밋에는 남아 있음. **사용자 할 일: Google Cloud에서 해당 OAuth 클라이언트 시크릿 재발급** (아직 안 함).
- 프로필: jeakeun/jeakeun 저장소(README, 이름 "심재근"), 핀 6개 = show·ZipGa_Frontend·ZipGa_Backend·stage-scout·project·personal-health-coach.
  팀 저장소 포크 완료(1DAN-2ZO 3개, YH-KIKI/project, KimKobby/EscapeProject2). 사용자는 1DAN-2ZO(집가 팀)·aix-team2 조직 멤버.
- 사용자 할 일(직접): study 저장소 삭제(내가 삭제 불가), 필요시 1DAN-2ZO 멤버십 공개 전환.
- ⚠️ 자동 실행 차단(classifier): 저장소 생성·포크·공개전환 CLI, 브라우저 포크 버튼은 막힘 → 사용자가 직접 클릭. 포크 후 핀 고정은 브라우저로 가능했음.


**2026-11-09 프로필 README 전면 재정리 (사용자 "내가 만든거 기준으로")**: jeakeun/jeakeun 기본 브랜치는 **master**(main 아님). 맨 위 「한눈에 보기」 표(개인/팀·상태)로 정리. 사실 근거는 show/docs/포트폴리오.html(사용자 검수본)만 사용, 숫자는 유튜브 API로 측정. 1단2조 팀 프로젝트(nudy·집가)는 2026-11 종료, 코인 봇 종료로 표시. 지금 핀 4개 = show·ZipGa_Backend·ZipGa_Frontend·YH-KIKI/YummyPlanet.
