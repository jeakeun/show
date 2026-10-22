# LangChain create_agent: 도구를 쓰는 에이전트 1개의 루프 확인
# 실제 모델 대신 "도구 호출 -> 최종 답" 순서로 답하는 시험용 가짜 모델을 씀 (API 키 불필요)
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

@tool
def get_weekly_views(week_start: str) -> str:
    """week_start(YYYY-MM-DD, 월요일)부터 7일간 채널 조회수 합계를 돌려준다. 읽기 전용."""
    return f"{week_start} 주간 합계 13,420회"   # 실제로는 정해진 쿼리에 날짜만 넣어 조회

class FakeToolModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kw):   # 가짜 모델이라 도구 목록은 무시
        return self

model = FakeToolModel(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "get_weekly_views", "args": {"week_start": "2026-10-12"}, "id": "c1"}]),
    AIMessage(content="지난주 조회수는 13,420회입니다"),
]))
# 실제로 쓸 때는 model="anthropic:모델이름" 처럼 넘긴다 (langchain-anthropic 설치 + API 키 필요)
agent = create_agent(model=model, tools=[get_weekly_views], system_prompt="너는 운영 비서다.")
out = agent.invoke({"messages": [{"role": "user", "content": "지난주 조회수?"}]})
print("흐름:", " -> ".join(type(m).__name__ for m in out["messages"]))
print("최종 답:", out["messages"][-1].content)
