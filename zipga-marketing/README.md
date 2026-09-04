# 집가(ZipGa) 마케팅 자동화 — 기본 틀

「1인 1모듈 분해안」의 M1~M6 구조를 그대로 코드로 옮긴 스켈레톤입니다.
**한 줄로 예시 데이터가 6단계를 통과합니다** (Week 0 완료 판정 기준).

```bash
python run.py --account=a
```

## 전체 흐름

```
inbox/ (촬영 원본)
  → M1 입력·정규화   → data/raw/*.mp4 + data/index.csv
  → M2 전사·자막     → data/transcript/*.json + *.srt
  → M3 클립 생성     → data/clips/*.mp4 (9:16, 자막 번인) + manifest.csv
  → M4 텍스트 생성   → data/texts.csv (인스타 캡션·쓰레드 글·쇼츠 제목)
  → M5 링크 생성     → data/links.csv (Play referrer 링크, utm 소문자·1회 인코딩)
  → M6 발행 큐       → data/queue.csv (클립+문구+링크+예약시각)
  → --export         → export/{날짜}/{플랫폼}/ (발행 담당은 이 폴더만 열면 됨)
```

## 사용법 (순서대로)

1. **원본 영상을 `inbox/` 폴더에 넣는다** (앱 화면 녹화 등, 아무 형식).
   비어 있으면 테스트용 60초 샘플 영상을 자동 생성합니다.
2. **파이프라인 실행**
   ```bash
   python run.py --account=a
   ```
   계정별로 문구·링크가 달라지므로 7계정이면 a~g 각각 실행합니다.
3. **사람이 고른다** — `data/clips/manifest.csv` 를 열어 쓸 클립 확인,
   `data/queue.csv` 에서 올릴 항목의 `status` 를 `draft` → `ready` 로 변경.
4. **내보내기**
   ```bash
   python run.py --export
   ```
   `export/{오늘날짜}/{플랫폼}/` 에 영상 + caption.txt 가 묶여 나옵니다.
   각 앱(비즈니스 스위트·유튜브 스튜디오·쓰레드)에서 예약 업로드하면 끝.
   발행 후에는 queue.csv 의 status 를 `published` 로 바꾸세요 (재발행 방지).

## 폴더 구조

| 폴더/파일 | 역할 | 담당 |
|---|---|---|
| `run.py` | 관통 실행 | 공용 |
| `config.json` | 앱 이름·패키지명·발행 슬롯·해시태그 | 공용 (회의로 확정) |
| `accounts/*.json` | 계정별 각도(훅)·핸들 | 각 계정 주인 |
| `prompts/*.txt` | 마케팅 문구 템플릿 — **코드 수정 없이 톤 변경** | 마케팅 담당 |
| `m1_input/` ~ `m6_queue/` | 모듈 코드 (자기 폴더만 수정) | 1인 1모듈 |
| `data/` | 모듈 사이에 오가는 공유 파일 | 자동 생성 |
| `inbox/` | 촬영 원본을 넣는 곳 | 촬영 담당 |
| `export/` | 발행용 묶음이 나오는 곳 | 발행 담당 |

## 지금은 스텁(임시)인 부분 → 실구현으로 바꾸는 법

| 모듈 | 지금 상태 | 실구현 |
|---|---|---|
| M2 전사 | faster-whisper 없으면 샘플 전사 복사 | `pip install faster-whisper` 하면 자동으로 실제 전사 |
| M4 문구 | 템플릿 변수 치환 | 클로드에게 transcript를 주고 생성하도록 교체 (프롬프트 파일은 그대로 사용) |
| M5 측정 | 링크 생성만 | 주 1회 인사이트 수집 → 구글 시트 + 깃허브 액션 (TODO 주석 참고) |
| M6 발행 | 폴더 내보내기 (수동 업로드) | 발행량 늘면 API 자동 발행으로 확장 |
| 댓글→DM | 코드 밖 (외부 서비스) | ManyChat 등에서 별도 설정 — 코드 불필요 |

## 출시일에 바꿀 것 (마케팅 플랜 5장 체크리스트)

- `config.json` 의 `play_package` 를 실제 패키지명으로 → `run.py` 재실행하면 링크 21개 자동 재생성
- DM 자동화의 폼 링크를 Play 링크로 교체
- 프로필 링크 교체 (인스타·쓰레드·유튜브)

## 원클릭 업로더 (`uploader/`)

다른 프로그램에서 만든 영상을 `uploader/watch/` 에 넣고 **`업로드.bat` 더블클릭**하면
유튜브·인스타·쓰레드에 올라갑니다. API 연결 전에는 보조 모드(페이지 열기 + 문구 자동 복사)로 동작.
자세한 건 [uploader/설명서.md](uploader/설명서.md) 참고.

## 콘텐츠 기획 (`content/`)

출시 전 대기 기간용 영상 15개 기획: 훅 실험 6종(계정 a~f) + 씬 소재 6종 + 테스터 모집 3종.
영상별 ComfyUI 생성 프롬프트(`comfyui프롬프트/`)와 업로드 문구(`문구/`)가 세트로 준비돼 있음.
기획 수정은 `기획.json` 고치고 `python generate_files.py` 재실행. 자세한 건 [content/영상기획.md](content/영상기획.md).

## 콤피 자동 연결 (`comfy/`)

콤피(ComfyUI)가 꺼져 있어도 자동으로 켜서 영상을 만듭니다. 콤피 화면을 열 필요가 없어요.
`scenes.txt` 에 장면을 적고 **`영상만들기.bat` 더블클릭** → `uploader/watch/` 에 완성본이 저장됩니다.
자세한 건 [comfy/콤피 사용법.md](comfy/콤피%20사용법.md).

## 작업 규칙 · 기록

- [CLAUDE.md](CLAUDE.md) — 제품 정의, 금지 표현, 리스크, 일하는 원칙. **새 세션이 자동으로 읽습니다**
- [docs/결정-기록.md](docs/결정-기록.md) — 왜 이렇게 정했는지. 기획을 되돌리고 싶을 때 먼저 읽으세요
- [docs/조사-기록.md](docs/조사-기록.md) — 채널별 API 제약과 출처 (6채널 + 카카오T + 경쟁 지형)

## 리서치 · 다채널 배포 (코워크에서 통합)

스킬 9개(리서치 5 + 배포 4)와 네이버·티스토리 배포 스크립트가 들어와 있습니다.
설정은 `context/` 4개 파일에서만 고치면 전체에 반영되고, `(미설정)` 채널은 자동으로 건너뜁니다.
예약 실행은 [automation/README.md](automation/README.md) 참고.

## 규격 (첫 회의에서 합의한 그대로)

| 파일 | 만드는 모듈 | 필수 필드 |
|---|---|---|
| `data/raw/*.mp4` | M1 | H.264 / 1080p / 30fps, 파일명 `YYYYMMDD_주제슬러그` |
| `data/transcript/*.json` | M2 | `start`, `end`, `text` 배열 |
| `data/clips/*.mp4` | M3 | 9:16 / 1080×1920, 파일명 `원본명_clip01` |
| `data/texts.csv` | M4 | clip_id, platform, body, hashtags |
| `data/links.csv` | M5 | channel, os, url, campaign_id |
| `data/queue.csv` | M6 | clip_id, platform, publish_at, status |
