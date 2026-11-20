# -*- coding: utf-8 -*-
"""클로드 메모리 → show 저장소 docs/claude-memory 사본 자동 동기화 (매일 밤 예약 실행).

- 개인 파일 4개(결제·지원 기록 등)는 빼고, 노션 주소는 가린다.
- 비밀값처럼 보이는 문자열이 있으면 올리지 않고 폰 알림만 보낸다.
- 바뀐 게 없으면 아무것도 하지 않는다. docs/claude-memory 외 파일은 커밋하지 않는다.
실행: python tools/memory_sync.py  (--dry 는 복사·검사만 하고 커밋 안 함)
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = Path.home() / ".claude" / "projects" / "C--Users-User-OneDrive-Desktop-show" / "memory"
DST = REPO / "docs" / "claude-memory"
LOG = REPO / "tools" / "memory_sync.log"
SKIP = {"api-billing.md", "job-applications-2026-11.md", "job-search-rules.md", "jocoding-hackathon.md"}
NOTE = ("\n\n> 공개 저장소 사본: api-billing·job-applications-2026-11·job-search-rules·jocoding-hackathon "
        "4개는 계정·지원 기록이 있어 메인 PC에만 둠. 노션 주소는 가림.\n")
NOTION = re.compile(r"https?://([\w.-]*\.)?notion\.(so|site|com)/\S+")
# 비밀값·개인정보로 보이는 것 (발견 시 중단)
DANGER = [
    re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"xox[abpr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\b\d{6}-[1-4]\d{6}\b"),                      # 주민등록번호 형태
    re.compile(r"\b01[016789]-?(?!1234-?5678)\d{3,4}-?\d{4}\b"),  # 휴대폰 번호(예시 번호 제외)
    re.compile(r"[\w.+-]+@(gmail|naver|daum|kakao|hanmail)\.\w+"),
]
NOTIFY = Path(r"D:\notify")


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
        sys.path.insert(0, str(NOTIFY))
        from push import push
        push("Memory sync", msg)
    except Exception:
        pass


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")


def build():
    out = {}
    for f in sorted(SRC.glob("*.md")):
        if f.name in SKIP:
            continue
        t = f.read_bytes().decode("utf-8").replace("\r\n", "\n")
        t = NOTION.sub("(노션 주소 비공개)", t)
        if f.name == "MEMORY.md":
            t = t.rstrip("\n") + NOTE
        out[f.name] = t
    return out


def main(dry=False):
    files = build()
    if "MEMORY.md" not in files:
        log("중단: 메모리 폴더를 못 찾음")
        alert("메모리 폴더를 못 찾아 동기화 중단")
        return 1
    hits = [f"{n}: {p.pattern[:20]}" for n, t in files.items() for p in DANGER if p.search(t)]
    if hits:
        log("중단: 비밀값 의심 → " + "; ".join(hits))
        alert("메모리에 비밀값/개인정보 의심 문자열이 있어 동기화 안 함. 클로드에게 확인 요청: " + "; ".join(hits)[:300])
        return 1
    for n, t in files.items():
        (DST / n).write_bytes(t.encode("utf-8"))
    for old in DST.glob("*.md"):  # 메모리에서 지운 파일은 사본에서도 지움
        if old.name not in files:
            old.unlink()
    git("add", "-A", "--", "docs/claude-memory")
    if not git("diff", "--cached", "--name-only", "--", "docs/claude-memory").stdout.strip():
        git("reset", "-q", "--", "docs/claude-memory")
        log("바뀐 것 없음")
        return 0
    changed = git("diff", "--cached", "--name-only", "--", "docs/claude-memory").stdout.split()
    if dry:
        git("reset", "-q", "--", "docs/claude-memory")
        log(f"(시험) 바뀔 파일 {len(changed)}개: {', '.join(Path(c).name for c in changed)}")
        return 0
    msg = f"Memory sync {datetime.now():%Y-%m-%d} (auto, personal files kept local, Notion URLs redacted)"
    r = git("commit", "-q", "-m", msg, "--", "docs/claude-memory")
    if r.returncode:
        log("커밋 실패: " + r.stderr.strip()[:300])
        alert("메모리 동기화 커밋 실패")
        return 1
    r = git("push", "-q")
    if r.returncode:
        git("pull", "-q", "--rebase", "--autostash")
        r = git("push", "-q")
    if r.returncode:
        log("푸시 실패: " + r.stderr.strip()[:300])
        alert("메모리 동기화 푸시 실패 (커밋은 됨)")
        return 1
    log(f"올림: {len(changed)}개 파일")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry" in sys.argv))
