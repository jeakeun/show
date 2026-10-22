import pytest
from conftest import ScriptedLLM, agent, team, text

from agent_factory import cli
from agent_factory.designer import Critique, DesignError, design_team
from agent_factory.spec import TeamSpec

READ = ["list_files", "read_file"]


def bad_team():  # 병렬 단계에 쓰기 도구 → R06·R07 위반
    return team([agent("scout_a", READ + ["save_file"]), agent("scout_b", READ), agent("writer", ["save_file"])],
                [["scout_a", "scout_b"], ["writer"]])


def good_team():
    return team([agent("scout_a", READ), agent("scout_b", READ), agent("writer", ["save_file"])],
                [["scout_a", "scout_b"], ["writer"]])


def single_team():
    return team([agent("solo", READ, why_separate="")], [["solo"]], why_not_single="", name="solo-team")


def designer_script(designs, critiques=()):
    designs, critiques = iter(designs), iter(critiques)

    def script(who, messages, tools, schema, none):
        if schema is TeamSpec:
            return text(next(designs).model_dump_json())
        if schema is Critique:
            return text(next(critiques).model_dump_json())
        raise AssertionError(who)

    return script


OK = Critique(verdict="ok", problems=[], notes=["괜찮음"], simpler_alternative="")
REVISE = Critique(verdict="revise", problems=["1명으로 충분"], notes=[], simpler_alternative="1명 팀")


def test_rule_violation_goes_back_to_designer():
    llm = ScriptedLLM(designer_script([bad_team(), good_team()], [OK]))
    d = design_team(llm, "상황 원문")
    assert d.team.stages[0].agents == ["scout_a", "scout_b"] and d.team.situation == "상황 원문"
    assert "R06" in d.log[0] and "통과" in d.log[1]
    fix_msg = llm.calls[1]["messages"][-1]["content"]
    assert "R06" in fix_msg and llm.calls[1]["messages"][1]["role"] == "assistant"
    assert d.critique.verdict == "ok" and not d.critique_applied


def test_gives_up_after_max_fixes():
    llm = ScriptedLLM(designer_script([bad_team()] * 3))
    with pytest.raises(DesignError) as e:
        design_team(llm, "x", max_fixes=2)
    assert {f.code for f in e.value.findings} >= {"R06"}
    assert len(llm.calls) == 3


def test_critic_revision_applied():
    llm = ScriptedLLM(designer_script([good_team(), single_team()], [REVISE]))
    d = design_team(llm, "x")
    assert d.critique_applied and len(d.team.agents) == 1
    assert "1명으로 충분" in llm.calls[2]["messages"][-1]["content"]
    critic_call = llm.calls[1]
    assert len(critic_call["messages"]) == 1  # 검토자는 설계자의 대화를 모른다


def test_critic_revision_that_breaks_rules_keeps_previous():
    llm = ScriptedLLM(designer_script([good_team(), bad_team(), bad_team(), bad_team()], [REVISE]))
    d = design_team(llm, "x", max_fixes=2)
    assert not d.critique_applied and len(d.team.agents) == 3
    assert any("앞 설계" in x for x in d.log)


def test_designer_prompt_contains_rules_and_catalogs():
    llm = ScriptedLLM(designer_script([single_team()]))
    design_team(llm, "x", use_critic=False, listing="a.md (10 bytes)")
    sys_prompt = llm.calls[0]["system"]
    for s in ("R01", "R11", "read_file", "haiku", "직함"):
        assert s in sys_prompt
    assert "a.md" in llm.calls[0]["messages"][0]["content"]


def test_cli_demo_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "TEAMS_DIR", tmp_path / "teams")
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path / "runs")
    rc = cli.main(["design", "세 리포트를 모두 비교해줘", "--demo", "--yes", "--workspace", str(cli.SAMPLE_WS)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "규칙 위반" in out and "규칙 검사: 통과" in out and "결과 파일" in out
    assert not list((tmp_path / "teams").glob("*.yaml"))  # 설계 결과는 깃 제외 폴더(teams/local)에만
    saved = list((tmp_path / "teams" / "local").glob("*.yaml"))
    assert len(saved) == 1
    assert cli.main(["check", str(saved[0])]) == 0
    rc = cli.main(["run", str(saved[0]), "--demo", "--yes", "--task", "다른 작업", "--workspace", str(cli.SAMPLE_WS)])
    assert rc == 0
    results = list((tmp_path / "runs").glob("*/result.md"))
    assert len(results) == 2


def test_cli_run_refuses_invalid_team(tmp_path, capsys):
    from agent_factory.spec import save_team

    p = save_team(bad_team(), tmp_path / "bad.yaml")
    assert cli.main(["run", str(p), "--demo", "--yes"]) == 1
    assert "위반" in capsys.readouterr().out


def test_critic_failure_keeps_paid_design():
    def script(who, messages, tools, schema, none):
        return text(good_team().model_dump_json()) if schema is TeamSpec else text("판정 아님")

    d = design_team(ScriptedLLM(script), "x")
    assert d.critique is None and len(d.team.agents) == 3
    assert any("검토 에이전트 실패" in x for x in d.log)


def test_designer_truncated_output_message():
    from agent_factory.llm import Reply

    llm = ScriptedLLM(lambda *a: Reply(content=[], stop_reason="max_tokens", text="{"))
    with pytest.raises(DesignError, match="출력 한도"):
        design_team(llm, "x")


def test_cli_records_workspace_and_lists_empty_situation(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "TEAMS_DIR", tmp_path / "teams")
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path / "runs")
    ws = tmp_path / "data"
    ws.mkdir()
    (ws / "note.md").write_text("메모", encoding="utf-8")
    assert cli.main(["design", "요약해줘", "--demo", "--no-run", "--workspace", str(ws)]) == 0
    from agent_factory.spec import load_team, save_team

    saved = next((tmp_path / "teams" / "local").glob("*.yaml"))
    assert load_team(saved).workspace == str(ws.resolve())
    t = load_team(saved)
    t.situation = ""
    save_team(t, tmp_path / "teams" / "local" / "blank.yaml")
    assert cli.main(["list"]) == 0
    assert "blank" in capsys.readouterr().out
