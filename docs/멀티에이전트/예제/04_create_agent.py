# LangChain create_agent: 도구를 쓰는 에이전트 1개의 루프 확인
# 실제 모델 대신 "도구 호출 -> 최종 답" 순서로 답하는 시험용 가짜 모델을 씀 (API 키 불필요)
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

@tool
def query_hub(sql: str) -> str:
    """공유 DB(hub.sqlite)에 읽기 전용 SQL을 실행해 결과를 돌려준다."""
    return "ok"

class FakeToolModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kw):   # 가짜 모델이라 도구 목록은 무시
        return self

model = FakeToolModel(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "query_hub", "args": {"sql": "select 1"}, "id": "c1"}]),
    AIMessage(content="조회 결과는 ok 입니다"),
]))
# 실제로 쓸 때는 model="anthropic:모델이름" 처럼 문자열로 넘기고 API 키를 설정한다
agent = create_agent(model=model, tools=[query_hub], system_prompt="너는 운영 비서다.")
out = agent.invoke({"messages": [{"role": "user", "content": "지난주 조회수?"}]})
print("흐름:", " -> ".join(type(m).__name__ for m in out["messages"]))
print("최종 답:", out["messages"][-1].content)
