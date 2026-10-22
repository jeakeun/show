"""에이전트가 쓸 수 있는 도구 목록.

원칙
- 도구는 코드에 정해 둔 것만 쓴다. 설계 에이전트는 이 목록에서 고를 수만 있고 새 도구를 만들 수 없다.
- 도구마다 위험도를 붙인다: read(읽기) / write(되돌릴 수 있는 쓰기) / external(밖으로 나가는 되돌릴 수 없는 행동).
  external 도구는 실행 직전에 사람에게 묻는다 (지금 목록에는 없음. 새로 추가할 때 이 칸으로).
- 읽기는 지정한 작업 폴더 안에서만, 비밀 파일은 이름만 봐도 막는다.
- 쓰기는 이번 실행 폴더 안에만, 같은 이름이 있으면 덮어쓰지 않고 새 이름으로 저장한다.
"""
from __future__ import annotations

import ast
import fnmatch
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional

Risk = Literal["read", "write", "external"]

# 경로 중 하나라도 이 이름이면 통째로 막는 폴더
BLOCKED_DIRS = {"secrets", ".git", ".venv", "venv", "node_modules", "__pycache__", ".ssh"}
# 파일 이름이 이 패턴이면 막는다 (대소문자 무시)
BLOCKED_FILES = [
    ".env", ".env.*", "*.env", "*token*", "*secret*", "*password*", "*credential*",
    "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "topic.txt", "*.kdbx",
]

MAX_READ_CHARS = 60_000
MAX_LIST = 300
MAX_HITS = 100


class ToolError(Exception):
    pass


@dataclass
class Workspace:
    """read_root: 에이전트가 읽을 수 있는 폴더. out_dir: 이번 실행에서 쓸 수 있는 폴더."""

    read_root: Path
    out_dir: Path

    def __post_init__(self):
        self.read_root = Path(self.read_root).resolve()
        self.out_dir = Path(self.out_dir).resolve()

    def resolve_read(self, rel: str) -> Path:
        rel = (rel or ".").strip()
        p = (self.read_root / rel).resolve()
        if p != self.read_root and self.read_root not in p.parents:
            raise ToolError(f"작업 폴더 밖은 읽을 수 없습니다: {rel}")
        if is_blocked(p.relative_to(self.read_root)):
            raise ToolError(f"비밀 파일로 보이는 경로라 막았습니다: {rel}")
        return p

    def rel(self, p: Path) -> str:
        return p.relative_to(self.read_root).as_posix() or "."


def is_blocked(rel_path: Path) -> bool:
    parts = [x.lower() for x in rel_path.parts]
    if any(x in BLOCKED_DIRS for x in parts):
        return True
    name = rel_path.name.lower()
    return any(fnmatch.fnmatch(name, pat) for pat in BLOCKED_FILES)


def _read_text(p: Path) -> str:
    data = p.read_bytes()
    if b"\x00" in data[:4096]:
        raise ToolError("글자 파일이 아닙니다 (이미지·영상 같은 이진 파일)")
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _walk(ws: Workspace, base: Path, pattern: str):
    """막힌 폴더는 들어가지 않고, 막힌 파일은 건너뛰며 파일을 돌려준다."""
    stack = [base]
    while stack:
        d = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for e in entries:
            relp = e.relative_to(ws.read_root)
            if is_blocked(relp) or e.name.startswith("."):
                continue
            if e.is_dir():
                stack.append(e)
            elif fnmatch.fnmatch(e.name.lower(), (pattern or "*").lower()):
                yield e


# ---------------------------------------------------------------- 도구 구현

def list_files(ws: Workspace, args: dict) -> str:
    base = ws.resolve_read(args.get("path", "."))
    if not base.is_dir():
        raise ToolError(f"폴더가 아닙니다: {args.get('path')}")
    rows = []
    for f in _walk(ws, base, args.get("pattern", "*")):
        rows.append(f"{ws.rel(f)}  ({f.stat().st_size:,} bytes)")
        if len(rows) >= MAX_LIST:
            rows.append(f"... (최대 {MAX_LIST}개까지만 표시)")
            break
    return "\n".join(rows) if rows else "(파일 없음)"


def read_file(ws: Workspace, args: dict) -> str:
    p = ws.resolve_read(args.get("path", ""))
    if not p.is_file():
        raise ToolError(f"파일이 없습니다: {args.get('path')}")
    text = _read_text(p)
    lines = text.splitlines()
    start = max(1, int(args.get("start_line", 1) or 1))
    max_lines = max(1, min(int(args.get("max_lines", 400) or 400), 2000))
    chunk = lines[start - 1 : start - 1 + max_lines]
    out = "\n".join(f"{start + i}: {ln}" for i, ln in enumerate(chunk))
    if len(out) > MAX_READ_CHARS:
        out = out[:MAX_READ_CHARS] + "\n... (글자 수 한도로 잘림)"
    end = start - 1 + len(chunk)
    if end < len(lines):
        out += f"\n... (전체 {len(lines)}줄 중 {start}~{end}줄. 이어 읽으려면 start_line={end + 1})"
    return out or "(빈 파일)"


def search_files(ws: Workspace, args: dict) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        raise ToolError("query 가 비었습니다")
    base = ws.resolve_read(args.get("path", "."))
    q = query.lower()
    hits = []
    for f in _walk(ws, base, args.get("pattern", "*")):
        try:
            text = _read_text(f)
        except (ToolError, OSError):
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            if q in ln.lower():
                hits.append(f"{ws.rel(f)}:{i}: {ln.strip()[:300]}")
                if len(hits) >= MAX_HITS:
                    return "\n".join(hits) + f"\n... (최대 {MAX_HITS}건까지만 표시)"
    return "\n".join(hits) if hits else f"('{query}' 를 찾지 못함)"


_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"round": round, "abs": abs, "min": min, "max": max, "sum": lambda *a: sum(a)}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ToolError("거듭제곱 숫자가 너무 큽니다")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ToolError("숫자와 + - * / // % ** ( ) 와 round abs min max sum 만 쓸 수 있습니다. "
                    "천 단위 쉼표 없이 쓰세요 (1,000 → 1000)")


def calculate(ws: Workspace, args: dict) -> str:
    expr = str(args.get("expression", "")).strip()  # 쉼표를 지우지 않는다: max(100,200) 이 100200 이 되면 안 됨
    if len(expr) > 500:
        raise ToolError("식이 너무 깁니다")
    try:
        tree = ast.parse(expr, mode="eval")
        value = _eval(tree)
    except ZeroDivisionError:
        raise ToolError("0으로 나눌 수 없습니다") from None
    except SyntaxError:
        raise ToolError(f"식을 이해하지 못했습니다: {expr}") from None
    if isinstance(value, float):
        value = round(value, 6)
    return f"{expr} = {value}"


SAVE_EXTS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html"}


def save_file(ws: Workspace, args: dict) -> str:
    name = str(args.get("filename", "")).strip()
    if not name or "/" in name or "\\" in name or name.startswith(".") or ":" in name:
        raise ToolError("filename 은 폴더 없이 파일 이름만 씁니다. 예: report.md")
    if Path(name).suffix.lower() not in SAVE_EXTS:
        raise ToolError(f"저장할 수 있는 확장자: {', '.join(sorted(SAVE_EXTS))}")
    content = str(args.get("content", ""))
    files = ws.out_dir / "files"
    files.mkdir(parents=True, exist_ok=True)
    target = files / name
    n = 2
    while target.exists():  # 덮어쓰지 않는다 = 되돌릴 수 있는 쓰기
        target = files / f"{Path(name).stem}-{n}{Path(name).suffix}"
        n += 1
    target.write_text(content, encoding="utf-8")
    return f"저장함: files/{target.name} ({len(content):,}자)"


# ---------------------------------------------------------------- 도구 목록

@dataclass
class Tool:
    name: str
    risk: Risk
    summary: str  # 설계 에이전트·사람이 보는 한 줄 설명
    description: str = ""  # 모델이 읽는 사용설명서
    input_schema: Optional[dict] = None
    fn: Optional[Callable[[Workspace, dict], str]] = None
    server_def: Optional[dict] = None  # 앤트로픽 서버에서 도는 도구면 그 정의
    models: Optional[set] = None  # 쓸 수 있는 모델 (None = 전부)
    note: str = ""

    def api_def(self) -> dict:
        if self.server_def:
            return dict(self.server_def)
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


TOOLS: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    TOOLS[tool.name] = tool
    return tool


register(Tool(
    name="list_files", risk="read",
    summary="작업 폴더의 파일 목록 보기",
    description="작업 폴더 안의 파일 목록을 크기와 함께 돌려준다. 읽기 전용. 비밀 파일은 목록에 나오지 않는다.",
    input_schema=_obj({
        "path": {"type": "string", "description": "작업 폴더 기준 하위 폴더. 기본 '.'"},
        "pattern": {"type": "string", "description": "파일 이름 패턴. 예: *.md  기본 *"},
    }, []),
    fn=list_files,
))
register(Tool(
    name="read_file", risk="read",
    summary="작업 폴더의 글자 파일 읽기 (줄 번호 포함)",
    description="작업 폴더 안의 글자 파일을 줄 번호와 함께 읽는다. 읽기 전용. 긴 파일은 start_line 으로 이어 읽는다.",
    input_schema=_obj({
        "path": {"type": "string", "description": "작업 폴더 기준 파일 경로"},
        "start_line": {"type": "integer", "description": "시작 줄 (기본 1)"},
        "max_lines": {"type": "integer", "description": "읽을 줄 수 (기본 400, 최대 2000)"},
    }, ["path"]),
    fn=read_file,
))
register(Tool(
    name="search_files", risk="read",
    summary="작업 폴더에서 낱말 찾기",
    description="작업 폴더 안 글자 파일에서 낱말을 찾아 '파일:줄: 내용'으로 돌려준다. 대소문자 무시. 읽기 전용.",
    input_schema=_obj({
        "query": {"type": "string", "description": "찾을 낱말"},
        "path": {"type": "string", "description": "찾을 하위 폴더. 기본 '.'"},
        "pattern": {"type": "string", "description": "파일 이름 패턴. 예: *.md"},
    }, ["query"]),
    fn=search_files,
))
register(Tool(
    name="calculate", risk="read",
    summary="계산기 (숫자는 AI가 머리로 세지 않고 코드가 계산)",
    description="사칙연산 식을 정확히 계산한다. 합계·비율·증감률 같은 숫자는 반드시 이 도구로 계산한다. "
                "천 단위 쉼표 없이 쓴다. 예: (13420-11200)/11200*100",
    input_schema=_obj({"expression": {"type": "string", "description": "계산할 식"}}, ["expression"]),
    fn=calculate,
))
register(Tool(
    name="save_file", risk="write",
    summary="결과 파일 저장 (이번 실행 폴더에만, 덮어쓰기 없음)",
    description="이번 실행 결과 폴더에 파일을 저장한다. 같은 이름이 있으면 새 이름으로 저장하고 덮어쓰지 않는다. "
                "확장자는 .md .txt .csv .json .yaml .html 만.",
    input_schema=_obj({
        "filename": {"type": "string", "description": "파일 이름만. 예: report.md"},
        "content": {"type": "string", "description": "파일 내용"},
    }, ["filename", "content"]),
    fn=save_file,
))
register(Tool(
    name="web_search", risk="read",
    summary="웹 검색 (앤트로픽 서버에서 실행, 1회 약 $0.01, 에이전트당 최대 5회)",
    server_def={"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
    models={"opus", "sonnet"},
    note="haiku 에서는 못 씀",
))


def catalog_text() -> str:
    """설계 에이전트에게 보여줄 도구 목록."""
    risk_ko = {"read": "읽기", "write": "쓰기(되돌릴 수 있음)", "external": "외부 행동(되돌릴 수 없음, 실행 전 사람 확인)"}
    lines = []
    for t in TOOLS.values():
        extra = f", {t.note}" if t.note else ""
        lines.append(f"- {t.name} [{risk_ko[t.risk]}{extra}]: {t.summary}")
    return "\n".join(lines)


def run_tool(name: str, args: dict, ws: Workspace) -> str:
    tool = TOOLS.get(name)
    if tool is None or tool.fn is None:
        raise ToolError(f"없는 도구입니다: {name}")
    if not isinstance(args, dict):
        raise ToolError("도구 입력 형식이 잘못됐습니다")
    return tool.fn(ws, args)


@dataclass
class ToolPolicy:
    """에이전트 1명이 쓸 수 있는 도구와, 되돌릴 수 없는 행동 앞의 사람 확인."""

    allowed: list[str]
    approver: Optional[Callable[[str, str, dict], bool]] = None  # (에이전트, 도구, 입력) -> 허락?

    def execute(self, agent: str, name: str, args: dict, ws: Workspace) -> tuple[str, bool]:
        """(결과 글, 오류 여부)"""
        if name not in self.allowed:
            return f"오류: '{name}' 은(는) 이 에이전트에게 허용되지 않은 도구입니다.", True
        tool = TOOLS[name]
        if tool.risk == "external":
            ok = bool(self.approver and self.approver(agent, name, args))
            if not ok:
                return "사람이 이 행동을 허락하지 않았습니다. 이 행동 없이 계속하세요.", True
        try:
            return run_tool(name, args, ws), False
        except ToolError as e:
            return f"오류: {e}", True
        except Exception as e:  # 도구 버그가 루프 전체를 멈추지 않게
            return f"오류: 도구 실행 중 문제 ({type(e).__name__}: {e})", True
