---
name: zipga-marketing
description: "집가(ZipGa) 앱 마케팅 자동화 파이프라인 — show\\zipga-marketing 폴더, M1~M6 모듈 구조"
metadata: 
  node_type: memory
  type: project
  originSessionId: 820d9f41-5f1f-4bfe-be24-531614f2f4c1
  modified: 2026-08-27T05:21:17.602Z
---

**집가(ZipGa)**: 술자리에서 QR로 모여 미니게임 → 3판 평균 40점 미만이면 "집 가" + 카카오T 실행되는 앱. 6인 팀, 안드로이드 우선, 플레이스토어 출시 목표 (2026년 9월 중순 예상).

**마케팅 자동화 틀** (2026-08-27 구축): `C:\Users\User\OneDrive\Desktop\show\zipga-marketing`
- M1~M6 모듈 파이프라인: 영상 정규화 → 전사 → 9:16 클립 → 문구 생성 → Play referrer 링크 → 발행 큐
- `python run.py --account=a` 로 6단계 관통 (검증 완료), `--export` 로 발행용 폴더 내보내기
- 7계정(a~g) × 3채널(인스타/유튜브/쓰레드), 계정 설정은 accounts/*.json, 문구 톤은 prompts/*.txt
- 스텁 상태: M2는 faster-whisper 미설치라 샘플 전사 사용, M4는 템플릿 치환(LLM 교체 예정), M5 주간 지표 수집 미구현, config.json 의 play_package 가 예시값(com.example.zipga)

**원클릭 업로더** (2026-08-27 추가): `uploader/` 폴더 — watch/에 영상 넣고 업로드.bat 더블클릭 → 유튜브(Data API)·인스타 릴스(Graph API resumable)·쓰레드(텍스트 API) 업로드. API 미연결 시 보조 모드(페이지 열기+문구 클립보드 복사+파일 선택). 설명서.md에 플랫폼별 연결 절차 있음. 사용자가 아직 API 연결 안 함(전부 보조 모드 상태). 라이브러리 설치 완료. 참고: 사용자가 "프라임 에이전트"(Prime Intellect의 에이전트 하네스) 도입을 물었으나 클로드 코드와 역할 중복 + 윈도우 미지원이라 권하지 않기로 함.

**ComfyUI Desktop 연동** (2026-08-27): 사용자가 "콤피데스크탑"으로 영상 생성 예정. ComfyUI Desktop 1.0.44, 설치 위치 D:\aivideos\ga, 모델·출력 폴더는 C:\Users\User\AppData\Local\Comfy-Desktop\ComfyUI-Shared\ (models/, output/). API 포트 8188. RTX 4080 16GB. MiniMax H3 t2v 템플릿(총 53GB) 다운로드 중이었음(VAE·LoRA만 완료). uploader/가져오기.bat = ComfyUI output의 새 영상을 watch/로 복사(중복 방지, webm→mp4 변환). 전체 흐름: ComfyUI 생성 → 가져오기.bat → 업로드.bat. 모델 다운로드 완료 후 API로 직접 생성시키는 스크립트는 추후 과제. 사용자가 설명서.md를 "마케팅자동화 설명서.md"로 이름 바꿈.

**중요 — 제재 예방 원칙** (2026-08-27 사용자 지시): 유튜브·인스타·쓰레드 제재 안 걸리게 모든 공개 문구·영상에서 술/음주/취함/사고 단어와 장면 전면 금지 → "모임", "늦은 밤"으로 표현, 영상 프롬프트에 "No alcohol, no drinks visible" 명시. 포지셔닝은 "설치 없이 링크로 쓰는 사이트"(앱 아님). 기획.json·prompts/·config 해시태그·계정 persona 전부 이 기준으로 교체 완료(훅E는 '먼저 일어나기', 훅F는 '제일 긴 귀갓길'로 변경). 사용자가 "완전 자동화 설계" 문서 공유함(승인 게이트·긴급정지·헬스체크 개념, 발행은 공식 API — 향후 uploader 확장 참고).

**시연영상 3편 + BGM 준비** (2026-08-30): 바탕화면 "집가 시연영상.mp4/2/3" = 실제 모임 시연 촬영(1920x1080 가로, **전부 top-down 앵글이라 얼굴 안 나옴** — 손·폰·식탁만). teaser/build_demo_videos.py로 세로 3편 제작 → 22_시연_모이기(18.5초) / 23_시연_게임(23.5초, 실제 게임화면 알깨기·틀린그림찾기 포함) / 24_시연_집가(19.5초). 가로 소스는 흐린 배경 위에 가로폭 맞춰 얹고, 세로 폰녹화(집가1~3.mp4)는 crop=1080:1920:0:285로 꽉 채움. 채널별 문구 txt도 watch/에 있음. **BGM**: 콤피에 음악모델이 없어서 ACE-Step 3.5B(7.2GB)를 models/checkpoints/ace_step_v1_3.5b.safetensors 로 다운로드함. comfy/make_music.py + 음악만들기.bat 준비 완료(가사 없는 연주곡, 기본 45초). bgm/ 폴더에 음악 파일이 있으면 build_demo_videos.py가 자동으로 BGM 믹싱(볼륨 0.16, 앞뒤 페이드). **사용자가 2026-08-30 12시에 학원에서 음악 생성 예정 — 이어서 하면 됨.**

**오늘의 에러·교훈** (2026-08-28, docs/에러기록-2026-08-28.md): 발행 실패 0건. 주요 이슈 — ①ComfyUI HostBuffer 오류의 **실제 원인은 윈도우 error 1450(시스템 리소스 부족)**, 모델 19.5GB를 RAM 32GB에서 스트리밍 읽는 중 LDPlayer·Unity Hub 등이 메모리 점유해 실패. 영상 생성 전 무거운 앱 종료 권장. comfy.py에 3회 재시도로 완화. ②**인스타 권한을 내가 틀리게 적었음** — pages_read_engagement 누락, business_management 불필요. 공식문서 직접 확인 후 정정. **플랫폼 API는 공식문서 직접 확인할 것**. ③파이썬 문자열에서 윈도우 경로 ``가 백스페이스로 해석돼 문서 글자 손실 — 경로는 raw/슬래시 사용. ④브라우저 한글 자동입력이 ㄸ+ㅡ 조합을 깨뜨림(뜹니다→뜽니다) — **한글은 클립보드 붙여넣기로 입력할 것**. ⑤배너 안전영역 초과 → assert로 검증 추가. ⑥Stop-Process -Force로 6개 프로세스 종료(전부 ComfyUI 관련이라 무사했으나 위험) — 종료 전 목록 확인 필수.

**첫 배포 완료** (2026-08-28): 사이트 https://zip-ga-frontend.vercel.app/ 오픈(Vercel). 3채널 모두 발행함.
- **유튜브**: 채널 "난 집이 좋더라"(@난집이좋더라, ID UCOyqHGlO-pNcBjZLKDKELTg). 15초 티저 전체공개 게시 → https://youtube.com/shorts/GXpWy6JB4Eo (조회수 124+). 채널 설명·배너(teaser/assets/banner.jpg)·링크버튼·댓글 세팅 완료. 전화번호 인증해서 중급기능 활성화 → 댓글 링크는 활성화됐으나 **설명란 링크와 댓글 고정은 반영 지연**(최대 24시간) — 나중에 재시도 필요.
- **쓰레드**: **API 자동 연결 완료**. 앱 zipga-threads(앱ID·Threads앱ID는 uploader/config.json 참고), 테스터 계정 hellohomeplz(user id는 uploader/config.json 참고), 토큰은 uploader/config.json에 저장(threads.enabled=true). 글 2개 게시(4_질문형 → 1_메인글).
- **인스타**: 사용자가 릴스 직접 업로드 완료. 웹 자동화는 reCAPTCHA로 차단됨 — API 연결(앱 zipga-uploader, 앱ID는 uploader/config.json 참고)은 아직 미완료.
- 소재: teaser/(build_teaser.py --short --link, build_banner.py, build_ig_cover.py), instagram/, threads/ 폴더. 바탕화면에 집가_인스타_업로드용.zip, 집가_쓰레드_업로드용.zip 생성(RustDesk 전송용).
- 로고: 바탕화면 zipga_logo.png, zipga_icon.png 사용.

**업로더 5채널 + 채널별 실행** (2026-08-28): uploader/upload.py에 --only 플래그 추가, 채널 5개로 확장(youtube·instagram·threads·naver_blog·tistory). 채널별 bat: 1_유튜브만~5_티스토리만.bat. 채널별 실행 시엔 watch에서 파일을 옮기지 않음(다른 채널에 또 올려야 하므로), 전체 실행(업로드.bat)일 때만 uploaded로 이동. 네이버블로그는 openapi.naver.com/blog/writePost.json 구현(액세스토큰 필요, 발급 가능 여부 미확인). 티스토리는 API 종료라 보조 모드만. config.json은 기존 값 유지하며 새 키만 자동 추가. **인스타 권한 정정**(공식문서 확인): Facebook Login 방식은 instagram_basic·instagram_content_publish·pages_read_engagement(내가 처음 적었던 business_management는 불필요, pages_read_engagement가 누락돼 있었음), Instagram Login 방식은 instagram_business_basic·instagram_business_content_publish. PPA 걸린 페이지는 게시 차단됨.

**티저 제작** (2026-08-28): teaser/ 폴더 — 바탕화면 집가1~3.mp4(실제 앱 녹화, 1080x2340)를 crop=1080:1920:0:285로 브라우저UI 제거 → 폰 프레임(PIL 생성) 안에 넣고 콤피 보케 배경 위에 합성. build_assets.py(프레임·자막 PNG), build_teaser.py(30초 / --short 15초). 배경은 teaser/assets/배경_보케.mp4. 소리는 녹화 원본을 loudnorm I=-16으로 정규화(원본이 -30dB로 너무 작았음). 결과물 20_유튜브_티저_30초.mp4, 21_유튜브_티저_15초.mp4. 앱 화면을 AI로 그리지 않는 이유: 한글이 깨짐.

**코워크 ZIP 통합 완료** (2026-08-28): jipga-marketing.zip 받아서 병합함. 들어온 것: .claude/skills/ 9개(daily-brief·competitor-watch·market-trends·voice-of-customer·keyword-aso / publish-video·write-post·setup-publishing·publish-tistory), context/ 4개(research-profile·sources·report-style·publish-profile — 여기만 고치면 스킬 전체 반영, "(미설정)" 채널은 스킬이 건너뜀), scripts/ 4개(youtube_upload·meta_post·naver_post·upload_media), automation/(run-research.bat·run-publish.bat), cowork-plugins/, docs/결정-기록.md(결정7개+미결5개), docs/조사-기록.md. CLAUDE.md는 양쪽 병합해 하나로 재작성. **핵심 결정3**: "취했다" 판정 안 함 → 경쟁조사 1순위가 음주측정앱→술게임앱으로 바뀜, ASO에서 "음주측정" 계열 제외. 결정6: 카페 자동게시 안전규칙(사람이 확인한 게시판만·카페마다 새 글·주1회·10분간격·재시도 없음). 영상 위치 두 곳: 콤피는 uploader/watch/, 배포 스킬은 videos/ 참조 → 스킬로 배포 시 복사 필요.

**코워크 세션 통합** (2026-08-27): 사용자가 Cowork의 "마케팅 에이전트 구축" 채팅 내용을 붙여넣음(세션 ID cse_로 시작 — CCD에서 접근 불가, 복붙/아티팩트 링크/파일로만 전달 가능). 그쪽에서 만든 Jipga marketing ZIP은 아직 미다운로드. 그 내용 기반으로 CLAUDE.md(제품정의·금지표현·리스크A카카오T/B40점근거·원칙6개·채널별 발행방식·미완료 체크리스트)와 docs/조사-기록.md 생성. **중요 정정**: Cowork은 "인스타도 공개 URL 필요(R2 써라)"고 했으나 실제로는 resumable upload로 로컬 파일 직접 업로드 가능(웹 검색으로 확인, uploader/upload.py가 이미 그 방식). 공개 URL이 진짜 필요한 건 쓰레드 영상뿐. Cowork에 예약작업 2개(매일 8시 리서치, 화·금 6시 배포) 살아있음 — 로컬 스케줄러와 중복 주의. 6채널 확장(네이버블로그·카페·티스토리 추가) 논의됨, 티스토리는 Open API 종료로 브라우저 자동화만 가능.

**콤피 자동 연결** (2026-08-27): comfy/ 폴더 — comfy.py가 ComfyUI 서버 꺼져 있으면 자동 기동(Comfy Desktop installations.json에서 설치경로 탐색 → .venv python으로 main.py --port 8188 헤드리스 실행, comfy_paths.yaml로 모델경로 지정). workflow_api.json은 생성된 mp4의 prompt 메타데이터에서 추출한 API 워크플로(노드: 140:131 프롬프트, 140:129 시드, 115 해상도, 140:133 초). 브라우저 없이 생성 가능. 실패 시 30초 후 3회 자동 재시도(서버 기동 직후 HostBuffer 오류가 간헐 발생). scenes.txt에 장면 적고 영상만들기.bat 더블클릭 → uploader/watch/에 이어붙인 완성본. 초안 0.4MP 장면당 3분 / 고화질 1.0MP(768x1376) 장면당 12분. GPU 로컬 실행이라 토큰·비용 0.

**콘텐츠 팩** (2026-08-27): content/ 폴더 — 출시 전 영상 15개 기획(훅 실험 6종 a~f 계정 배정, 씬 소재 6종, 테스터 모집 3종). 기획.json이 원본, generate_files.py가 comfyui프롬프트/·문구/ txt와 영상기획.md 생성. 워크플로: ComfyUI에 프롬프트 복붙 → 가져오기.bat → 영상 이름을 슬러그로 변경 → 문구 txt 복사 → 업로드.bat. 출시 전이라 문구에 링크 없음, CTA는 댓글 "점수"/"테스터".

출처 문서: Downloads 의 노션 export zip (프로젝트_개요, 마케팅-출시플랜-3주4주 등) + 클로드 아티팩트 "1인 1모듈 분해안", "8주 무인 운영 설계".

**유튜브 예약 발행 (2026-08-31 설정)**: 집가 채널(UCOyqHGlO-pNcBjZLKDKELTg)에 쇼츠 4편 예약 완료 — 8/31(월) 21시 22_시연_모이기 / 9/2(수) 21시 23_시연_게임 / 9/4(금) 21시 24_시연_집가 / 9/5(토) 21시 25_시연_풀버전 (사용자 요청으로 19시->21시 변경). 시간대 GMT+9. 유튜브 API 미연결(uploader/secrets 비어 있음)이라 브라우저로 직접 올림. **주의 2가지**: (1) 브라우저 file_upload는 10MB 제한 — 25번(20MB)은 crf26으로 재인코딩한 watch/_업로드용/25_crf26.mp4를 올림. (2) 크롬 자동번역이 켜지면 스튜디오 화면의 한글 제목까지 엉뚱하게 번역돼 보임(저장값은 정상) — youtube.com/?persist_hl=1&hl=ko 로 언어 고정하면 안 걸림. 빈 입력칸에 Ctrl+A를 누르면 글자 'a'가 입력되므로, 빈 칸에는 Ctrl+V만 할 것.

**쓰레드 자동 발행 (2026-08-31 설정)**: 쓰레드 계정 @hellohomeplz, user_id는 config.json에 채워 넣음(원래 비어 있었음). `uploader/threads_post.py --file <txt>` 가 글 하나만 올림(upload.py는 watch 폴더 전체를 돌아서 예약용으로 못 씀). 윈도우 작업 스케줄러 \ZipGa\ 폴더에 ZipGa_Threads_0831/0902/0904/0905 등록, 각 21시 1회. **쓰레드·인스타 API 모두 예약 기능이 없어서 PC가 그 시각에 켜져 있어야 함**(StartWhenAvailable 끔 — 놓치면 새벽에 올라가는 것보다 안 올라가는 게 낫다). 쓰레드 영상 게시는 공개 URL이 필요해 텍스트+링크로만 나감. 인스타는 API 미연결(프로페셔널 전환+페이스북 페이지+Meta 검수 필요).
