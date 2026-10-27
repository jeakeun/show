# 레거시 시스템 연계: 읽기 도구는 자유롭게, 쓰기 도구는 사람 승인 뒤에
import sqlite3
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ToolCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

# "레거시" DB (실제로는 회사의 기존 DB. 여기서는 메모리 DB로 흉내)
legacy = sqlite3.connect(":memory:", check_same_thread=False)
legacy.executescript("""
CREATE TABLE channel_daily(day TEXT PRIMARY KEY, views INTEGER);
INSERT INTO channel_daily VALUES ('2026-10-19', 2100), ('2026-10-20', 1850), ('2026-10-21', 1990);
CREATE TABLE upload_control(id INTEGER PRIMARY KEY, paused INTEGER, reason TEXT);
INSERT INTO upload_control VALUES (1, 0, '');
""")

@tool
def get_channel_views(start_day: str, end_day: str) -> str:
    """채널 일별 조회수를 조회한다. 날짜는 YYYY-MM-DD. 최대 31일. 읽기 전용."""
    rows = legacy.execute(                       # 자유 SQL 대신 정해진 쿼리 + 파라미터
        "SELECT day, views FROM channel_daily WHERE day BETWEEN ? AND ? ORDER BY day LIMIT 31",
        (start_day, end_day)).fetchall()
    total = sum(v for _, v in rows)              # 숫자는 도구(코드)가 계산해서 돌려줌
    return f"{len(rows)}일, 합계 {total}회, 일별 {rows}"

@tool
def pause_uploads(reason: str) -> str:
    """자동 업로드를 일시 중지한다. 되돌리기 어려운 쓰기 작업이라 사람 승인이 필요하다."""
    legacy.execute("UPDATE upload_control SET paused=1, reason=? WHERE id=1", (reason,))
    return "업로드 일시 중지됨"

# 가짜 모델: 조회 -> 중지 요청 -> 마무리 순서로 도구를 부르는 척
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
class Fake(GenericFakeChatModel):
    def bind_tools(self, tools, **kw): return self
model = Fake(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "get_channel_views", "args": {"start_day": "2026-10-19", "end_day": "2026-10-21"}, "id": "t1"}]),
    AIMessage(content="", tool_calls=[{"name": "pause_uploads", "args": {"reason": "조회수 급락 점검"}, "id": "t2"}]),
    AIMessage(content="조회 후 업로드를 중지했습니다."),
]))

agent = create_agent(
    model=model,
    tools=[get_channel_views, pause_uploads],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"pause_uploads": True}),     # 쓰기 도구만 승인 필요
        ToolCallLimitMiddleware(run_limit=5),                               # 폭주 방지
    ],
    checkpointer=InMemorySaver(),
)
cfg = {"configurable": {"thread_id": "ops-1"}}
out = agent.invoke({"messages": [{"role": "user", "content": "최근 조회수 보고 이상하면 업로드 멈춰"}]}, cfg)
print("1) 멈춘 곳:", agent.get_state(cfg).next, "| 승인 요청:", [i.value["action_requests"][0]["name"] for i in out["__interrupt__"]])
print("   그 사이 DB paused =", legacy.execute("SELECT paused FROM upload_control").fetchone()[0])
out = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), cfg)
print("2) 승인 후 DB paused =", legacy.execute("SELECT paused FROM upload_control").fetchone()[0], "|", out["messages"][-1].content)
print("   조회 도구 결과:", [m.content for m in out["messages"] if getattr(m, "name", "") == "get_channel_views"][0])
