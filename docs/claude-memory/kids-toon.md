---
name: kids-toon
description: "키즈 캐릭터 만화 시험(보리와 뭉치), D:\\kids-toon, 새 키즈 채널 예정 (2026-11-18)"
metadata:
  node_type: memory
  type: project
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-24T14:29:19.460Z
---

2026-11-18 주인이 웹드라마 대신 키즈 콘텐츠 → 형식 "캐릭터 만화 시리즈", 올릴 곳 "새 키즈 채널"(아동용 지정) 선택.
시험 1화: D:\kids-toon\make_ep.py ep01 (episode.json 대본 → 캐릭터 기준 그림 2장 → 장면 그림에 기준 그림 넣어 얼굴 유지 → 대사별 제미나이 TTS(보리 Leda·뭉치 Puck) → 켄번스+색 자막). 48초, 비용 약 ₩1,200(그림 8+재시도 없음, TTS 20회).
캐릭터: 보리(아기 고슴도치, 노란 목도리), 뭉치(구름 강아지, 슬프면 비·기쁘면 무지개). 매화 교훈 1개.
주의: gemini-3.8-flash-tts 는 영어 연기 지시문을 앞에 붙이면 그대로 읽는다 → 대사만 보낼 것.
미정: 채널 만들기(주인 직접), 자동 예약 여부, 아동용 지정·광고 단가 낮음 설명함. [[youtube-auto-pipeline]] 과 별개 폴더라 운영 영향 없음.
2026-11-18 추가 결정: 2방향 매일 2편 - A 3D 아기 동요 40초(17시), B 작은 생물 몸개그 대사 없음 25초(12시), 새벽 3시 제작. 캐릭터는 섞어서 돌려 씀(A1·A2·A3 / B2·B3·보리뭉치), B1은 라바 닮아 제외. 설정 D:\kids-toon\config.json(enabled=false). 비용 하루 약 800원. 남은 것: 노래 모델(ACE-Step 1.5) 내려받기 허락, 새 채널(주인 직접).
롱폼 대비(주인 11/18 "편이 쌓이면 롱폼으로 만들 것"): 매 편 manifest.json(장면 그림·움직임 문장·seed·장면 길이·교훈), 글자 안 구운 깨끗한 영상, 소리 따로(audio_master.wav -16 LUFS). 가로 롱폼은 기본 세로+양옆 흐림, 잘된 편은 seed로 가로 재생성.
사고 11/18 03:05: self-audit 정리 작업(cleanup-leftovers.ps1)이 키즈 제작 중 콤피를 끔 → 예외에 kids-toon·compile_longform 추가. 키즈 스크립트는 반드시 절대경로(D:/kids-toon/...)로 실행해야 예외가 먹음.
11/18 03:30 노래 모델 ACE-Step 1.5 turbo AIO(10GB, Comfy-Org 공식) 주인 허락 후 설치 → ComfyUI-Shared/models/checkpoints. D:\kids-toon\make_song.py 로 40초 한국어 동요 30초 만에 생성, 가사 거의 정확히 부름(whisper 확인). 2화 몸개그 ep02.mp4 완성(25초). 채널 만들기는 11/18 낮(주인 "내일하자")으로 미룸 → 그다음 자동 예약(새벽 3시 제작, 12시·17시 업로드) 붙일 것.

## 채널 브랜딩 (2026-11-18)
- 채널명 추천 **뿅뿅마을** (유튜브 API 검색으로 같은 이름 없음 확인). 예비: 퐁퐁뭉치, 몽실방울. 이미 있음: 보리뭉치·말랑콩콩·꼬물랜드·도토리쿵·말랑팡팡·꼬마구름
- 프로필/배너/설명: D:\kids-toon\channel\ (make_art.py 그림, compose.py 글자, 채널_설정.md 설명·키워드·아동용 설정). 글꼴 MalangmalangB
- 사용자가 채널 만들면 → OAuth 연결·업로드 자동화 진행

## 채널 = 옛 영어 채널 재활용 (2026-11-18, 사용자 "니가해")
- 새 채널 대신 1-Minute Wonder(UC1unjna6kgh9W1YA37QKrmA, 구독 5·29편)를 **한국어 키즈 "뿅뿅마을"**로 전환. 업로드 토큰 = D:\yt-auto\secrets\token_wonder.json (force-ssl)
- API로 완료: 옛 영상 19편 비공개(원래 상태 백업 D:\kids-toon\channel\wonder_backup_2026-11-18.json), 배너·설명·키워드·KR/ko
- API로 안 되는 것(사용자가 스튜디오에서): 채널 이름·핸들·프로필 사진·아동용 설정(selfDeclaredMadeForKids 반영 안 됨)
- YouTubeWonderMirror 예약은 Disabled 유지 필수 (켜면 영어 과학 쇼츠가 키즈 채널에 올라감)

## 매일 자동화 (2026-11-18 가동)
- D:\kids-toon\daily.py: 대본(gemini-2.5-flash JSON, state.json 지난 제목 넣어 반복 금지) → 장면 그림(캐릭터 ref) → Wan 움직임 → B=make_silent / A=make_song+8장면 → 검사(길이·무음) → token_wonder 로 비공개+publishAt 예약(B 12:00, A 17:00), 아동용
- 예약 작업 KidsPpyongTownDaily 03:00 (run-hidden.vbs → run-daily.ps1, 실패 시 1회 재실행), 로그 D:\kids-toon\logs\, 폰 푸시 PpyongTown OK/FAIL
- 결과물 D:\kids-toon\daily\YYYYMMDD_A|B\ (manifest.json에 seed·shot_seconds → 롱폼용)
- 캐릭터 이름: A1 토리와 누나 소라, A2 아라, A3 다온이와 삐약이, B2 퐁이와 콩이, B3 느릿이와 느긋이, BM 보리와 뭉치
- 하루 비용 ≈ 그림 13장 × 57원 ≈ 740원. 업로드 2편/일 = API 할당량 3200 (yt-auto와 같은 프로젝트면 합산 주의)
- 2026-11-18 첫 업로드: A vJp9aY6EdIs 「반짝반짝 손 씻기」(A1) 17:22, B 0lTu517-rNc 「말랑말랑 구출 작전」(B2) 17:30. 도깨비의세계 게임이 켜져 있으면 Wan 장면당 2분→13분, 30분 초과로 animate 시간 초과(SystemExit) 발생 → daily.py가 SystemExit도 잡게 수정. 게임은 보호 프로세스라 종료 불가(관리자 권한 필요)
- 이어서 만들 때 캐릭터는 episode.json 값 사용(제목에 엉뚱한 이름 붙던 버그 수정)

## 벤치마킹·주간 회고 v2 (2026-11-19 주인 지시 "1분호기심보다 좋은 회고", 코덱스 설계·코드 검토)
- 설계 D:\kids-toon\docs\회고_설계_v2.md. 숫자·판정은 코드, LLM(구독 sonnet 1회)은 숫자 없는 해석+사실번호[F#]만 → 숫자 들어간 문장은 코드가 버림
- snapshot.py 하루 3번(제작 끝난 뒤 run-daily 안, 12:10·17:10 KidsPpyongTownSnapshot) → data/stats_daily.jsonl. 공개 후 48시간 실측(46~52h)끼리만 비교. 남의 채널 통계는 30일 지나면 지움(API 정책)
- experiments.py 실험 장부: 한 번에 하나, 이틀 짝 동전던지기 배정, log1p 평균차 정확 순열 검정, 끝난 뒤 한 번만 판정. 제안은 experiments.json proposals, 등록은 주인 승인 후 register()
- daily.py: arm 지시문 붙임, history에 category·title_type·experiment·arm·publish_at 기록
- weekly.py 월 02:20 (KidsPpyongTownWeekly) → retro\YYYY-MM-DD.md, 품질·정책 위험(유튜브 키즈 저품질 기준) 영상별 점검, 이야기 구조 반복 검사
- 벤치마킹 9채널 config benchmarks (vocavoca·nono·metimestudio·mooandmomo·jujiberry·cokifamily·티디키즈·치타부·니니키즈), 리서치 research\키즈시장_리서치_2026-11-19.md
- 최대 위험: 유튜브가 AI 유아 대량생산 영상 단속(2026-02 NYT 후 5채널 YPP 정지) → 반복·기괴함·줄거리 엉킴 주의
- 캐릭터 추가 허락(주인 "언제든지 더 늘려도 좋아"): A4 봄이와 콩떡이, B4 몽실이와 똑똑이 (11/19)

## 제작 안전·배경 일관성·대본 모델 (2026-11-19)
- 주인 지적: 손 씻기 편 세면대 위치가 계속 바뀌고 물 나오는 곳 이상 → "그리기 전에 안전 규칙 정해", "API 프롬프트로 해결"(비싼 그림 모델 안 씀).
- daily.py: SAFETY_RULES 한 곳(아이 키 가구·발판 없음·가구 위/안 금지·입에 물고 뛰기 금지 등) → 대본 지시·predraw_check(구독 Opus가 그리기 전 고쳐 씀)·set.png 배경 기준 그림·draw_checked(구독 Claude sonnet이 그림 보고 7문항 판정, 최대 2번 재그림, 끝까지 불합격이면 가장 나은 것+폰 알림).
- 제미나이 Flash 그림 판정은 들쭉날쭉 → Claude 판정이 정확. 발판 규칙은 발판이 떨어져 그려져 실패 → 아이 키 가구로.
- 대본: B만 구독 Opus 5.5(Codex 비교 승), A 동요는 제미나이 유지(가사 자연스러움). history.script_model 기록. 상세 docs/제작_안전_일관성.md
- 11/20 사고: B편이 draw_checked 의 push(…, "low") 인자 3개 오류로 멈춤(daily.py 의 push 는 2인자). 알림은 try 로 감싸 제작을 막지 않게 함. 확인 질문이 "두 발 다 보이게 서 있기"라 강아지(털·앉은 자세)가 다 불합격 → 앉기·털에 가린 발·작은 소품 중복은 통과로 완화. 교훈: 새 코드는 실패 경로(끝까지 불합격·알림)까지 실제 함수로 시험할 것.

## 새 채널로 이전 (2026-11-24, 주인 "새로 만들고 다 옮기자")
- 원인: 옛 @ppyongtown 14편 28일 조회 25회, 스튜디오 트래픽에 **Shorts 피드 0%**(검색48·채널페이지32). 제한 표시 없음. 벤치마킹 채널은 같은 아동용인데 수백~수백만 → 채널 이력(영어 채널 전환)·AI 대량생산 판정 의심
- 새 채널 **뿅뿅마을 @ppyongmaeul UC1RJi_NpapLrnBU_sqkI-_w** (크롬에서 생성), 토큰 D:\yt-auto\secrets\token_ppyong.json (auth_ppyong.py), 배너·설명·키워드·KR·프로필·채널 아동용 설정 완료
- kids-toon migrate.py: 옛 14편을 하루 2편(B12·A17) 다시 올림, 그동안 daily.py 새 제작 쉼, 11/25~12/1 → 12/2 제작 자동 재개. data/migrate.json
- 옛 채널 14편 비공개(목록 channel/old_ppyongtown_public_2026-11-24.json). **2026-12-08쯤 옛 채널 삭제 여부 주인에게 다시 묻기**(주인: 비공개 2주 지켜본 뒤 삭제)
- 주인은 하루 2편 유지 선택(1편 추천 거절). 새 채널도 피드 노출 0이면 원인은 대량생산 쪽

**2026-11-21 벤치마킹 확대·직업 놀이 (주인 요청, kids-toon d64c44a):** 벤치마킹 9→16채널(@sherifflabrador·@cocomelon_jobsandcareers·@kelliskorner·@kidsmilotv·@키키팝팝·@yes_neo·@tuki-tales). 구독 1위 Cocomelon 2.03억, Sheriff Labrador 1,090만. 2026년 생겨 빨리 크는 곳 공통점 = 30~66초 쇼츠 + 생활습관(화장실·손씻기·먹기)·웃음(Kelli's Korner 하루 452만 조회). A 동요 주제에 직업 놀이 노래 추가(구조만 참고, 장난감 소품, 진짜 불·칼·도로 금지). 남의 대본·캐릭터 베끼기 금지. 조사 D:\kids-toon\research\benchmark_2026-11-21.md
**2026-11-21 실험 등록 A-jobsong-2026-11 (주인 "추천대로해"):** 화·금 A = 직업 놀이 노래(b), 월·목 A = 생활습관 대조(a), 11/23~12/18 8짝. 직업 순서 경찰관→소방관→요리사→의사→버스 기사→집배원→농부→미용사(배정표 add 칸). 판정: log1p 차이 0.4(약 1.5배) 이상이면 늘림, 비슷하면 주 1회, 낮으면 끝. 마지막 영상 48시간 관측 뒤 한 번만 판정(엿보기 금지). 직업 노래는 실험 지시가 있을 때만 나옴(대조 오염 방지). experiments.register_fixed 추가. "따라 하기 동작" 제안은 12월 말 이후로 보류.
