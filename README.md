# 유튜브 자동 트렌드 학습 → 영상 생성 → 자동 업로드 파이프라인

매일 정해진 시간에 자동으로:

1. **트렌드 수집** — 한국 유튜브 인기 급상승 영상 50개의 메타데이터(제목/태그/조회수) 분석
2. **대본 생성** — Claude AI가 트렌드에서 사람들의 관심사를 읽고 **오리지널** 지식/호기심 대본 작성
3. **영상 제작** — 무료 TTS(edge-tts) 내레이션 + 자막 + 그라데이션 배경을 ffmpeg로 렌더링
4. **자동 업로드** — YouTube API로 제목/설명/태그까지 자동 업로드

매일 쇼츠 1편, 일요일에는 롱폼 1편 추가 (config.json에서 변경 가능).

---

## ⚠️ 시작 전 꼭 읽으세요

- **수익화 정책**: 유튜브는 "대량 생산된/반복적인 콘텐츠"의 수익화를 제한합니다.
  완전 무인 운영보다는, 업로드 전 영상을 확인하고 가끔 직접 편집을 더하는 것이
  채널 승인/유지에 훨씬 안전합니다. 처음에는 `config.json`의 `privacy_status`를
  `"private"`으로 바꿔 비공개 업로드 → 검토 후 공개하는 방식을 권장합니다.
- **수익화 조건**: 구독자 및 시청시간 요건(YPP)을 채워야 수익이 발생합니다.
- **저작권**: 이 파이프라인은 남의 영상을 재사용하지 않고 메타데이터만 분석해
  오리지널 콘텐츠를 만듭니다. 배경 음악 등을 추가할 땐 저작권 프리 소스만 쓰세요.

---

## 1회 설정 (순서대로)

### 1단계. API 키 준비

`secrets/.env.example`을 복사해 `secrets/.env`로 저장하고 두 개의 키를 넣습니다.

**① Claude API 키** (대본 생성)
1. https://console.anthropic.com 접속 → 로그인
2. **API Keys** → **Create Key** → 키 복사 → `.env`의 `ANTHROPIC_API_KEY`에 붙여넣기

**② YouTube Data API 키** (트렌드 수집)
1. https://console.cloud.google.com 접속 → 상단에서 **새 프로젝트** 생성 (이름 예: `yt-auto`)
2. **API 및 서비스 → 라이브러리** → "YouTube Data API v3" 검색 → **사용 설정**
3. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → API 키**
4. 생성된 키를 `.env`의 `YOUTUBE_API_KEY`에 붙여넣기

### 2단계. 유튜브 업로드용 OAuth 설정 (같은 Google Cloud 프로젝트에서)

1. **API 및 서비스 → OAuth 동의 화면** → 사용자 유형 **외부** → 앱 이름/이메일 입력
2. **대상(Audience) → 테스트 사용자**에 본인 구글 계정(유튜브 채널 계정) 추가
3. **사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
   - 애플리케이션 유형: **데스크톱 앱**
4. 생성 후 **JSON 다운로드** → 파일명을 `client_secret.json`으로 바꿔 `secrets/` 폴더에 넣기

### 3단계. 최초 인증 + 테스트 실행

```bash
.venv\Scripts\python.exe -m src.pipeline --type shorts --no-upload
```

먼저 업로드 없이 영상이 잘 만들어지는지 확인하세요. 결과물은 `output/날짜/shorts/video.mp4`.

업로드까지 테스트:

```bash
.venv\Scripts\python.exe -m src.pipeline --type shorts
```

최초 1회 브라우저가 열리면 유튜브 채널 계정으로 로그인/동의하세요.
이후에는 `secrets/token.json`으로 자동 인증됩니다.

### 4단계. 매일 자동 실행 등록

PowerShell에서:

```bash
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
```

매일 오전 9시에 자동 실행됩니다. 시간 변경: `-Time "20:00"` 추가.
컴퓨터가 꺼져 있으면 실행되지 않으니, 그 시간에 PC가 켜져 있어야 합니다.

---

## 설정 변경 (config.json)

| 항목 | 설명 |
|---|---|
| `privacy_status` | `"public"` / `"private"` / `"unlisted"` — 처음엔 private 권장 |
| `longform_weekday` | 롱폼 만드는 요일 (0=월 ... 6=일). 롱폼 끄기: `99` |
| `shorts.voice` | TTS 목소리. 여성 `ko-KR-SunHiNeural`, 남성 `ko-KR-InJoonNeural` |
| `model` | 대본 생성 Claude 모델 |

## 폴더 구조

```
output/2026-08-02/shorts/   ← 날짜별 결과물 (trends.json, meta.json, video.mp4)
logs/2026-08-02.log         ← 실행 로그
data/used_topics.json       ← 다뤘던 주제 기록 (중복 방지)
secrets/                    ← .env, client_secret.json, token.json (절대 공유 금지)
```

## 문제 해결

- **업로드 시 quotaExceeded**: YouTube API 일일 할당량 초과. 하루 1~2개 업로드면 충분합니다.
- **OAuth "앱이 확인되지 않음" 경고**: 테스트 사용자로 본인을 추가했으면 "고급 → 이동"으로 진행 가능.
- **토큰 만료 (테스트 모드는 7일)**: OAuth 동의 화면에서 **앱 게시(프로덕션 전환)**를 하면 갱신 토큰이 만료되지 않습니다.
- **TTS 실패**: 인터넷 연결 확인 후 재실행. `pip install -U edge-tts`로 업데이트.
