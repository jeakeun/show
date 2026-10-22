# 읽기는 병렬로, 쓰기는 하나로: 지휘자가 감사 대상을 나눠 Send로 동시에 보내고, 작성자 하나가 합친다
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

class State(TypedDict, total=False):
    projects: list[str]
    findings: Annotated[list[str], operator.add]   # 병렬 결과를 덧붙여 합침
    report: str

class AuditTask(TypedDict):
    project: str

def plan(state: State) -> dict:
    return {"projects": ["yt-auto", "coin-bot", "ai-daily"]}

def fan_out(state: State) -> list[Send]:
    return [Send("audit", {"project": p}) for p in state["projects"]]

def audit(task: AuditTask) -> dict:          # 읽기 전용 감사관 (동시에 여러 개)
    return {"findings": [f"{task['project']}: 이상 없음"]}

def write_report(state: State) -> dict:      # 쓰기는 여기 한 곳
    return {"report": " / ".join(sorted(state["findings"]))}

g = StateGraph(State)
g.add_node("plan", plan)
g.add_node("audit", audit)
g.add_node("write_report", write_report)
g.add_edge(START, "plan")
g.add_conditional_edges("plan", fan_out, ["audit"])
g.add_edge("audit", "write_report")
g.add_edge("write_report", END)
print(g.compile().invoke({})["report"])
