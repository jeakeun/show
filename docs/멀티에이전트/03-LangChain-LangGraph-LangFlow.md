# LangChain · LangGraph · LangFlow

> 확인한 버전: langchain 1.4.7, langgraph 1.2.16 (2026-10-22 설치 기준).
> 아래 예제 코드는 실제로 실행해서 확인했습니다. 실행 파일은 [예제/](예제/) 폴더에 있습니다.
> 예제는 실제 모델 대신 시험용 가짜 모델과 단순 함수로 **구조만** 확인한 학습용입니다.
>
> 이 문서에서 "내가 만든 것"은 운영자인 내가 설계·운영하고 클로드 코딩 에이전트가 구현한 것을 말합니다.
> 면접에서는 "설계하고 운영했으며, 구현은 AI 코딩 도구와 함께 했다"고 정확히 말합니다.

## 1. 세 가지의 관계

| 이름 | 한 줄 정의 | 비유 | 언제 쓰나 |
|---|---|---|---|
| **LangChain** | 모델·도구·문서 검색 부품을 공급사와 상관없이 같은 방식으로 쓰게 해주는 부품 상자. 기본 에이전트(`create_agent`) 포함 | 레고 블록 | 표준적인 에이전트, RAG 부품 |
| **LangGraph** | 에이전트 흐름을 **상태 + 단계(노드) + 화살표(엣지)** 그래프로 설계하고 실행하는 엔진. 멈췄다 재개, 사람 승인, 반복 제한, 병렬 실행 | 지하철 노선도 + 운행 기록 | 멀티 에이전트, 분기·반복이 많은 흐름, 오래 도는 작업 |
| **LangFlow** | LangChain 부품을 화면에서 끌어다 연결하는 시각적 도구. 만든 흐름을 API나 MCP 서버로 바로 공개 | 조립 화면 | 빠른 시제품, 비개발자와 같이 보기 |
| (LangSmith) | 실행 추적·평가 서비스 | 블랙박스 기록 장치 | 디버깅, 품질 평가 |

알아둘 사실:
- LangChain과 LangGraph는 **2025-10에 함께 1.0**이 됐고, 2.0까지 큰 호환성 변경을 하지 않겠다고 약속했습니다.
- 1.0부터 LangChain의 `create_agent` 는 **LangGraph 위에서 돌아갑니다.** LangChain = 쉬운 입구, LangGraph = 그 밑의 엔진.
- **LangFlow는 LangChain 팀 제품이 아닙니다.** LangChain 부품을 쓰는 별도 오픈소스(MIT)이고, 지금은 IBM 소유입니다.
  IBM의 DataStax 인수가 2025-05에 끝나면서 IBM으로 넘어갔습니다.

## 2. LangChain 핵심 개념

| 개념 | 뜻 | 내 경험과 연결 |
|---|---|---|
| **모델** | `"anthropic:모델이름"` 처럼 공급사만 바꾸면 같은 코드로 다른 회사 모델 사용 | 지금은 앤트로픽·제미나이를 각자 다른 코드로 부름 |
| **도구 (Tool)** | 파이썬 함수에 `@tool` 을 붙이면 AI가 부를 수 있는 도구가 됨. **함수 설명문이 곧 AI가 읽는 사용설명서** | AI데일리 헤드리스 실행의 허용 도구 목록 |
| **에이전트** | `create_agent(model, tools, system_prompt)` → 생각·도구 호출·결과 확인 루프가 자동 | 유튜브 대본 생성은 클로드 API를 직접 호출 (서버 쪽 웹 검색 도구 사용) |
| **미들웨어** | 루프 중간에 끼우는 규칙 | 아래 표 |
| **RAG 부품** | 문서 로더, 텍스트 분할기, 임베딩, 벡터 저장소, 검색기 | → [04-RAG.md](04-RAG.md) |

**미들웨어 = 내가 손으로 만든 안전장치의 표준 부품판**

| LangChain 미들웨어 (1.4.7에 실제로 있음) | 하는 일 | 내가 직접 만든 것 |
|---|---|---|
| `HumanInTheLoopMiddleware` | 지정한 도구를 부르기 전에 멈추고 사람 승인 | 승인 대기 파일 + `src.approve` (9/7~9/20. 9/21부터는 자동 적용 후 보고, 설정 스위치로 복귀 가능) |
| `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware` | 호출 횟수 상한 | 대본 시도 2회(재생성 1회) 상한 |
| `ModelFallbackMiddleware` | 모델 호출이 오류 나면 다른 모델로 바꿔 다시 부름 | **목적만 비슷함.** 내 시스템은 모델을 바꾸지 않고, 검수 장애 시 통과(fail-open)하거나 예비 대본으로 대체함. LangGraph에서는 갈림길·대체 노드로 구현할 일 |
| `ModelRetryMiddleware`, `ToolRetryMiddleware` | 실패 시 재시도 | 해외 채널 업로드 5회 백오프 |
| `SummarizationMiddleware` | 대화가 길어지면 요약 | — |
| `PIIMiddleware` | 개인정보 가리기 | — |

**도구 + 에이전트 코드** ([예제/04_create_agent.py](예제/04_create_agent.py))

```python
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def get_weekly_views(week_start: str) -> str:
    """week_start(YYYY-MM-DD, 월요일)부터 7일간 채널 조회수 합계를 돌려준다. 읽기 전용."""
    ...   # 자유 SQL이 아니라 정해진 쿼리에 날짜만 넣음 (05 문서 원칙 2)

agent = create_agent(model=model, tools=[get_weekly_views],
                     system_prompt="너는 운영 비서다.")
agent.invoke({"messages": [{"role": "user", "content": "지난주 조회수?"}]})
```

- 실행은 시험용 가짜 모델로 확인했습니다. 실제 모델을 쓰려면 `model="anthropic:모델이름"` 처럼 넘기고, `langchain-anthropic` 설치와 API 키가 필요합니다.
- 실행 흐름은 `사용자 질문 → AI(도구 호출 결정) → 도구 결과 → AI(최종 답)` 이었습니다. 이 반복이 에이전트 루프입니다.

## 3. LangGraph 핵심 개념

| 개념 | 뜻 | 내가 손으로 만든 것 |
|---|---|---|
| **State (상태)** | 그래프 전체가 같이 보는 공유 메모 | `strategy.json`, 제안 파일 |
| **Node (노드)** | 일하는 단계. 함수 하나 또는 에이전트 하나 | 대본 작성, 검수, 렌더 |
| **Edge (엣지)** | 다음 단계로 가는 화살표 | 파이프라인 순서 |
| **Conditional edge** | 상태를 보고 갈 곳을 고르는 갈림길 | 차단급이면 재생성, 2연속이면 예비 대본 |
| **Checkpointer** | 단계마다 상태를 저장. 멈췄다 재개, 되감기 | `playbook_history` 이전본 보관 |
| **interrupt** | 사람 입력을 기다리며 멈춤. `Command(resume=...)` 로 재개하면 **그 노드를 처음부터 다시 실행** | 승인 대기 파일 + "적용해" (9/7~9/20) |
| **Send** | 같은 작업을 여러 개로 나눠 병렬 실행 | 8/27 1회성 감사에서 읽기 전용 에이전트 3기를 병렬로 돌려봄 (코드로 만든 기능은 아님) |
| **Reducer** | 병렬 결과를 합치는 규칙 (예: 리스트에 덧붙이기) | — |
| **Command** | "상태 갱신 + 다음 행선지"를 한 번에. 에이전트 사이 넘기기(handoff)에 사용 | — |

### 예제 1. 검수 루프 (평가자-최적화자) — [예제/01_review_loop.py](예제/01_review_loop.py)

내 대본 검수 게이트의 **갈림길 구조만** 흉내 낸 학습 예제입니다.
작성자는 정해진 문자열을 돌려주고, 검수는 "구독 멘트" 포함 여부만 봅니다. 실제 게이트의 경고급 규칙, 등급 낮춰 진행, fail-open은 없습니다.

```python
def route(state):                     # 갈림길: 검수 결과를 보고 다음 행선지 결정
    if state["passed"]:
        return "publish"
    if state["attempts"] >= 2:        # 재생성 상한
        return "fallback"             # 예비 대본
    return "write"

g = StateGraph(State)
g.add_node("write", write)
g.add_node("critique", critique)
g.add_node("publish", publish)
g.add_node("fallback", fallback)
g.add_edge(START, "write")
g.add_edge("write", "critique")
g.add_conditional_edges("critique", route, ["write", "publish", "fallback"])
```

```
START → write → critique ─┬─ 통과 ──────────→ publish → END
            ↑             ├─ 실패, 2회 미만 ─→ write (다시)
            └─────────────┘
                          └─ 실패, 2회째 ────→ fallback → END
```

실행 결과: 최종 상태가 `attempts: 2, passed: True` 로, 1차는 실패하고 2차에 통과했습니다.
최종 상태만 출력하므로 1차 실패 사유는 보이지 않습니다. 단계별로 보려면 `app.stream(...)` 을 씁니다.

### 예제 2. 사람 승인으로 멈췄다 재개 — [예제/02_human_approval.py](예제/02_human_approval.py)

```python
def approve(state):
    answer = interrupt({"질문": "이 제안을 적용할까요?", "제안": state["proposal"]})
    return {"approved": answer == "적용"}

app = g.compile(checkpointer=InMemorySaver())       # 멈추려면 체크포인터 필수
config = {"configurable": {"thread_id": "retro-2026-10-26"}}
app.invoke({}, config)                               # approve 에서 멈춤
app.invoke(Command(resume="적용"), config)           # 같은 thread_id 로 재개
```

- 실행 결과: 첫 호출은 `approve` 노드 안의 `interrupt` 에서 멈췄고(`next=('approve',)`), `Command(resume="적용")` 으로 재개하자 `approved: True` 로 끝났습니다.
- **함정**: 재개하면 `approve` 노드가 **처음부터 다시 실행**되고, 이번에는 `interrupt()` 가 멈추는 대신 "적용"을 돌려줍니다.
  그래서 `interrupt()` 앞에 메일 발송이나 DB 쓰기 같은 일을 두면 두 번 실행됩니다. 그런 일은 `interrupt()` 뒤나 다음 노드에 두거나, 두 번 실행돼도 괜찮게(멱등) 만듭니다.
- `thread_id` 는 "어느 작업을 이어서 할지"를 가리키는 책갈피입니다.
- `InMemorySaver` 는 프로그램을 끄면 기록이 사라지는 시험용입니다. 실제 운영에서는 DB에 저장하는 체크포인터를 씁니다.

### 예제 3. 읽기는 병렬로, 쓰기는 하나로 — [예제/03_parallel_audit.py](예제/03_parallel_audit.py)

```python
class State(TypedDict, total=False):
    findings: Annotated[list[str], operator.add]    # 병렬 결과를 덧붙여 합치는 규칙

def fan_out(state):                                  # 지휘자가 감사 대상을 나눠 동시에 보냄
    return [Send("audit", {"project": p}) for p in state["projects"]]

g.add_conditional_edges("plan", fan_out, ["audit"])  # audit 이 3개 동시에 돎
g.add_edge("audit", "write_report")                  # 보고서 쓰기는 한 곳
```

실행 결과: 감사관 3개(yt-auto, coin-bot, ai-daily)가 동시에 돌았고, 결과 3개가 합쳐져 보고서 작성 노드 하나로 들어갔습니다.

## 4. LangGraph로 멀티 에이전트를 만드는 3가지 구조

| 구조 | 어떻게 | 장점 | 주의 |
|---|---|---|---|
| **지휘자 (Supervisor)** | 중앙 에이전트가 하위 에이전트를 **도구처럼** 부르고 결과를 받음 | 흐름이 한눈에 보이고 쓰기 통제가 쉬움 | 지휘자가 병목 |
| **스웜 (Swarm, 넘기기)** | 에이전트끼리 `Command(goto=..., update=...)` 로 직접 넘김. 마지막 담당자가 다음 대화를 이어받음 | 유연함 | 쓰기가 여기저기 생기기 쉬움 |
| **계층형 (Hierarchical)** | 팀 단위를 하위 그래프(subgraph)로 묶어 중첩 | 큰 시스템을 나눠 관리 | 구조가 복잡해짐 |

- 지휘자 구조는 예전엔 별도 라이브러리(`langgraph-supervisor`)를 썼습니다. 지금 LangChain 문서는 대부분 **하위 에이전트를 도구로 감싸서 직접 만드는 방식**을 권장합니다 (출처 4).
- 내 원칙("읽기는 나누고 쓰기는 하나로")에 가장 잘 맞는 건 **지휘자 구조 + 읽기 위주 하위 에이전트 + 작성자 하나**입니다.

## 5. 직접 짠 것 vs LangGraph — 면접 핵심 표

| 필요했던 것 | 내가 직접 만든 방법 | LangGraph에서는 | 내 판단 |
|---|---|---|---|
| 재시도 상한 | 코드 카운터 (시도 2회 = 재생성 1회) | 상태 카운터 + 갈림길, 또는 호출 상한 미들웨어 | 기능은 같음. 그래프로 그려져서 남에게 설명하기 쉬움 |
| 사람 승인 | 승인대기 파일 + 승인 명령 (9/7~9/20 운영, 지금은 되돌릴 수 있는 건 자동 적용) | `interrupt` + 체크포인터 + `Command(resume)` | LangGraph는 같은 작업(thread)을 이어서 하되, 멈춘 노드는 처음부터 다시 실행. 내 방식은 단순하고 파일로 추적하기 쉬움 |
| 이전본·되돌리기 | `playbook_history` 폴더 | 체크포인트 기록 (thread별) | 되감기가 표준 기능 |
| 병렬 처리 | 8/27 1회성 감사에서 대화 안에서 3기 병렬 (코드화 안 됨) | `Send` + reducer | LangGraph로는 코드로 재현 가능한 기능이 됨 |
| 실행 추적 | 로그 파일 + 폰 알림 + 비용 기록 | LangSmith | 단계별 입력·출력·토큰을 화면으로 봄 |
| 실패 대체 | fail-open, 예비 대본 | 갈림길·대체 노드 (`ModelFallbackMiddleware` 는 모델 교체용이라 다름) | 구현 방식이 다름 |
| 중간에 죽으면 | 실패 알림 → 수동 재실행 (일부 중간 결과는 재사용) | 마지막 체크포인트부터 이어서 | LangGraph가 유리 |

면접 한 줄:
> "운영 시스템에 재시도 상한, 사람 승인, 이전본 보관을 설계해서 넣어봤기 때문에,
> LangGraph의 상태·갈림길·체크포인터·interrupt가 각각 어떤 문제를 푸는지 경험으로 압니다.
> 반대로 중간에 죽었을 때 이어서 하기와 병렬 처리는 제 시스템에 코드로 없던 부분이라, LangGraph로 채워야 할 부분입니다."

## 6. 언제 LangGraph를 쓰고, 언제 안 쓰나

**쓴다**
- 분기와 반복이 많을 때
- 사람 승인으로 멈췄다가 나중에 재개해야 할 때
- 에이전트가 여럿일 때
- 여러 사람이 같이 유지보수할 때 (그래프 자체가 설계 문서 역할)
- 중간에 죽어도 이어서 해야 하는 긴 작업일 때

**안 쓴다**
- 모델 호출 한 번으로 끝나는 일
- 순서가 고정된 단순 파이프라인 (함수를 차례로 부르는 코드가 더 읽기 쉬움)
- 외부 의존성을 최소로 해야 할 때

**주의**: LangChain은 1.0 전까지 버전마다 바뀌는 게 많기로 유명했습니다. 1.0부터 안정성을 약속했지만, 예제를 볼 때 **버전부터 확인하는 습관**이 필요합니다.
예: `langgraph.prebuilt.create_react_agent`(LangGraph 1.0에서 지원 중단 예고) → `langchain.agents.create_agent`(1.0 방식).

## 7. LangFlow

| 항목 | 내용 |
|---|---|
| 무엇 | 화면에서 부품(모델, 프롬프트, 검색기, 도구)을 끌어다 선으로 연결해 흐름을 만듦 |
| 공개 | 만든 흐름을 REST API·MCP 서버로 바로 공개. JSON으로 내보내 깃으로 버전 관리 |
| 장점 | 빠른 시제품. 기획자·현업과 화면을 같이 보며 흐름을 합의하기 좋음 |
| 한계 | 복잡한 분기, 단위 테스트, 코드 리뷰는 코드가 나음 |
| 내 계획 | 2단계에서 만든 RAG 흐름을 LangFlow로도 한 번 만들어, 코드 버전과 장단점을 비교 |

면접 한 줄:
> "LangFlow로 빠르게 흐름을 합의하고 시제품을 만든 뒤, 운영할 부분은 테스트가 가능한 LangGraph 코드로 옮기는 식으로 나눠 쓰겠습니다."

## 8. 면접 질문

<details><summary>Q1. LangChain과 LangGraph의 차이는?</summary>

LangChain은 모델·도구·검색 부품을 표준화한 부품 상자이고, 1.0부터는 `create_agent` 로 기본 에이전트를 쉽게 만듭니다.
LangGraph는 그 밑에서 도는 엔진으로, 상태·노드·엣지 그래프로 흐름을 직접 설계합니다. 체크포인트로 멈췄다 재개할 수 있고, 사람 승인과 병렬 실행을 세밀하게 제어합니다.
표준적인 에이전트는 LangChain으로, 분기·승인·멀티 에이전트처럼 흐름을 통제해야 하면 LangGraph로 갑니다.
</details>

<details><summary>Q2. 왜 에이전트를 그래프로 설계하나요?</summary>

상태가 어디서 바뀌고 어디로 갈라지는지가 그림으로 보여서 설계와 디버깅이 쉽습니다.
단계마다 체크포인트가 남아, 중간에 멈추거나 실패해도 같은 작업을 이어서 할 수 있습니다.
제 유튜브 검수 게이트의 구조를 학습 예제로 그래프로 그려보니, "작성 → 검수 → 통과/재작성/예비" 갈림길이 한눈에 드러났습니다.
</details>

<details><summary>Q3. State는 어떻게 설계하나요?</summary>

- 필요한 것만 넣습니다. 큰 데이터는 파일이나 DB에 두고 경로나 ID만 넣습니다.
- 병렬 노드가 같은 필드에 쓰면 합치는 규칙(reducer)을 정합니다.
- 최종 결과물을 쓰는 필드는 한 노드만 쓰게 합니다 (쓰기 단일화).
- 재시도 횟수처럼 흐름 제어에 필요한 값도 상태에 둡니다.
</details>

<details><summary>Q4. 사람 승인(Human-in-the-loop)은 어떻게 구현하나요?</summary>

노드 안에서 `interrupt()` 를 부르면 상태가 체크포인터에 저장되고 멈춥니다.
사람이 결정하면 같은 `thread_id` 로 `Command(resume=값)` 을 보내 재개합니다.
이때 그 노드는 **처음부터 다시 실행**되고 `interrupt()` 가 사람의 값을 돌려줍니다. 그래서 `interrupt()` 앞에는 두 번 실행되면 안 되는 일을 두지 않습니다.
도구 단위로 걸 때는 `HumanInTheLoopMiddleware` 로 특정 도구 호출 전에 멈추게 합니다.
어디에 걸지는 제 운영 원칙대로 "되돌릴 수 없는 행동 앞"입니다.
</details>

<details><summary>Q5. 멀티 에이전트 구조 중 무엇을 고르나요?</summary>

기본은 지휘자 구조입니다. 하위 에이전트는 조사·검색 같은 읽기 위주로 두고, 결과를 쓰는 건 작성자 하나로 모읍니다.
스웜은 유연하지만 쓰기가 여러 곳에서 생기기 쉬워서, 상담처럼 담당자가 자연스럽게 바뀌는 대화형에만 쓰겠습니다.
</details>

<details><summary>Q6. LangFlow는 언제 쓰나요?</summary>

현업과 흐름을 빠르게 합의하는 시제품 단계에 씁니다. 흐름을 API나 MCP 서버로 바로 공개할 수 있습니다.
운영 단계에서 분기가 복잡해지거나 테스트·코드 리뷰가 필요하면 코드(LangGraph)로 옮깁니다.
</details>

## 출처

1. LangChain, [LangChain and LangGraph Agent Frameworks Reach v1.0 Milestones](https://blog.langchain.com/langchain-langgraph-1dot0) (2025-10-22)
2. LangChain Docs, [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
3. LangChain Docs, [Multi-agent (prebuilts)](https://docs.langchain.com/oss/python/multi-agent-prebuilts) · [Custom multi-agent](https://docs.langchain.com/oss/python/multi-agent-custom)
4. LangChain Reference, [langgraph-supervisor](https://reference.langchain.com/python/langgraph-supervisor)
5. IBM, [Langflow](https://www.ibm.com/products/langflow) · Langflow Docs, [MCP server](https://docs.langflow.org/mcp-server)
6. 설치한 langgraph 1.2.16의 `interrupt` 설명: "The graph resumes from the start of the node, re-executing all logic."
