---
name: no-paid-work-for-unfit-jobs
description: 지원서 만들 때 필수 조건 결격(비추천) 공고는 유료 API(jobfit-agent) 돌리기 전에 걸러서 아예 만들지 않는다
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-13T17:33:07.145Z
---

필수 조건을 못 맞추는 공고(비추천)는 지원서를 만들지 않는다. 2026-11-14 67곳 회차에서 비추천 12곳까지 jobfit-agent(API 크레딧, 1곳당 약 US$0.66)로 돌려 만들었다가 사용자가 "돈 드는데 비추천은 당연히 안 만들었어야지"라고 지적.

**Why:** 사용자는 크레딧을 아껴 쓰길 원하고, 낼 수 없는 곳의 지원서는 쓸모가 없다.

**How to apply:** 공고를 모은 뒤 유료 단계 전에 공고 원문의 필수 자격(대졸·경력·특정 툴 실무·그림 실력·근무지 등)을 무료로 먼저 대조해 결격이면 "뺀 곳"으로 돌린다. 애매한 곳만 jobfit-agent로 판정. 관련: [[job-applications-2026-11]]
