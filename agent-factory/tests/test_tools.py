import pytest

from agent_factory import tools as T
from agent_factory.tools import ToolPolicy, Workspace


@pytest.fixture
def ws(ws_dir, tmp_path):
    return Workspace(ws_dir, tmp_path / "out")


def test_list_hides_secrets(ws):
    out = T.list_files(ws, {})
    assert "a.md" in out and "sub/b.txt" in out
    assert ".env" not in out and "secrets" not in out and "token" not in out


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/passwd", ".env", "secrets/key.txt", "my_token.json"])
def test_read_blocked(ws, path):
    with pytest.raises(T.ToolError):
        T.read_file(ws, {"path": path})


def test_read_with_line_numbers_and_continuation(ws):
    out = T.read_file(ws, {"path": "a.md", "max_lines": 2})
    assert out.startswith("1: 첫째 줄\n2: 조회수 100")
    assert "start_line=3" in out


def test_read_cp949(ws, ws_dir):
    (ws_dir / "old.txt").write_bytes("한글 파일".encode("cp949"))
    assert "한글 파일" in T.read_file(ws, {"path": "old.txt"})


def test_read_binary_rejected(ws, ws_dir):
    (ws_dir / "img.png").write_bytes(b"\x89PNG\x00\x00\x00")
    with pytest.raises(T.ToolError):
        T.read_file(ws, {"path": "img.png"})


def test_search(ws):
    out = T.search_files(ws, {"query": "조회수"})
    assert "a.md:2:" in out and "sub/b.txt:1:" in out
    assert "secret" not in out


def test_calculate():
    assert T.calculate(None, {"expression": "(13420-11200)/11200*100"}).endswith("= 19.821429")
    assert T.calculate(None, {"expression": "1000 + round(2.5)"}).endswith("= 1002")
    assert T.calculate(None, {"expression": "max(100,200) + min(1, 2)"}).endswith("= 201")


@pytest.mark.parametrize("expr", ["__import__('os').system('ls')", "a+1", "(1).real", "9**999999", "1/0", "", "1,000 + 5"])
def test_calculate_rejects(expr):
    with pytest.raises(T.ToolError):
        T.calculate(None, {"expression": expr})


def test_save_never_overwrites(ws):
    assert "files/r.md" in T.save_file(ws, {"filename": "r.md", "content": "1"})
    assert "files/r-2.md" in T.save_file(ws, {"filename": "r.md", "content": "2"})
    assert (ws.out_dir / "files" / "r.md").read_text(encoding="utf-8") == "1"


@pytest.mark.parametrize("name", ["../x.md", "sub/x.md", "a\\b.md", ".hidden.md", "x.exe", "", "C:x.md"])
def test_save_rejects_bad_names(ws, name):
    with pytest.raises(T.ToolError):
        T.save_file(ws, {"filename": name, "content": "x"})


def test_policy_blocks_unlisted_tool(ws):
    out, err = ToolPolicy(allowed=["read_file"]).execute("a", "save_file", {"filename": "x.md", "content": ""}, ws)
    assert err and "허용되지 않은" in out


def test_policy_tool_bug_becomes_error_result(ws):
    out, err = ToolPolicy(allowed=["read_file"]).execute("a", "read_file", {"path": "a.md", "max_lines": "많이"}, ws)
    assert err and "오류" in out


def test_external_tool_needs_human(ws):
    sent = []
    T.register(T.Tool(name="send_test", risk="external", summary="테스트용 외부 행동",
                      input_schema={"type": "object", "properties": {}}, fn=lambda w, a: sent.append(1) or "보냄"))
    try:
        out, err = ToolPolicy(allowed=["send_test"]).execute("a", "send_test", {}, ws)
        assert err and not sent  # 확인 장치 없으면 막힘
        out, err = ToolPolicy(allowed=["send_test"], approver=lambda *a: False).execute("a", "send_test", {}, ws)
        assert err and not sent
        out, err = ToolPolicy(allowed=["send_test"], approver=lambda *a: True).execute("a", "send_test", {}, ws)
        assert not err and sent == [1]
    finally:
        T.TOOLS.pop("send_test")
