from conftest import agent, team

from agent_factory import rules
from agent_factory.spec import ReviewSpec

READ = ["list_files", "read_file"]


def codes(t):
    return sorted({f.code for f in rules.check(t)})


def good_parallel():
    return team(
        [agent("scout_a", READ, model="haiku"), agent("scout_b", READ, model="haiku"),
         agent("writer", ["calculate", "save_file"]), agent("checker", ["read_file"])],
        [["scout_a", "scout_b"], ["writer"]],
        review=ReviewSpec(reviewer="checker", criteria=["출처가 있다"], max_rounds=2),
    )


def test_good_team_passes():
    assert rules.check(good_parallel()) == []


def test_single_agent_needs_no_reasons():
    t = team([agent("solo", READ, why_separate="")], [["solo"]], why_not_single="")
    assert rules.check(t) == []


def test_r01_names():
    t = good_parallel()
    t.name = "Bad Name"
    t.agents[0].name = "Scout-A"
    t.stages[0].agents[0] = "Scout-A"
    assert "R01" in codes(t)
    dup = team([agent("a1", READ), agent("a1", READ)], [["a1"]])
    assert "R01" in codes(dup)


def test_r02_unknown_tool_model_and_tool_model_limit():
    t = team([agent("solo", ["read_file", "delete_everything"])], [["solo"]])
    assert codes(t) == ["R02"]
    t = team([agent("solo", ["web_search"], model="haiku")], [["solo"]])
    assert codes(t) == ["R02"]
    t = team([agent("solo", ["web_search"], model="sonnet")], [["solo"]])
    assert codes(t) == []


def test_r03_size_limits():
    many = [agent(f"a{i}", READ) for i in range(7)]
    t = team(many, [[f"a{i}" for i in range(6)], ["a6"]])
    assert "R03" in codes(t)


def test_r04_unused_missing_and_double_use():
    t = team([agent("a1", READ), agent("a2", READ)], [["a1"]])
    assert "R04" in codes(t)  # a2 안 씀
    t = team([agent("a1", READ)], [["a1"], ["ghost"]])
    assert "R04" in codes(t)  # 없는 에이전트
    t = team([agent("ww", READ), agent("rr", READ)], [["ww"], ["rr"]],
             review=ReviewSpec(reviewer="rr", criteria=["x"], max_rounds=1))
    assert "R04" in codes(t)  # 검토자가 단계에도 있음


def test_r05_reasons_required_for_multi():
    t = good_parallel()
    t.why_not_single = ""
    t.agents[1].why_separate = "짧음"
    found = [f for f in rules.check(t) if f.code == "R05"]
    assert len(found) == 2


def test_r06_parallel_must_be_read_only():
    t = good_parallel()
    t.agents[0].tools = READ + ["save_file"]
    assert "R06" in codes(t)


def test_r07_single_writer_in_last_stage():
    t = team([agent("w1", ["save_file"]), agent("w2", ["save_file"])], [["w1"], ["w2"]])
    c = codes(t)
    assert "R07" in c
    msgs = [f.message for f in rules.check(t) if f.code == "R07"]
    assert any("2명" in m for m in msgs) and any("마지막 단계가 아닙니다" in m for m in msgs)


def test_r08_last_stage_single():
    t = team([agent("aa", READ), agent("bb", READ)], [["aa", "bb"]])
    assert codes(t) == ["R08"]


def test_r09_reviewer_rules():
    t = good_parallel()
    t.agents[3].tools = ["save_file"]
    assert "R09" in codes(t)
    t = good_parallel()
    t.review.criteria = ["  "]
    t.review.max_rounds = 0
    assert [f.code for f in rules.check(t)].count("R09") == 2


def test_r10_r11_limits():
    t = team([agent("solo", READ, max_turns=0)], [["solo"]], budget_usd=0)
    assert codes(t) == ["R10", "R11"]
    t = team([agent("solo", READ, max_turns=13)], [["solo"]], budget_usd=5)
    assert codes(t) == ["R10", "R11"]


def test_rules_text_lists_every_rule():
    text = rules.rules_text()
    for r in rules.RULES:
        assert r.code in text


def test_warnings():
    t = team([agent(f"a{i}", READ, model="opus") for i in range(3)] + [agent("w", ["web_search"])],
             [["a0", "a1", "a2"], ["w"]])
    w = rules.warnings(t)
    assert len(w) == 4 and any("calculate" in x for x in w)


def test_example_teams_pass():
    from pathlib import Path

    from agent_factory.spec import load_team

    files = sorted((Path(__file__).resolve().parent.parent / "teams").glob("*.yaml"))
    assert files, "예제 팀이 있어야 함"
    for f in files:
        assert rules.check(load_team(f)) == [], f.name


def test_r12_web_and_workspace_split():
    t = team([agent("solo", ["web_search", "read_file"])], [["solo"]])
    assert codes(t) == ["R12"]
    t = team([agent("web", ["web_search"]), agent("files", READ), agent("ww", ["calculate"])],
             [["web", "files"], ["ww"]])
    assert codes(t) == []


def test_r09_reviewer_cannot_web_search():
    t = good_parallel()
    t.agents[3].tools = ["web_search"]
    assert "R09" in codes(t)


def test_empty_team_does_not_crash():
    from agent_factory.spec import TeamSpec

    assert "R03" in codes(TeamSpec(name="empty-team", situation="x", agents=[], stages=[]))


def test_all_problems_reported_at_once():
    t = team([agent("aa", READ, why_separate=""), agent("bb", READ)], [["aa"], ["ghost"], ["bb"]],
             why_not_single="")
    assert {"R04", "R05"} <= set(codes(t))  # 이름 문제가 있어도 나머지 규칙도 한 번에 알려줌


def test_spec_typo_and_cp949(tmp_path):
    import pytest

    from agent_factory.spec import SpecError, load_team

    bad = tmp_path / "typo.yaml"
    bad.write_text("name: x-team\nsituation: s\nagents:\n- name: solo\n  role: r\n  model: haiku\n"
                   "  instructions: i\n  tool: [read_file]\nstages:\n- agents: [solo]\n", encoding="utf-8")
    with pytest.raises(SpecError, match="tool"):
        load_team(bad)
    ok = tmp_path / "cp949.yaml"
    ok.write_bytes("name: x-team\nsituation: 한글 상황\nagents:\n- name: solo\n  role: 역할\n  model: haiku\n"
                   "  instructions: 지시\nstages:\n- agents: [solo]\n".encode("cp949"))
    assert load_team(ok).situation == "한글 상황"
