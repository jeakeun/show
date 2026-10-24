# 웹드라마 반자동 (힉스필드 + Seedance 2.5)

> 마지막 갱신: 2026-10-24 (10화 묶음 몰아보기 롱폼 자동 업로드 추가) (이전 2026-10-23 처음 만듦)

세로형 숏드라마(회당 약 1분)를 주 2~3회 유튜브 쇼츠·인스타 릴스·틱톡에 올리는 반자동 파이프라인입니다.
10화마다 묶은 **몰아보기 롱폼**(약 10분)도 유튜브에 자동으로 올립니다. 쇼츠는 새 시청자를 모으고, 롱폼은 수익 창출 조건(1년 시청 4,000시간)과 광고 수익을 맡습니다.
**영상 생성만 사람이** 힉스필드 웹사이트에서 하고, 나머지(대본·장면 지시문·편집·업로드)는 자동입니다.

- 비용: 힉스필드 Plus 무제한 약 $49/월(약 7만 원) + Claude 대본 회당 몇십 원
- 사람 손: 회차당 30분~1시간 (장면 6~9개 복사·붙여넣기·생성·다운로드)

## 흐름

| 단계 | 누가 | 실행 | 결과 |
|---|---|---|---|
| 0. 시리즈 만들기 (처음 한 번) | 🤖 | `0_시리즈만들기.bat` | `series/bible.json` (인물·장소·30화 줄거리), 인물사진 작업지시서 |
| 0-1. 인물 기준 사진 | 🙋 | 힉스필드 Image | `series/characters/<영문이름>.png` |
| 1. 대본 | 🤖 | `1_대본만들기.bat` | `episodes/ep001/script.json` + `작업지시서.html` (자동으로 열림) |
| 2. 장면 영상 | 🙋 | 힉스필드 Video · Seedance 2.5 · Unlimited 켜기 | 다운로드 폴더에 mp4 |
| 3. 가져오기 | 🤖 | `2_영상가져오기.bat` | 받은 순서대로 `clips/01.mp4 …` |
| 4. 편집 | 🤖 | `3_편집하기.bat` | `final.mp4` (1080×1920, 자막·제목·"다음 화에 계속"·배경음악·음량 맞춤) |
| 5. 업로드 | 🤖 | 작업 스케줄러 `Webdrama_Publish` (화·목·토 19:00) | 완성된 가장 앞 회차 1편을 켜진 플랫폼에 업로드, 폰 알림 |
| 6. 몰아보기 | 🤖 | 같은 작업 스케줄러 (`drama.py binge`) | 10화가 유튜브에 올라간 **다음 업로드 날** 1~10화를 이어 붙여 유튜브 롱폼으로 (챕터·썸네일·재생목록 자동). 시즌 끝(30화)에는 전편 정주행판도 |

그 밖에: `현황보기.bat`(회차별 진행·몰아보기 현황), `몰아보기미리보기.bat`(다음 몰아보기를 만들기만 해서 확인, 올리지 않음), `작업지시서열기.bat`(인물 사진을 넣은 뒤 지시서 새로 만들기), `유튜브연결.bat`.

## 규칙

- 업로드 실패 시 **자동 재시도하지 않음** (중복 게시 방지). 실패한 플랫폼은 `status.json`에 남고 폰으로 알림.
  다시 올리려면 `python drama.py publish --ep 3 --only instagram --force`.
- 하루 한 편만 올림. 올릴 완성 회차가 없으면 폰으로 "다음 회차 만들어 주세요" 알림.
- 몰아보기는 하루 한 편, 유튜브에만. 이미 쇼츠로 올라간 회차만 묶음(스포일러 방지). 업로드 실패는 자동 재시도 안 함 → 유튜브 스튜디오에서 확인 후 `python drama.py binge 1-10 --force`.
- 몰아보기 화면은 기본 **가로 16:9**(가운데 세로 영상 + 흐린 배경, TV·PC용). 8분이 넘어야 중간 광고가 붙음 (회당 1분 × 10화 ≈ 10분).
- 몰아보기 맞춤 썸네일은 **유튜브 채널 휴대폰 인증**을 해야 적용됨. 안 했으면 영상은 올라가고 썸네일만 실패 알림.
- 대본은 앞 회차 줄거리를 모두 읽고 쓰며, 같은 사건·대사·반전을 되풀이하지 않도록 지시 (1분호기심 반복 금지 원칙과 같음).
- 유튜브는 `containsSyntheticMedia`(AI 생성 표시), 틱톡은 `is_aigc`를 켜서 올림. 설명란에 AI 제작 문구 자동 추가.
- 실존 인물·연예인·기존 작품 캐릭터·브랜드는 대본에서 금지.

## 처음 설정 (아직 안 한 것)

1. **유튜브 채널**: 1분호기심과 다른 새 채널(브랜드 계정)을 만들고 `유튜브연결.bat` → 브라우저에서 **새 채널**을 고르기.
   yt-auto 의 `client_secret.json` 을 같이 씀(토큰은 `webdrama/secrets/yt_token.json` 따로). 그 뒤 `config.json`의 `youtube.enabled` 를 `true`.
2. **인스타**: 프로페셔널 계정 + 메타 앱 → `secrets/instagram.json` 에 `{"ig_user_id": "...", "access_token": "..."}`. (집가 uploader 설명서 4장과 같은 절차)
3. **틱톡**: TikTok for Developers 앱 + Content Posting API → `secrets/tiktok.json` 에 `client_key, client_secret, refresh_token`.
   **틱톡 심사 통과 전에는 "나만 보기(SELF_ONLY)"로만 올라감** → 심사 전에는 `업로드문구.txt` 를 복사해 직접 올리는 게 현실적.
4. 다 연결되면 PowerShell 에서 `setup_scheduler.ps1` 실행 (메인 PC에서만).

## 설정 (`config.json`)

| 항목 | 기본 | 뜻 |
|---|---|---|
| `model` / `effort` | claude-opus-5-5 / medium | 대본 작성 모델 |
| `episode_seconds` | 60 | 회당 목표 길이 |
| `season_episodes` | 30 | 시즌 화수 (시리즈 만들 때 줄거리 개수) |
| `downloads_dir` | 비우면 내 다운로드 폴더 | 힉스필드 영상이 저장되는 곳 |
| `bgm_dir` / `bgm_volume` | yt-auto BGM / 0.07 | 배경음악 (0 이면 끔) |
| `publish_days` / `publish_time` | 화·목·토 19:00 | 바꾸면 `setup_scheduler.ps1` 도 같이 고칠 것 |
| `binge.enabled` / `every` | true / 10 | 몰아보기 롱폼 켜기, 몇 화마다 묶을지 |
| `binge.season_full` | true | 시즌 마지막 화 뒤에 1화~끝 전편 몰아보기도 |
| `binge.layout` | landscape | landscape(가로 16:9) 또는 vertical(세로 그대로) |
| `platforms.*.enabled` | 모두 false | 연결을 마친 플랫폼만 true |

## 파일

```
drama.py        명령 모음 (series / write / sheet / collect / build / publish / binge / status / connect)
writer.py       Claude 대본·시리즈 설정 (JSON 스키마 출력)
sheet.py        작업지시서 HTML
editor.py       다운로드 가져오기 + ffmpeg 편집
publisher.py    유튜브·인스타·틱톡 업로드 (몰아보기 롱폼 포함)
binge.py        몰아보기: 묶음 차례 계산, 이어 붙이기·가로 화면·챕터·썸네일
series/         bible.json, state.json(재생목록 ID·몰아보기 기록), characters/*.png
episodes/epNNN/ script.json, status.json, 작업지시서.html, clips/, final.mp4, 업로드문구.txt
binges/epAAA-BBB/ binge.mp4, thumb.jpg (깃 제외)
secrets/        토큰 (깃 제외)
```
