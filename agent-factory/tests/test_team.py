import json
import threading
import time

import pytest
from conftest import ScriptedLLM, agent, team, text

from agent_factory.llm import Usage
from agent_factory.spec import ReviewSpec
from agent_factory.team import ReviewVerdict, run_team

READ = ["list_files", "read_file"]


def first_user(messages):
    return messages[0]["content"]


def go(t, llm, ws_dir, tmp_path, task="작업"):
    return run_team(t, task, llm, read_root=ws_dir, runs_root=tmp_path / "runs")


def test_chain_passes_only_previous_stage(ws_dir, tmp_path):
    t = team([agent("a1"), agent("a2"), agent("a3")], [["a1"], ["a2"], ["a3"]])
    llm = ScriptedLLM(lambda who, m, *a: text(f"{who}의 결과"))
    res = go(t, llm, ws_dir, tmp_path)
    inputs = {c["who"]: first_user(c["messages"]) for c in llm.calls}
    assert "a1의 결과" in inputs["a2"]
    assert "a2의 결과" in inputs["a3"] and "a1의 결과" not in inputs["a3"]  # 맥락 보호
    assert res.final_text == "a3의 결과" and res.stopped is None
    for f in ["result.md", "summary.md", "team.yaml", "flow.md"]:
        assert (res.run_dir / f).is_file()
    assert len(list((res.run_dir / "agents").glob("*.md"))) == 3


def test_parallel_runs_together_and_merges(ws_dir, tmp_path):
    active, peak, lock = [0], [0], threading.Lock()

    def script(who, messages, *a):
        if who.startswith("scout"):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.2)
            with lock:
                active[0] -= 1
        return text(f"{who} 요약")

    t = team([agent("scout_a", READ), agent("scout_b", READ), agent("scout_c", READ), agent("writer")],
             [["scout_a", "scout_b", "scout_c"], ["writer"]])
    llm = ScriptedLLM(script)
    res = go(t, llm, ws_dir, tmp_path)
    w = [c for c in llm.calls if c["who"] == "writer"][0]
    for s in ("scout_a", "scout_b", "scout_c"):
        assert f"{s} 요약" in first_user(w["messages"])
    assert peak[0] >= 2, "병렬 단계는 동시에 돌아야 함"
    assert sum(1 for c in llm.calls if c["who"] == "writer") == 1
    assert res.final_text == "writer 요약"


def review_team(rounds=2):
    return team([agent("scout", READ), agent("writer"), agent("checker", ["read_file"])],
                [["scout"], ["writer"]],
                review=ReviewSpec(reviewer="checker", criteria=["출처"], max_rounds=rounds))


def test_review_loop_fail_then_pass(ws_dir, tmp_path):
    verdicts = iter([ReviewVerdict(passed=False, issues=["3번 문장 출처 없음"], summary="x"),
                     ReviewVerdict(passed=True, issues=[], summary="ok")])
    drafts = iter(["초안1", "초안2"])

    def script(who, messages, tools, schema, none):
        if schema is ReviewVerdict:
            return text(next(verdicts).model_dump_json())
        if who == "writer":
            return text(next(drafts))
        return text("근거 자료")

    llm = ScriptedLLM(script)
    res = go(review_team(), llm, ws_dir, tmp_path)
    assert res.review_passed is True and res.review_rounds == 2 and res.final_text == "초안2"
    writer_calls = [c for c in llm.calls if c["who"] == "writer"]
    second = first_user(writer_calls[1]["messages"])
    assert "3번 문장 출처 없음" in second and "초안1" in second and "근거 자료" in second
    checker_input = first_user([c for c in llm.calls if c["who"] == "checker"][0]["messages"])
    assert "근거 자료" in checker_input and "초안1" in checker_input and "출처" in checker_input
    assert "⚠" not in (res.run_dir / "result.md").read_text(encoding="utf-8")


def test_review_exhausted_marks_result(ws_dir, tmp_path):
    def script(who, messages, tools, schema, none):
        if schema is ReviewVerdict:
            return text(ReviewVerdict(passed=False, issues=["여전히 과장"], summary="no").model_dump_json())
        return text(f"{who} 글")

    llm = ScriptedLLM(script)
    res = go(review_team(rounds=2), llm, ws_dir, tmp_path)
    assert res.review_passed is False and res.review_rounds == 2
    assert sum(1 for c in llm.calls if c["who"] == "writer") == 2
    body = (res.run_dir / "result.md").read_text(encoding="utf-8")
    assert "통과하지 못한" in body and "여전히 과장" in body


def test_budget_stop(ws_dir, tmp_path):
    t = team([agent("a1", model="opus"), agent("a2", model="opus")], [["a1"], ["a2"]], budget_usd=0.01)
    llm = ScriptedLLM(lambda who, *a: (text(f"{who}"), Usage(input_tokens=10_000)), budget=0.01)  # 1회 $0.04
    res = go(t, llm, ws_dir, tmp_path)
    assert res.stopped and "예산" in res.stopped
    assert [c["who"] for c in llm.calls] == ["a1"]
    rows = [json.loads(x) for x in (res.run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["who"] == "a1" and rows[0]["usd"] == pytest.approx(0.04)
    assert "멈춤" in (res.run_dir / "result.md").read_text(encoding="utf-8")


def test_invalid_team_is_not_run(ws_dir, tmp_path):
    t = team([agent("aa", ["save_file"]), agent("bb", READ)], [["aa", "bb"]])
    llm = ScriptedLLM(lambda *a: text("x"))
    with pytest.raises(ValueError):
        go(t, llm, ws_dir, tmp_path)
    assert llm.calls == []


def test_writer_saves_into_run_folder_only(ws_dir, tmp_path):
    from conftest import tool_use

    def script(who, messages, *a):
        if len(messages) == 1:
            return tool_use("save_file", {"filename": "report.md", "content": "보고서"})
        return text("저장 완료")

    t = team([agent("writer", ["save_file"])], [["writer"]])
    res = go(t, ScriptedLLM(script), ws_dir, tmp_path)
    assert (res.run_dir / "files" / "report.md").read_text(encoding="utf-8") == "보고서"
    assert not (ws_dir / "report.md").exists()


# ---- 검토 지적 반영 확인 -------------------------------------------------

def test_parallel_then_parallel_runs_each_once_with_all_inputs(ws_dir, tmp_path):
    t = team([agent("a1", READ), agent("a2", READ), agent("a3", READ), agent("b1", READ), agent("b2", READ),
              agent("ww")], [["a1", "a2", "a3"], ["b1", "b2"], ["ww"]])
    llm = ScriptedLLM(lambda who, m, *a: text(f"{who} 결과"))
    res = go(t, llm, ws_dir, tmp_path)
    whos = [c["who"] for c in llm.calls]
    assert sorted(whos) == ["a1", "a2", "a3", "b1", "b2", "ww"]  # 중복 실행 없음
    for c in llm.calls:
        if c["who"] in ("b1", "b2"):
            inp = first_user(c["messages"])
            assert all(f"{x} 결과" in inp for x in ("a1", "a2", "a3")) and "결과 없음" not in inp
    assert "b1 결과" in first_user([c for c in llm.calls if c["who"] == "ww"][0]["messages"])
    assert res.final_text == "ww 결과"


def test_parallel_budget_overshoot_is_bounded(ws_dir, tmp_path):
    t = team([agent(f"p{i}", READ, model="opus") for i in range(4)] + [agent("ww", model="opus")],
             [[f"p{i}" for i in range(4)], ["ww"]], budget_usd=0.05)

    def script(who, *a):
        time.sleep(0.05)
        return text(who), Usage(input_tokens=10_000)  # 1회 $0.04

    llm = ScriptedLLM(script, budget=0.05)
    res = go(t, llm, ws_dir, tmp_path)
    assert res.stopped and "예산" in res.stopped
    assert llm.ledger.total_usd <= 0.05 + 0.04 + 1e-9  # 넘어도 호출 1번만큼만
    assert len(llm.calls) == 2
    saved = sorted((res.run_dir / "agents").glob("*.md"))
    assert any("중단됨" in f.read_text(encoding="utf-8") for f in saved)  # 멈춘 에이전트도 기록이 남음


def test_review_format_error_fails_open(ws_dir, tmp_path):
    def script(who, messages, tools, schema, none):
        return text("판정 대신 아무 글") if schema is ReviewVerdict else text(f"{who} 글")

    res = go(review_team(), ScriptedLLM(script), ws_dir, tmp_path)
    assert res.stopped is None and res.review_passed is None and res.final_text == "writer 글"
    assert "판정을 내지 못해" in (res.run_dir / "result.md").read_text(encoding="utf-8")


def test_stop_keeps_review_progress(ws_dir, tmp_path):
    def script(who, messages, tools, schema, none):
        if schema is ReviewVerdict:
            return text(ReviewVerdict(passed=False, issues=["x"], summary="no").model_dump_json()), Usage()
        if who == "writer" and "검토자가 고치라고" in first_user(messages):
            return text("다시 씀"), Usage(input_tokens=100_000)
        return text(f"{who}"), Usage()

    t = review_team(rounds=3)
    t.budget_usd = 0.1
    llm = ScriptedLLM(script, budget=0.1)
    llm.ledger.record("x", "sonnet", "claude-sonnet-5-5", Usage(input_tokens=40_000), "end_turn")  # 이미 $0.08 씀
    res = go(t, llm, ws_dir, tmp_path)
    assert res.stopped and res.review_rounds == 1  # 1회차 검토 → 다시 쓰기 → 2회차 전에 예산 초과
    assert "미통과 (1회)" in (res.run_dir / "summary.md").read_text(encoding="utf-8")
