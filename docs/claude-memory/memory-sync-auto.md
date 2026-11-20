---
name: memory-sync-auto
description: 메모리 사본 동기화는 매일 밤 23:50 자동(MemorySyncNightly → show/tools/memory_sync.py), 비밀값 의심 시 중단·폰 알림 (2026-11-21)
metadata:
  type: project
---

2026-11-21 사용자 요청으로 "메모리 동기화"를 매일 밤 자동화.
- 예약 작업 `MemorySyncNightly` 매일 23:50, pythonw로 창 없이 `show/tools/memory_sync.py` 실행. 기록은 `show/tools/memory_sync.log`(깃 제외).
- 개인 파일 4개(api-billing·job-applications-2026-11·job-search-rules·jocoding-hackathon) 제외, 노션 주소 가림, docs/claude-memory만 커밋(다른 수정 파일은 안 건드림), 바뀐 게 없으면 아무것도 안 함.
- API 키·주민번호·휴대폰 번호·개인 이메일 형태가 보이면 올리지 않고 D:\notify 폰 알림.
- 새로 공개하면 안 되는 메모리 파일이 생기면 memory_sync.py의 SKIP 목록에 추가할 것.

**How to apply:** 사용자가 "메모리 동기화해"라고 하면 `python tools/memory_sync.py`로 즉시 실행해도 됨. 폰에 "Memory sync" 알림이 오면 log를 보고 원인 설명. 관련 [[session-map]] [[git-repos]]
