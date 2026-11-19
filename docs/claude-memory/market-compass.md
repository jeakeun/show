---
name: market-compass
description: "규제 준수 내장형 카카오 마케팅 메시지 에이전트(Radar/Guard/Dispatch) — D:\\market-compass, 비공개 깃허브, Notion, 2주안(작업일 10일) 1일차 완료(2026-09-07), 일차마다 학습 노트 필수"
metadata: 
  node_type: memory
  type: project
  originSessionId: 07650bef-26e5-4479-be3d-1d7aec8fc3ce
  modified: 2026-09-07T05:56:16.637Z
---

# market-compass (2026-09-07 시작)

- **정의**: 1인 셀러의 자연어 요청 → 대상 선정·문구 생성 → 정보통신망법·카카오 정책 위반을 **코드(Guard R01~R12)** 로 걸러낸 뒤 사람 승인 2회 → 발송(목 카카오 API). 핵심 가치 "안 걸리게". **목적: 포트폴리오 + 공부.**
- **위치**: 로컬 `D:\market-compass` (메인 PC), 깃허브 `jeakeun/market-compass` **private** (사용자 승인 없이 public 전환 금지). 기획 원문·일정·학습노트 규칙은 저장소 루트 `CLAUDE.md`.
- **Notion**: 상위 페이지 (노션 주소 비공개) — 하위: 기획서 / 구조도 / 판정 D01~D12 / 상태 머신 / 데이터 스키마 / 논문 노트 / `일정 (2주안)` DB(일차 0~11, 마일스톤 3·8·9일차) / `규칙 R01~R12` DB(제목 속성 "규칙 ID", 테스트 상태 select 0/4~4/4).
- **세 원칙(코드 리뷰 기준)**: ① 숫자는 엔진만(LLM은 의도 JSON·문구만) ② 실측·추정 컬럼 분리 ③ 발송은 `src/dispatch/executor.py` 한 곳.
- **일정**: 사용자가 12주안 거부 → **2주안(작업일 10일)** 확정 (2026-09-07). 0·1·2일차 완료(2026-09-07, 사용자가 "2일차까지만 하고 공부"). 다음 = **3일차 Guard R07~R12 + engine.py → 48/48**. Guard 설계: frozen dataclass(Message/Recipient/SendContext), RuleResult(status pass|fail|na, auto_fix dict: exclude_recipient / rewrite_body / switch_channel), RULES 등록표, apply_fix. 규칙 순서 R04→R05→R06(R05는 수신거부 줄 앞에 삽입).
- **학습 노트 규칙(사용자 요청)**: 일차마다 `docs/learning/NN-topic.md` 를 TEMPLATE.md 형식으로, 코드와 같은 커밋에. 비개발자 기준, 실제 실행 결과 포함, "포트폴리오 한 줄" 포함. README.md 목록·serving-overview.md 갱신.
- 환경: 파이썬 3.12 venv(`.venv`: pytest, faker, pyyaml). pyproject `pythonpath=["."]`, import는 `src.common.db` 형태. gh는 `"C:\Program Files\GitHub CLI\gh.exe"` 전체 경로. Git Bash에서 한글 출력 깨짐 → 확인은 PowerShell.

**Why:** 5번째 프로젝트. 사용자가 "최대한 빨리, 공부하면서, 포폴용"으로 방향을 정함.
**How to apply:** 일차 완료 시 Notion 일정 DB 상태(진행/완료)와 규칙 DB 테스트 상태를 갱신하고, 학습 노트 없이 커밋하지 말 것. 관련: [[git-repos]], [[roles-and-hub]]
