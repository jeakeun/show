# 사람 승인: interrupt 로 멈췄다가 Command(resume=...) 로 재개
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict, total=False):
    proposal: str
    approved: bool

def propose(state: State) -> dict:
    return {"proposal": "저녁 쇼츠 훅을 숫자형으로 바꾸기"}

def approve(state: State) -> dict:
    answer = interrupt({"질문": "이 제안을 적용할까요?", "제안": state["proposal"]})
    return {"approved": answer == "적용"}

g = StateGraph(State)
g.add_node("propose", propose)
g.add_node("approve", approve)
g.add_edge(START, "propose")
g.add_edge("propose", "approve")
g.add_edge("approve", END)
app = g.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "retro-2026-10-26"}}
first = app.invoke({}, config)
print("멈춤:", app.get_state(config).next, first)
print("재개:", app.invoke(Command(resume="적용"), config))
