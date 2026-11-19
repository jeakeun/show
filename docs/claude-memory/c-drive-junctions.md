---
name: c-drive-junctions
description: 메인 PC C드라이브 게임 폴더 7개를 D로 옮기고 정션 링크로 연결함 (2026-09-07)
metadata:
  type: project
---

2026-09-07, 메인 PC의 C드라이브 용량 부족(여유 118GB)을 해결하려고 게임 폴더 7개를 D로 옮기고
원래 자리에 **정션 링크(mklink /J)** 를 만들었다. 결과: C 여유 118.7GB → 501.6GB (401GB 확보).

| C 경로 (정션) | 실제 위치 |
|---|---|
| C:\Nexon | D:\Nexon |
| C:\AKInteractive | D:\AKInteractive |
| C:\Games | D:\Games |
| C:\Riot Games | D:\Riot Games (발로란트와 합쳐짐) |
| C:\Program Files (x86)\DNFTest | D:\DNFTest |
| C:\Program Files (x86)\Steam\steamapps | D:\SteamAppsMain |
| C:\Program Files\JOYCITY | D:\JOYCITY |

**주의: 이 경로들은 실제 폴더가 아니라 링크다.** 용량 계산·백업·삭제 작업을 할 때 중복 집계되거나
링크를 따라가 D의 원본을 지우지 않도록 robocopy는 `/XJ`, 탐색은 ReparsePoint 속성 확인이 필요하다.

아직 C에 남은 정리 후보 (사용자가 이번 범위에서 제외): Unity 에디터 4버전 66GB(구버전 3개 2024년 이후 미사용),
ComfyUI(AppData\Local\Comfy-Desktop) 50.7GB, C:\Download\maplestory 36.3GB(메이플 설치파일, 게임은 이미 설치됨),
Downloads 16.8GB, C:\_moved_to_D_* 찌꺼기 1.3GB. 합치면 약 170GB 추가 확보 가능.

**작업 시 배운 것 (다음에 반복하지 말 것)**
- 스크립트 로그를 `tail -f`로 감시하면 파일이 잠겨 스크립트의 로그 기록이 막히고 스크립트가 멎는다.
  로그는 폴링(`wc -l` + `sed -n`)으로 읽을 것.
- robocopy 요약 출력 텍스트 파싱(`Select-String 'Files :'`)은 승격된 세션에서 실패했다.
  검증은 **종료 코드**로 할 것: `/L` 드라이런에서 rc<8 이고 (rc -band 1)==0 이면 완전 동기화됨 (2는 대상에 추가 파일만 있다는 뜻).
- Program Files 및 C 루트 폴더를 건드리려면 관리자 권한 필요 → `Start-Process -Verb RunAs`로 UAC 승인 받아야 함.

관련: [[git-repos]]
- 2026-10-22 드라이브 정리(show/docs/handoff/2026-10-21-드라이브정리-지시서.md, show/tools/disk_scan.py): C 371.8 → 410.9GB. 지운 것: C:\_moved_to_D_* 5개, pip·uv·npm·유니티·그래픽 캐시, 이틀 넘은 임시파일, 게임 외 충돌기록, 다운로드 설치파일 2개(IntelliJ aarch64·GitKraken), yt-auto/output 9/22 이전 날짜 폴더의 영상·그림·음성(meta.json·자막은 보존). 주인이 남기라 한 것: 한컴·MySQL·이클립스 설치파일, 최대절전파일, 구글 플레이 게임즈(82GB), C:\Download\maplestory(36GB). 콤피 Wan 2.2 모델 8개는 support-yr-makeup-marketing/agent/genvideo.py 가 쓰므로 보존. 게임·넥슨 관련은 지우기 전 반드시 무엇인지 물어볼 것(주인 지시).
- 2026-10-22 (이어서): LD플레이어 제거(D, 17.4GB), 퍼플 설치파일 2개 삭제, 유니티 2022.3.17f1·2023.1.16f1 제거(에디터 Uninstall.exe /S - 화면 클릭 없이 됨; 2022.3.27f1·6000.3.23f1 은 프로젝트용으로 보존). 최종 C 371.8→439GB, D 835→854GB. LD플레이어 제거 프로그램의 재시작 안내 창은 관리자 권한 창이라 클릭이 안 됨 → 주인이 '나중에' 눌러야 함. 도깨비의세계 튕김: 10/15·10/18·10/22 등 4회 모두 UnityPlayer.dll 접근 위반(게임 자체 버그, 캐릭터 데이터 스트리밍 중) - 충돌기록 4개(1.3GB)는 주인 결정 대기.
