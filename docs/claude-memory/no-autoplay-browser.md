---
name: no-autoplay-browser
description: 유튜브 등 자동 재생 페이지를 브라우저로 열지 말 것 — 사용자 PC에서 갑자기 소리가 남
metadata:
  type: feedback
---

유튜브(특히 쇼츠), 틱톡, 인스타 릴스처럼 열자마자 자동 재생되는 페이지를 앱 내 브라우저나 크롬으로 열지 말 것.
영상 상태 확인은 YouTube Data API(videos.list)나 curl 텍스트 조회로만 한다.

**Why:** 2026-09-04 새벽, 조회수 0 영상 확인차 쇼츠 페이지를 열었더니 PC에서 갑자기 소리가 나서 사용자가 놀라 "당장 꺼, 갑자기 영상 켜지 마"라고 했음.
**How to apply:** 브라우저로 영상 사이트를 열어야만 한다면 먼저 사용자에게 소리가 날 수 있다고 알리고 허락받기. 기본은 API·텍스트 확인.
관련: [[youtube-auto-pipeline]]
