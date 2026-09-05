# show 작업공간 — 클로드 안내 (다른 컴퓨터에서 이어서 작업할 때 먼저 읽을 것)

이 저장소는 사용자(한국어, 비개발자, 단계별 안내 필요)의 자동화 프로젝트 모음입니다.
**먼저 `README.md`(프로젝트 전체 개요)와 `docs/claude-memory/MEMORY.md` 및 그 폴더의 메모리 파일들을 읽고 상황을 파악하세요.**
(메인 PC 클로드의 메모리 사본. 메인 PC에서 "메모리 동기화"라고 하면 최신본으로 갱신됨.)

## 저장소 구성 (총 4개, 전부 비공개)
| 저장소 | 내용 | 메인 PC 위치 |
|---|---|---|
| show (이 저장소) | 집가 마케팅(zipga-marketing), 브이튜버 몽글이(vtuber), 옛 백업(archive/ — 유튜브 코드·AI데일리 초기 결과물) | OneDrive\Desktop\show |
| yt-auto | 유튜브 "1분호기심" 완전 자동화 (실제 운영 코드) | D:\yt-auto |
| ai-daily | AX 취업 채용공고·뉴스논문 일일 수집 | D:\ai-daily |
| coin-bot | 코인 모의투자 봇 | D:\coin-bot |

메인 PC에만 있고 깃에 없는 것: `D:\notify`(폰 푸시, topic.txt는 비밀), `D:\self-audit`(주간 자가감사),
각 저장소의 secrets/·토큰·.venv·영상 결과물·BGM.

## 다른 컴퓨터에서 세팅하는 법
1. 4개 저장소를 같은 이름으로 클론 (가능하면 D:\yt-auto 처럼 메인 PC와 같은 경로).
2. 파이썬 3.12 설치 → 각 폴더에서 `python -m venv .venv` → `.venv\Scripts\pip install -r requirements.txt`.
3. 비밀 파일은 메인 PC에서 직접 복사(USB/원격): yt-auto\secrets\, zipga-marketing\uploader\config.json, notify\topic.txt.
4. **자동 실행(작업 스케줄러)은 메인 PC에서만 돌아갑니다.** 다른 컴퓨터에서는 코드 수정·분석·대시보드 열람용.
   같은 자동화를 두 PC에서 동시에 돌리면 이중 업로드·이중 매매가 나므로 절대 스케줄러를 복제하지 말 것.

## 꼭 지킬 규칙 (메모리에도 있음)
- 유튜브·쇼츠 등 자동재생 페이지를 브라우저로 열지 말 것 (PC에서 소리 남). 영상 상태는 API로만 확인.
- 이상 징후를 보면 사용자가 묻기 전에 먼저 보고.
- .bat/.ps1 파일에 한글·이모지 금지 (CP949 깨짐).
- 토큰·비밀 파일은 어떤 경우에도 커밋 금지.
