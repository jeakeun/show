---
name: installed-oss-tools
description: "2026-11-16 설치한 외부 오픈소스 도구들(마케팅 스킬 6개, save/resume-session, kordoc, watch, 코덱스 imagegen) 위치와 용도"
metadata:
  node_type: memory
  type: project
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-15T18:08:45.506Z
---

2026-11-16 해커톤 마감 후 사용자 요청으로 설치 (모두 내용 검토 후).
- 마케팅 스킬 6개 (coreyhaines31/marketingskills, MIT): ~/.claude/skills/ copywriting, marketing-psychology, ab-testing, social, video, content-strategy. 53개 중 골라 넣음(전부 넣으면 설명만 약 2만 자가 매 세션 깔려서).
- ECC(affaan-m/everything-claude-code)에서 /save-session, /resume-session 두 개만 ~/.claude/commands/ 에. 비밀정보 쓰지 말 것 규칙 덧붙임. 나머지는 ECC 훅 전제라 안 가져옴.
- kordoc 4.24.80: npm 전역 CLI (`kordoc 파일.hwp -o 파일.md`). MCP 등록은 안 함(필요할 때 CLI).
- watch (bradautomates/claude-video 0.3.2): ~/.claude/skills/watch, 엔진 local(구글 업로드 없음), SessionStart 훅은 안 넣음. yt-dlp winget 설치. 토큰 많이 들어 수동으로만.
- 코덱스 imagegen: 원래 내장(~/.codex/skills/.system/imagegen). 11/16 시험 생성 성공(ChatGPT 요금제 한도 안).
- 안 한 것: graphify·Doory·OpenMontage·ECC 통째 설치(추천 안 함). 영상·음악 생성 AI(LTX-2, ACE-Step)는 수십 GB라 따로 요청 시.

관련: [[context-mode-plugin]] [[youtube-auto-pipeline]]
- rea-video (JuneYaooo/rea-video, Apache-2.0, 2026-11-16 설치): D:/rea-video/.venv, 실행 시 PYTHONUTF8=1 필요(안 하면 cp949 오류). 모델 약 400MB는 ~/.cache/rea-video. 1분호기심 11/15 쇼츠 테스트: 자막 27줄·타이밍·TTS·스톡 BGM은 정확, 화면 종류는 "3D 렌더"로 오판(실제는 AI 이미지+5% 줌/팬), 클로드 리뷰를 넣어도 판정 안 바뀜. VLM(제미나이 키) 없이 돌림. 쓸모: 경쟁 쇼츠 벤치마킹(자막·컷 속도·BGM·서사 흐름). 복제 기능(capsule-cinema)은 유료·저작권 위험이라 안 씀. 결과 D:/rea-video/tests_out/sondike/report.html
- grill-me (mattpocock/skills, MIT, 2026-11-18 설치): ~/.claude/skills/grill-me + grilling(본체). 계획을 질문으로 파고드는 인터뷰, /grill-me 로 직접 호출. grilling에 "한국어 쉬운 말, 한 번에 3개 이하" 메모 덧붙임. handoff(=save-session과 중복)·research(토큰 많이)는 안 넣음.
- awesome-opus5-5-videos (yihui-dev, MIT, 2026-11-18 검토만): 클로드가 HTML/Canvas/Three.js 코드로 만든 애니메이션 영상 프롬프트 703개. 설치할 것 없는 프롬프트 모음. 1분호기심 설명 화면 대안으로 참고 가능.
- 코드 장면 시험 (2026-11-19): D:/code-scene-test, 11/18 쇼츠 "매직넘버7" 9.54~21.30초를 HTML Canvas 애니메이션(scene.html, render(t) 프레임별)으로 교체. playwright(전용 .venv, 설치된 크롬 channel=chrome)로 353프레임 약 1분30초 렌더, 그림값 0원. 결과 test_매직넘버7_코드장면.mp4. 파이프라인 반영은 사용자 판단 대기.
- 2026-11-20 antialgorithm 스킬(mankidev/antialgorithm, MIT, 커밋 기록 ~/.claude/skills/antialgorithm/.source-commit) 사용자 스킬로 설치. 스크립트 5개 검토(네트워크 없음), 이 PC는 python3 가 스토어 바로가기라 SKILL.md 의 명령을 python 으로 바꿈. 자동화 적용은 주인 결정대로 2곳만: jobfit AI 말투 검사(prompts.py·style.py), 뿅뿅마을 B 줄거리 지시(default_avoided 기록). 1분호기심 대본·뿅뿅마을 A 동요에는 넣지 않음(히트 공식·유아 반복과 충돌).
- 2026-11-22 watch 스킬에 WhisperX 로컬 음성 글변환 설치(사용자 "설치해", 도구 검토 세션): 백엔드 whisperx·모델 small·CPU·상세 balanced, 환경 ~/.cache/watch/whisperx-venv, 모델 ~/.cache/huggingface·~/.cache/torch/hub. 자막 없는 영상만 씀, 소리는 PC 밖으로 안 나감. 한국어가 엉터리면 WATCH_WHISPERX_LANGUAGE=ko 또는 large-v3(2.9GB). 페이스북 릴스 공개 링크는 yt-dlp로 정상 다운로드 확인(11/22), 쿠키는 기본 안 씀.
