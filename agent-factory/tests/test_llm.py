"""실제 API 를 부르지 않고, SDK 가 보낼 요청 모양과 응답 해석을 확인한다."""
import json

import anthropic
import httpx2
import pytest

from agent_factory.llm import AnthropicLLM, BudgetExceeded, Ledger, LLMError, Usage, cost_usd
from agent_factory.team import ReviewVerdict
from agent_factory.tools import TOOLS


def test_cost():
    assert cost_usd("opus", "claude-opus-5-5", Usage(input_tokens=1_000_000)) == pytest.approx(4.0)
    assert cost_usd("opus", "claude-opus-5-5", Usage(output_tokens=1_000_000)) == pytest.approx(20.0)
    assert cost_usd("sonnet", "claude-sonnet-5-5", Usage(cache_read=1_000_000)) == pytest.approx(0.20)
    assert cost_usd("sonnet", "claude-sonnet-5-5", Usage(cache_write=1_000_000)) == pytest.approx(2.5)
    assert cost_usd("haiku", "claude-haiku-5-5", Usage(input_tokens=50_000)) == pytest.approx(0.005)
    assert cost_usd("haiku", "claude-haiku-5-5", Usage(input_tokens=200_000)) == pytest.approx(0.1)  # 긴 입력 가격
    assert cost_usd("sonnet", "claude-sonnet-5-5", Usage(web_searches=3)) == pytest.approx(0.03)
    assert cost_usd("opus", "claude-opus-4-8", Usage(input_tokens=1_000_000)) == pytest.approx(5.0)  # 대신 답한 모델


def test_ledger_budget(tmp_path):
    led = Ledger(0.05, tmp_path / "l.jsonl")
    led.ensure_room("a")
    led.record("a", "opus", "claude-opus-5-5", Usage(input_tokens=20_000), "end_turn")
    with pytest.raises(BudgetExceeded):
        led.ensure_room("b")
    assert json.loads((tmp_path / "l.jsonl").read_text(encoding="utf-8"))["usd"] == pytest.approx(0.08)


def fake_client(responses, captured):
    it = iter(responses)

    def handler(req):
        captured.append({"headers": dict(req.headers), "body": json.loads(req.content)})
        status, body = next(it)
        return httpx2.Response(status, json=body)

    return anthropic.Anthropic(api_key="test", max_retries=0,
                               http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))


def msg(content, stop="end_turn", model="claude-opus-5-5", **usage):
    return 200, {"id": "m", "type": "message", "role": "assistant", "model": model, "content": content,
                 "stop_reason": stop, "stop_sequence": None,
                 "usage": {"input_tokens": 100, "output_tokens": 50, **usage}}


def test_request_shape_opus_with_tools():
    cap = []
    llm = AnthropicLLM(Ledger(1), client=fake_client([msg(
        [{"type": "text", "text": "볼게요"}, {"type": "tool_use", "id": "tu1", "name": "read_file", "input": {"path": "a.md"}}],
        stop="tool_use", server_tool_use={"web_search_requests": 2})], cap))
    tools = [TOOLS["read_file"].api_def(), TOOLS["web_search"].api_def()]
    r = llm.chat(who="w", model="opus", system="sys", messages=[{"role": "user", "content": "hi"}],
                 tools=tools, effort="high")
    body, headers = cap[0]["body"], cap[0]["headers"]
    assert body["model"] == "claude-opus-5-5" and body["system"] == "sys"
    assert body["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in headers["anthropic-beta"]
    assert body["output_config"] == {"effort": "high"}
    assert body["cache_control"] == {"type": "ephemeral"}
    assert {t["name"] for t in body["tools"]} == {"read_file", "web_search"}
    assert "temperature" not in body and "thinking" not in body
    assert r.stop_reason == "tool_use" and r.tool_calls[0].name == "read_file" and r.tool_calls[0].input == {"path": "a.md"}
    row = llm.ledger.rows[0]
    assert row["web_searches"] == 2 and row["usd"] == pytest.approx((100 * 4 + 50 * 20) / 1e6 + 0.02)


def test_request_shape_haiku_structured_and_tool_choice_none():
    cap = []
    v = ReviewVerdict(passed=True, issues=[], summary="ok")
    llm = AnthropicLLM(Ledger(1), client=fake_client([msg([{"type": "text", "text": v.model_dump_json()}],
                                                          model="claude-haiku-5-5")], cap))
    r = llm.chat(who="c", model="haiku", system="s", messages=[{"role": "user", "content": "x"}],
                 tools=[TOOLS["read_file"].api_def()], output_schema=ReviewVerdict, tool_choice_none=True)
    body = cap[0]["body"]
    assert "fallbacks" not in body and "anthropic-beta" not in cap[0]["headers"]  # haiku 는 서버 대체 없음
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert body["tool_choice"] == {"type": "none"}
    assert r.parsed == v


def test_structured_garbage_raises():
    llm = AnthropicLLM(Ledger(1), client=fake_client([msg([{"type": "text", "text": "형식 없음"}])], []))
    with pytest.raises(LLMError):
        llm.chat(who="c", model="opus", system="s", messages=[{"role": "user", "content": "x"}],
                 output_schema=ReviewVerdict)


def test_refusal_text():
    body = msg([], stop="refusal")[1]
    body["stop_details"] = {"type": "refusal", "category": "cyber", "explanation": "x"}
    llm = AnthropicLLM(Ledger(1), client=fake_client([(200, body)], []))
    r = llm.chat(who="c", model="opus", system="s", messages=[{"role": "user", "content": "x"}])
    assert r.stop_reason == "refusal" and "거절" in r.text


def test_api_errors_become_korean():
    err = {"type": "error", "error": {"type": "authentication_error", "message": "bad key"}}
    llm = AnthropicLLM(Ledger(1), client=fake_client([(401, err)], []))
    with pytest.raises(LLMError, match="API 키"):
        llm.chat(who="c", model="opus", system="s", messages=[{"role": "user", "content": "x"}])


def test_find_api_key_never_prints_value(monkeypatch, capsys):
    from agent_factory.llm import find_api_key

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
    key, where = find_api_key()
    assert key == "sk-test-123" and "sk-" not in where


def test_fallback_iterations_are_each_billed():
    usage = {"iterations": [
        {"type": "message", "model": "claude-opus-5-5", "input_tokens": 1000, "output_tokens": 500,
         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        {"type": "fallback_message", "model": "claude-opus-4-8", "input_tokens": 1000, "output_tokens": 100,
         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
    ]}
    llm = AnthropicLLM(Ledger(1), client=fake_client([msg([{"type": "text", "text": "ok"}], model="claude-opus-4-8",
                                                          **usage)], []))
    llm.chat(who="w", model="opus", system="s", messages=[{"role": "user", "content": "x"}])
    expected = (1000 * 4 + 500 * 20) / 1e6 + (1000 * 5 + 100 * 25) / 1e6
    assert llm.ledger.rows[0]["usd"] == pytest.approx(expected)


def test_single_shot_call_skips_cache_write():
    cap = []
    llm = AnthropicLLM(Ledger(1), client=fake_client([msg([{"type": "text", "text": "ok"}])], cap))
    llm.chat(who="c", model="opus", system="s", messages=[{"role": "user", "content": "x"}])
    assert "cache_control" not in cap[0]["body"]


def test_find_api_key_file_formats(tmp_path, monkeypatch):
    from agent_factory.llm import find_api_key

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    f = tmp_path / ".env"
    f.write_bytes("# 한글 주석\nexport ANTHROPIC_API_KEY=\"sk-abc\" # 메모\n".encode("cp949"))
    assert find_api_key([f]) == ("sk-abc", str(f))
    g = tmp_path / "g.env"
    g.write_text("ANTHROPIC_API_KEY=sk-plain # note\n", encoding="utf-8")
    assert find_api_key([g])[0] == "sk-plain"
    assert find_api_key([tmp_path / "none"]) == (None, "없음")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "t")
    assert find_api_key([tmp_path / "none"])[1] == "환경변수 ANTHROPIC_AUTH_TOKEN"
