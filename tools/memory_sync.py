# -*- coding: utf-8 -*-
"""클로드 메모리 → show 공개 저장소 docs/claude-memory 사본 자동 동기화 (매일 밤 예약 실행).

안전 원칙 (2026-11-21 Codex 검토 반영):
- **허용 목록에 있는 파일만** 공개한다. 새 메모리 파일은 기본 보류 → 알림 → 사용자 승인 후
  ~/.claude/memory_sync_allow.txt 에 이름을 넣어야 올라간다.
- MEMORY.md 목차에서도 공개하지 않는 파일 줄은 지운다.
- 이름·주소 가림 규칙은 이 PC에만 있는 ~/.claude/memory_sync_redact.tsv. 없거나 형식이 틀리면 중단.
- 비밀값 의심 문자열이 있으면 아무것도 쓰지 않고 중단.
- --dry 는 파일·깃을 전혀 건드리지 않는다. 푸시가 거절되면 자동 rebase 하지 않고 멈춘다.
실행: python tools/memory_sync.py [--dry]
"""
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home() / ".claude"
SRC = HOME / "projects" / "C--Users-User-OneDrive-Desktop-show" / "memory"
DST = REPO / "docs" / "claude-memory"
LOG = REPO / "tools" / "memory_sync.log"
ALLOW_FILE = HOME / "memory_sync_allow.txt"     # 공개 허용 파일 이름 (한 줄에 하나)
REDACT_FILE = HOME / "memory_sync_redact.tsv"   # 정규식<TAB>바꿀 말
NOTE = "\n\n> 공개 저장소 사본: 허용 목록에 있는 메모리만 올림(계정·지원 기록·점검 결과 등은 메인 PC에만). 노션 주소·회사 정보는 가림.\n"
NOTION = re.compile(r"\S*notion\.(so|site|com)/\S*")
DANGER = [
    re.compile(r"sk-(ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]{30,}"),
    re.compile(r"xox[abpr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]{20,}"),                   # 구글 OAuth 토큰
    re.compile(r"\b\d{6}-[1-4]\d{6}\b"),                        # 주민등록번호 형태
    re.compile(r"\b01[016789]-?(?!1234-?5678)\d{3,4}-?\d{4}\b"),  # 휴대폰(예시 번호 제외)
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),                     # 이메일 전부
    re.compile(r"(?i)(password|passwd|비밀번호)\s*[:=]\s*\S{4,}"),
]
GIT_TIMEOUT = 120


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M} {msg}"
    try:
        print(line)
    except Exception:  # 창 없이(pythonw) 실행하면 출력 창이 없음
        pass
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def alert(msg):
    try:
        sys.path.insert(0, r"D:\notify")
        from push import push
        push("Memory sync", msg)
    except Exception as e:
        log(f"알림 실패: {type(e).__name__}")


class Stop(Exception):
    pass


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                       timeout=GIT_TIMEOUT, env={**__import__("os").environ, "GIT_TERMINAL_PROMPT": "0"})
    if r.returncode:
        raise Stop(f"git {args[0]} 실패: {r.stderr.strip()[:200]}")
    return r.stdout


def load_rules():
    if not REDACT_FILE.exists():
        raise Stop("가림 목록 파일 없음")
    rules = []
    for i, line in enumerate(REDACT_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            raise Stop(f"가림 목록 {i}번째 줄 형식 오류(탭 없음)")
        pat, rep = line.split("\t", 1)
        rules.append((re.compile(pat), rep))
    if not rules:
        raise Stop("가림 목록이 비어 있음")
    allow = {x.strip() for x in ALLOW_FILE.read_text(encoding="utf-8").splitlines()
             if x.strip() and not x.startswith("#")} if ALLOW_FILE.exists() else set()
    if "MEMORY.md" not in allow:
        raise Stop("허용 목록 파일이 없거나 MEMORY.md 가 빠짐")
    return rules, allow


def build():
    rules, allow = load_rules()
    names = {f.name for f in SRC.glob("*.md")}
    if "MEMORY.md" not in names:
        raise Stop("메모리 폴더를 못 찾음")
    held = sorted(names - allow)
    out = {}
    for name in sorted(names & allow):
        t = (SRC / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if name == "MEMORY.md":  # 공개 안 하는 파일을 가리키는 목차 줄 삭제
            t = "\n".join(l for l in t.split("\n")
                          if not any(f"({h})" in l for h in names - allow)).rstrip("\n") + NOTE
        t = NOTION.sub("(노션 주소 비공개)", t)
        for pat, rep in rules:
            t = pat.sub(rep, t)
        out[name] = t
    return out, held


def main(dry=False):
    files, held = build()
    hits = sorted({f"{n}#{i}" for n, t in files.items() for i, p in enumerate(DANGER) if p.search(t)})
    if hits:
        raise Stop(f"비밀값·개인정보 의심 {len(hits)}건: {', '.join(hits)[:200]}")
    current = {p.name: p.read_bytes().decode("utf-8") for p in DST.glob("*")} if DST.exists() else {}
    changed = [n for n, t in files.items() if current.get(n) != t]
    removed = [n for n in current if n not in files]
    if held:
        log(f"공개 보류(허용 목록에 없음) {len(held)}개: {', '.join(held)}")
    if dry:
        log(f"(시험) 바뀔 파일 {len(changed)}개, 지울 파일 {len(removed)}개: {', '.join(changed + removed)}")
        return 0
    if not changed and not removed:
        log("바뀐 것 없음")
        if held:
            alert(f"새 메모리 {len(held)}개가 공개 보류 중. 클로드에게 '메모리 공개 보류 확인'이라고 말하세요.")
        return 0
    for n in changed:
        (DST / n).write_bytes(files[n].encode("utf-8"))
    for n in removed:
        (DST / n).unlink()
    paths = [f"docs/claude-memory/{n}" for n in changed + removed]
    git("add", "-A", "--", *paths)
    staged = git("diff", "--cached", "--name-only").split()
    extra = [s for s in staged if s not in paths]
    if extra:  # 다른 작업이 미리 올려둔(staged) 파일이 섞이면 중단
        git("reset", "-q", "--", *paths)
        raise Stop(f"다른 staged 파일 {len(extra)}개가 있어 커밋 안 함")
    git("commit", "-q", "-m",
        f"Memory sync {datetime.now():%Y-%m-%d} (auto, allowlisted files only, redacted)", "--", *paths)
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != "main":
        raise Stop(f"main 이 아닌 {branch} 브랜치라 푸시 안 함(커밋은 됨)")
    git("push", "-q", "origin", "main")
    log(f"올림: {len(changed)}개 변경, {len(removed)}개 삭제")
    if held:
        alert(f"메모리 동기화 완료. 새 메모리 {len(held)}개는 공개 보류 중.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(dry="--dry" in sys.argv))
    except Stop as e:
        log("중단: " + str(e))
        alert("메모리 동기화 중단: " + str(e)[:150])
        sys.exit(1)
    except Exception as e:
        log("오류: " + "".join(traceback.format_exception_only(type(e), e)).strip()[:300])
        alert(f"메모리 동기화 오류: {type(e).__name__}")
        sys.exit(1)
