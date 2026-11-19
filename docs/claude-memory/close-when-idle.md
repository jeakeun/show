---
name: close-when-idle
description: "자동화는 끝나면 바로 종료, 쓸 때만 켬, 게임 위에 창 금지 — AutoCleanupLeftovers·run-hidden.vbs·대시보드 20분 자동 종료 (2026-11-02)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-04T09:40:46.322Z
---

자동화 프로그램은 업로드·작업이 끝나면 바로 꺼져야 하고, 다시 쓸 때만 켠다. 사용자는 이 PC로 게임을 한다(2026-11-05쯤 출시되는 "와우 포에버").

**Why:** 사용자가 "이건 확실히해, 안 쓰면 바로바로 종료"라고 지시했다. CPU·GPU를 게임에 양보하기 위해서다.

**How to apply:**
- 새 자동화나 서버를 만들면 끝날 때 반드시 종료되게 한다. 상주 서버는 유휴 시간이 지나면 스스로 꺼지게 한다.
- 예약 작업은 `wscript.exe ...\run-hidden.vbs` 로 창 없이 실행한다. `D:\ai-daily\run-hidden.vbs` 와 `D:\self-audit\run-hidden.vbs` 가 있다. powershell 창이 뜨면 전체 화면 게임에서 화면이 튕길 수 있다.
- 예약 작업에는 실행 시간 제한을 둔다. 우선순위는 7(보통보다 낮음)을 유지한다.
- 안전망은 `AutoCleanupLeftovers` 다. 30분마다 `D:\self-audit\cleanup-leftovers.ps1` 를 실행해, 업로드 뒤 남은 ComfyUI와 3시간 넘은 자동화 프로세스를 끈다. 끈 기록은 `cleanup.log` 에 남는다.
- 유튜브 대시보드 서버는 바탕화면 바로가기를 누를 때만 켜지고, 20분 동안 요청이 없으면 꺼진다. 시작프로그램 바로가기는 `D:\self-audit\startup-backup\` 으로 옮겨 두었다.
- 관련: [[youtube-auto-pipeline]], [[self-audit-rule]], [[ax-job-daily-tasks]]
- 2026-11-02 사용자 요청으로 시작프로그램을 정리했다. 라이엇·넥슨·레이저(Synapse·Axon·Cortex)·카카오 게임 DKBI·구글 플레이 게임즈는 시작프로그램을 끄고 서비스를 수동으로 바꿨다. 퍼플(NCSOFT)은 삭제했다. 기록과 되돌리기 정보(서비스의 원래 시작 유형)는 `D:\self-audit\startup-cleanup.log` 에 있다. Battle.net·카카오톡·Discord·Steam은 그대로 뒀다.
- **도깨비의세계 켜는 법(2026-11-04):** 이 게임(카카오 DKBI)은 실행기가 구글 플레이 게임즈로 넘겨서 돌아간다(로그 C:\Kakaogames\DKBI\logs 의 "GpgRedirect"). 사용자 말: "끌 때는 다 꺼도 돼, 다시 켜는 법만 기억하자." 그러니 정리할 때 구글 플레이 게임즈를 꺼도 된다. 게임이 안 켜진다고 하면 다음 순서로 켠다.
  1. 관리자 권한으로 `Start-Service GooglePlayGamesServices-*` 를 실행한다. `Start-Process powershell -Verb RunAs` 를 쓰고, 버전 번호는 Get-Service 로 확인한다.
  2. `explorer.exe C:\Users\Public\Desktop\도깨비의세계.lnk` 로 바로가기를 연다. 바로가기의 대상은 `DKBI_Launcher.exe -gameCode=dkbi -env=Live` 다.
  - Square.exe 나 인자 없는 런처를 단독으로 실행하면 "런처를 바로 실행 할 수 없습니다" 오류가 나며 안 켜진다.
  - 2026-11-04 기준 이 서비스는 자동 실행으로 되돌려 둔 상태다. 다음 정리 때 수동으로 바꿔도 된다.
