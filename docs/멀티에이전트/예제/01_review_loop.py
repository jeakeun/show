# 평가자-최적화자: 작성 -> 검수 -> (통과/재작성/예비) 를 LangGraph로
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict, total=False):
    topic: str
    draft: str
    feedback: str
    attempts: int
    passed: bool
    result: str

def write(state: State) -> dict:
    n = state.get("attempts", 0) + 1
    draft = f"[{n}차 대본] {state['topic']}" + (" (구독 멘트 포함)" if n >= 2 else "")
    return {"draft": draft, "attempts": n}

def critique(state: State) -> dict:
    ok = "구독 멘트" in state["draft"]
    return {"passed": ok, "feedback": "" if ok else "구독 멘트 누락"}

def route(state: State) -> str:
    if state["passed"]:
        return "publish"
    if state["attempts"] >= 2:
        return "fallback"
    return "write"

def publish(state: State) -> dict:
    return {"result": "업로드: " + state["draft"]}

def fallback(state: State) -> dict:
    return {"result": "예비 대본 사용"}

g = StateGraph(State)
g.add_node("write", write)
g.add_node("critique", critique)
g.add_node("publish", publish)
g.add_node("fallback", fallback)
g.add_edge(START, "write")
g.add_edge("write", "critique")
g.add_conditional_edges("critique", route, ["write", "publish", "fallback"])
g.add_edge("publish", END)
g.add_edge("fallback", END)
app = g.compile()

print(app.invoke({"topic": "밀그램 실험"}))
