# -*- coding: utf-8 -*-
"""매일 쌓이는 기록 파일 자동 백업 (예약 DataBackupNightly, 매일 05:40).

정해 둔 폴더만 각 비공개 저장소 main 에 커밋·푸시한다. 코드·설정은 건드리지 않는다
(코드 변경은 브랜치 규칙대로 사람이 승인 후). 2026-11-21 안전 점검에서 데이터가
몇 주씩 커밋 안 된 채 PC에만 있던 것을 막으려고 만듦.

멈추는 경우: main 이 아님 / 다른 staged 파일이 있음 / 깃 오류. 실패하면 폰 알림.
실행: python tools/data_backup.py [--dry]
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TARGETS = {
    r"D:\yt-auto": ["data", "reports"],
    r"D:\ai-daily": ["채용", "뉴스논문"],
    r"D:\kids-toon": ["data", "retro", "experiments.json", "state.json", "research"],
}
LOG = Path(__file__).resolve().parent / "data_backup.log"


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M} {msg}"
    try:
        print(line)
    except Exception:
        pass
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def alert(msg):
    try:
        sys.path.insert(0, r"D:\notify")
        from push import push
        push("Data backup", msg)
    except Exception as e:
        log(f"알림 실패: {type(e).__name__}")


def git(repo, *args):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8",
                       timeout=180, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if r.returncode:
        raise RuntimeError(f"git {args[0]}: {r.stderr.strip()[:150]}")
    return r.stdout


def backup(repo, paths, dry):
    paths = [p for p in paths if (Path(repo) / p).exists()]
    if not paths:
        return "대상 없음"
    if git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() != "main":
        raise RuntimeError("main 브랜치가 아님")
    if git(repo, "diff", "--cached", "--name-only").strip():
        raise RuntimeError("미리 staged 된 파일이 있음(사람 작업 중)")
    changed = git(repo, "status", "--porcelain", "--", *paths).strip()
    if not changed:
        return "바뀐 것 없음"
    n = len(changed.splitlines())
    if dry:
        return f"(시험) {n}개 바뀜"
    git(repo, "add", "-A", "--", *paths)
    git(repo, "commit", "-q", "-m", f"Data and reports through {datetime.now():%Y-%m-%d} (auto backup)", "--", *paths)
    git(repo, "push", "-q", "origin", "main")
    return f"{n}개 올림"


def main():
    dry = "--dry" in sys.argv
    fails = []
    for repo, paths in TARGETS.items():
        name = Path(repo).name
        try:
            log(f"{name}: {backup(repo, paths, dry)}")
        except Exception as e:
            log(f"{name}: 실패 - {e}")
            fails.append(name)
    if fails:
        alert(f"기록 백업 실패: {', '.join(fails)} (show/tools/data_backup.log 확인)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
