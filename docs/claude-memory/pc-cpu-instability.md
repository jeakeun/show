---
name: pc-cpu-instability
description: "게임 튕김 원인 = i7-13700F 인텔 13세대 불안정, BIOS H.60(2023-10)·마이크로코드 0x11F 미패치, 최신 7E01vHH 업데이트 필요 (2026-11-05)"
metadata:
  node_type: memory
  type: project
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-05T12:20:58.028Z
---

2026-11-05 사용자 "와우포에버 왜 이리 팅길까". 와우 포에버(D:\World of Warcraft\_forever_)가 그날만 8번 꺼짐(Errors 폴더 Crash_*.txt, 전부 ACCESS_VIOLATION, 2번은 D3D12Core.dll). 같은 2주 동안 도깨비(dokkaebi.exe) 14번, DxDiag 6번, 넥슨 런처 2번도 같은 메모리 오류로 꺼짐 → 게임 하나 문제가 아니라 PC 쪽.

**원인 판단:** CPU i7-13700F(인텔 13세대) + 메인보드 MSI MAG B760M MORTAR MAX WIFI(MS-7E01) BIOS **H.60(2023-10-26)**, 마이크로코드 **0x11F**. 와우 로그(gx.log)도 "Intel13And14GenStatus:Unpatched". 13·14세대 전압 불안정(Vmin shift) 수정 마이크로코드 0x129/0x12B/0x12F 가 없는 상태. 그래픽카드는 RTX 4080, 드라이버 610.88(최신 판정), WHEA 오류 0건.

**How to apply:** 해결책은 BIOS를 최신 **7E01vHH(2026-09-09)** 로 올리는 것 - MSI 지원 페이지에서 받아 USB로 M-FLASH. BIOS 업데이트는 사용자가 직접 한다(시스템 설정 변경이라 클로드가 대신 하지 않음). 업데이트 뒤에도 튕기면 CPU가 이미 손상됐을 수 있음 → 인텔 보증(13세대 연장 보증) 교환 안내. 사용자가 다시 튕긴다고 하면 BIOS 버전(Win32_BIOS)부터 확인. 관련: [[close-when-idle]]
