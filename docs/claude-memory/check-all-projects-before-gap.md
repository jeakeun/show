---
name: check-all-projects-before-gap
description: "지원서에 \"~경험 없음\"을 쓰기 전에 냠냠플래닛 등 모든 프로젝트를 먼저 확인할 것 (FastAPI·Docker 오기재 지적 2026-11-14)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4385df34-e448-4566-ac22-6e315725cd78
  modified: 2026-11-14T08:17:56.926Z
---

지원서·자소서에 "OO 경험 없음"을 쓰기 전에 사용자의 모든 프로젝트(yt-auto, jobfit-agent, ai-daily, market-compass, D:\YummyPlanet 등)를 grep으로 먼저 확인한다.
2026-11-14 디밀리언 지원서에 "FastAPI·Docker 경험 없음"이라 썼다가 "냠냠플래닛에서 사용한 건데" 지적받음.

**Why:** 사용자는 냠냠플래닛(팀 프로젝트)에서 FastAPI AI 서버, GitHub Actions + Docker + AWS EC2 자동 배포를 담당했다 (D:\YummyPlanet\README.md 4. My Contribution). 없는 경험을 없다고 쓰면 불리하게 깎인다.

**How to apply:** 기술 공백을 적기 전 `grep -ril <기술명>` 으로 각 저장소 확인, 냠냠플래닛 README "My Contribution" 절을 근거로 쓴다. Vector DB(Qdrant·pgvector)는 2026-11-14 기준 어디에도 없음. 관련: [[yummy-planet]] [[job-applications-2026-11]]
