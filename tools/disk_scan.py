#!/usr/bin/env python3
r"""Drive usage scan for the main PC. READ-ONLY: never deletes, moves or edits anything.

Walks C:\ and D:\ once each. Junctions and symlinks (the game folders moved to D on
2026-09-07 are junctions) are listed but never followed, so nothing is counted twice
and no scan wanders into another drive.

Writes a Korean report to the desktop: 드라이브점검-YYYYMMDD-HHMM.md
The report lists personal file paths: do not commit it (show is a public repo).

Usage on the main PC:  tools\disk-scan.bat   or   py -3 tools\disk_scan.py
Options: --roots C:\ D:\   --out <folder>   --depth 3   --min-gb 1
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import heapq
import os
import re
import shutil
import sys
import time
from collections import defaultdict

# OneDrive "online-only" placeholders are listed with their full size but use no disk space.
CLOUD_ONLY = 0x1000 | 0x40000 | 0x400000  # OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS
REPARSE_POINT = 0x400
TOP_FILES = 50
TOP_FOLDERS = 60
SYSTEM_FILES = {"pagefile.sys", "hiberfil.sys", "swapfile.sys", "dumpstack.log.tmp"}

SAFE, CHECK = "safe", "check"

# (tier, path pattern, note). %VARS% and * are expanded on the main PC.
CANDIDATES = [
    (SAFE, r"%LOCALAPPDATA%\Temp", "프로그램들이 쓰고 남긴 임시 파일"),
    (SAFE, r"C:\Windows\Temp", "Windows 임시 파일 (관리자 권한이 없으면 작게 나옴)"),
    (SAFE, r"C:\Windows\SoftwareDistribution\Download", "이미 설치된 Windows 업데이트 원본"),
    (SAFE, r"C:\ProgramData\Microsoft\Windows\WER", "프로그램 오류 보고서"),
    (SAFE, r"%LOCALAPPDATA%\CrashDumps", "프로그램 충돌 기록"),
    (SAFE, r"C:\Windows\Minidump", "블루스크린 기록"),
    (SAFE, r"%LOCALAPPDATA%\pip\Cache", "파이썬 패키지 캐시 (pip cache purge)"),
    (SAFE, r"%LOCALAPPDATA%\uv\cache", "uv 캐시 (uv cache clean)"),
    (SAFE, r"%LOCALAPPDATA%\npm-cache", "npm 캐시 (npm cache clean --force)"),
    (SAFE, r"%LOCALAPPDATA%\D3DSCache", "그래픽 셰이더 캐시 (게임 첫 실행만 잠깐 느려짐)"),
    (SAFE, r"%LOCALAPPDATA%\NVIDIA\DXCache", "NVIDIA 셰이더 캐시"),
    (SAFE, r"%LOCALAPPDATA%\NVIDIA\GLCache", "NVIDIA 셰이더 캐시"),
    (SAFE, r"%LOCALAPPDATA%\Google\Chrome\User Data\*\Cache", "크롬 캐시 (크롬 설정에서 비우기)"),
    (SAFE, r"%LOCALAPPDATA%\Google\Chrome\User Data\*\Code Cache", "크롬 캐시"),
    (SAFE, r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*\Cache", "엣지 캐시"),
    (SAFE, r"%LOCALAPPDATA%\Unity\cache", "유니티 패키지 캐시 (필요하면 다시 받아짐)"),
    (SAFE, r"C:\$Recycle.Bin", "C 휴지통"),
    (SAFE, r"D:\$Recycle.Bin", "D 휴지통"),
    (CHECK, r"C:\_moved_to_D_*", "2026-09-04 D 이전 때 남긴 C 원본. D 쪽이 잘 돌면 삭제 가능"),
    (CHECK, r"C:\Windows.old", "이전 Windows (Windows 정리 도구로만 삭제)"),
    (CHECK, r"%USERPROFILE%\Downloads", "다운로드 폴더"),
    (CHECK, r"D:\yt-auto\output", "유튜브 영상 결과물 (이미 업로드됨). 월별 표 참고"),
    (CHECK, r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\output", "콤피 생성 결과물"),
    (CHECK, r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models", "콤피 모델 (17:20 저녁 클립 모델은 보존)"),
    (CHECK, r"D:\wt", "브랜치 작업 폴더 (gitwork.sh list 로 확인 후 drop)"),
    (CHECK, r"C:\Program Files\Unity\Hub\Editor", "유니티 편집기 버전들 (지울 땐 유니티 허브에서)"),
    (CHECK, r"%APPDATA%\Claude\claude-code", "클로드 CLI 버전들 (최신 2개는 보존)"),
    (CHECK, r"%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude-code",
     "클로드 CLI 버전들 (최신 2개는 보존)"),
    (CHECK, r"C:\LDPlayer*", "LD플레이어 (안 쓰면 설정 > 앱에서 제거)"),
    (CHECK, r"D:\LDPlayer*", "LD플레이어 (안 쓰면 설정 > 앱에서 제거)"),
]

KEEP_TEXT = """\
- `D:\\yt-auto`, `D:\\ai-daily`, `D:\\coin-bot`, `D:\\market-compass`, `D:\\hub`, `D:\\notify`, `D:\\self-audit`
  (단, 승인받은 `D:\\yt-auto\\output` 의 오래된 날짜 폴더는 예외). 각 폴더의 `secrets`, `.env`, `.venv` 포함
- `C:\\Users\\User\\OneDrive\\Desktop\\show` 와 바탕화면의 경고·보고 파일
- 아래 「다른 드라이브로 연결된 링크」 전부 (C에 남은 게임 링크와 D의 실제 게임 폴더)
- `D:\\aivideos` (콤피 데스크톱 설치본), 17:20 저녁 클립에 쓰는 콤피 모델
- `%USERPROFILE%\\.cache\\huggingface` (자막용 whisper 모델, 매일 사용), `%USERPROFILE%\\.claude` (클로드 메모리)
- `C:\\Windows`, `C:\\Program Files*`, `C:\\ProgramData` (위 안전 목록의 임시 폴더만 예외), pagefile·hiberfil
"""


def norm(p: str) -> str:
    return os.path.normcase(os.path.normpath(p))


def expand(pattern: str) -> list[str]:
    if "%" in pattern:
        pattern = os.path.expandvars(pattern)
        if "%" in pattern:  # variable not defined on this machine
            return []
    return sorted(p for p in glob.glob(pattern) if os.path.isdir(p))


def is_link(entry: os.DirEntry) -> bool:
    """Junction or symlink: never walk into it."""
    if entry.is_symlink():
        return True
    is_junction = getattr(entry, "is_junction", None)  # Python 3.12+
    if is_junction is not None:
        try:
            return is_junction()
        except OSError:
            return True
    try:
        attrs = entry.stat(follow_symlinks=False).st_file_attributes
    except (OSError, AttributeError):
        return False
    if not attrs & REPARSE_POINT:
        return False
    try:  # junctions and symlinks have a target; OneDrive folders do not
        os.readlink(entry.path)
        return True
    except (OSError, ValueError):
        return False


def link_target(path: str) -> str:
    try:
        t = os.readlink(path)
    except (OSError, ValueError):
        return "?"
    return t[4:] if t.startswith("\\\\?\\") else t


def fmt_size(n: float) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:,.1f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:,.0f} MB"
    return f"{n / 1024:,.0f} KB"


def fmt_date(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "-"


def drive_of(path: str) -> str:
    return os.path.splitdrive(path)[0].upper()


class Scan:
    def __init__(self, depth: int, watch: set[str]):
        self.depth = depth
        self.watch = watch
        self.dirs: dict[str, tuple] = {}  # norm -> (path, size, files, newest, depth)
        self.watched_files: dict[str, list] = defaultdict(list)  # parent norm -> [(size, path, mtime)]
        self.links: list[tuple[str, str]] = []
        self.top: list[tuple] = []
        self.cloud_bytes = 0
        self.errors = 0
        self.ndirs = 0
        self.t0 = time.time()

    def _keep_big(self, size: int, path: str, mtime: float) -> None:
        item = (size, path, mtime)
        if len(self.top) < TOP_FILES:
            heapq.heappush(self.top, item)
        elif size > self.top[0][0]:
            heapq.heapreplace(self.top, item)

    def walk(self, path: str, depth: int = 0, parent_watched: bool = False):
        size = files = 0
        newest = 0.0
        key = norm(path)
        watched = key in self.watch
        self.ndirs += 1
        if self.ndirs % 20000 == 0:
            print(f"  ... 폴더 {self.ndirs:,}개 확인 ({time.time() - self.t0:,.0f}초) {path[:70]}", flush=True)
        try:
            it = os.scandir(path)
        except OSError:
            self.errors += 1
            it = None
        if it is not None:
            with it:
                for e in it:
                    try:
                        if is_link(e):
                            if e.is_dir():  # link to a folder: list it, do not count or follow
                                self.links.append((e.path, link_target(e.path)))
                        elif e.is_dir(follow_symlinks=False):
                            s, n, m = self.walk(e.path, depth + 1, watched)
                            size += s
                            files += n
                            newest = max(newest, m)
                        elif e.is_file(follow_symlinks=False):
                            st = e.stat(follow_symlinks=False)
                            if getattr(st, "st_file_attributes", 0) & CLOUD_ONLY:
                                self.cloud_bytes += st.st_size
                                continue
                            size += st.st_size
                            files += 1
                            newest = max(newest, st.st_mtime)
                            self._keep_big(st.st_size, e.path, st.st_mtime)
                            if watched:
                                self.watched_files[key].append((st.st_size, e.path, st.st_mtime))
                    except OSError:
                        self.errors += 1
        if depth <= self.depth or watched or parent_watched:
            self.dirs[key] = (path, size, files, newest, depth)
        return size, files, newest


def is_yt_output(path: str) -> bool:
    return norm(path).endswith(norm(os.path.join("yt-auto", "output")))


def children(scan: Scan, parent: str) -> list[tuple]:
    """(size, path, newest, kind) of recorded subfolders and files directly under parent."""
    pk = norm(parent)
    out = [(v[1], v[0], v[3], "폴더") for k, v in scan.dirs.items()
           if k != pk and norm(os.path.dirname(v[0])) == pk]
    out += [(s, p, m, "파일") for s, p, m in scan.watched_files.get(pk, [])]
    return sorted(out, reverse=True)


def build_report(scan: Scan, roots: list[str], cands: list[tuple], args, elapsed: float) -> str:
    now = dt.datetime.now()
    L: list[str] = []
    L.append(f"# 드라이브 점검 리포트 ({now:%Y-%m-%d %H:%M})")
    L.append("")
    L.append("> 이 리포트는 **읽기만** 했습니다. 아무것도 지우거나 옮기지 않았습니다.")
    L.append("> 개인 파일 경로가 들어 있으니 깃(공개 저장소 show)에 올리지 마세요.")
    L.append("")

    L.append("## 1. 드라이브 여유 공간")
    L.append("")
    L.append("| 드라이브 | 전체 | 사용 | 남음 | 남은 비율 |")
    L.append("|---|---|---|---|---|")
    for r in roots:
        try:
            u = shutil.disk_usage(r)
            L.append(f"| {r} | {fmt_size(u.total)} | {fmt_size(u.used)} | {fmt_size(u.free)} | {u.free / u.total:.0%} |")
        except OSError:
            L.append(f"| {r} | - | - | - | 읽기 실패 |")
    L.append("")

    tier_title = {SAFE: "### 2-1. 안전 (임시·캐시, 지워도 필요하면 다시 생김)",
                  CHECK: "### 2-2. 확인 필요 (주인이 정할 것)"}
    L.append("## 2. 정리 후보")
    L.append("")
    for tier in (SAFE, CHECK):
        rows = [c for c in cands if c[0] == tier]
        total = sum(c[3] for c in rows if c[3] is not None)
        L.append(f"{tier_title[tier]} — 합계 {fmt_size(total)}")
        L.append("")
        L.append("| 위치 | 크기 | 파일 수 | 마지막 변경 | 설명 |")
        L.append("|---|---|---|---|---|")
        for _, path, note, size, nfiles, newest in sorted(rows, key=lambda c: -(c[3] or 0)):
            if size is None:
                L.append(f"| `{path}` | 스캔 안 됨 | - | - | {note} |")
            else:
                L.append(f"| `{path}` | {fmt_size(size)} | {nfiles:,} | {fmt_date(newest)} | {note} |")
        L.append("")
        if tier == CHECK:
            for _, path, note, size, _n, _m in rows:
                if not size or is_yt_output(path):
                    continue
                kids = children(scan, path)[:15]
                if not kids:
                    continue
                L.append(f"**`{path}` 안에서 큰 것**")
                L.append("")
                for s, p, m, kind in kids:
                    L.append(f"- {fmt_size(s)} · {fmt_date(m)} · {kind} `{os.path.basename(p)}`")
                L.append("")

    L.append("### 2-3. 건드리지 말 것")
    L.append("")
    L.append(KEEP_TEXT)

    ytout = next((c for c in cands if is_yt_output(c[1]) and c[3]), None)
    if ytout:
        months: dict[str, list] = defaultdict(lambda: [0, 0])
        for s, p, _m, _k in children(scan, ytout[1]):
            name = os.path.basename(p)
            month = name[:7] if re.match(r"\d{4}-\d{2}", name) else "기타"
            months[month][0] += s
            months[month][1] += 1
        L.append("## 3. 유튜브 영상 결과물 월별 (`D:\\yt-auto\\output`)")
        L.append("")
        L.append("| 월 | 크기 | 날짜 폴더 수 |")
        L.append("|---|---|---|")
        for month in sorted(months):
            L.append(f"| {month} | {fmt_size(months[month][0])} | {months[month][1]} |")
        L.append("")

    L.append(f"## 4. 큰 폴더 ({args.min_gb:g}GB 이상, {args.depth}단계 깊이까지)")
    L.append("")
    min_bytes = args.min_gb * 1024 ** 3
    for r in roots:
        rk = norm(r)
        rows = [v for k, v in scan.dirs.items()
                if k.startswith(rk) and 1 <= v[4] <= args.depth and v[1] >= min_bytes]
        rows.sort(key=lambda v: -v[1])
        L.append(f"**{r}**")
        L.append("")
        if not rows:
            L.append("- (해당 없음)")
        for path, size, nfiles, newest, _d in rows[:TOP_FOLDERS]:
            L.append(f"- {fmt_size(size)} · {nfiles:,}개 · {fmt_date(newest)} · `{path}`")
        L.append("")

    L.append(f"## 5. 큰 파일 상위 {TOP_FILES}")
    L.append("")
    L.append("| 크기 | 마지막 수정 | 경로 |")
    L.append("|---|---|---|")
    for size, path, mtime in sorted(scan.top, reverse=True):
        mark = " (시스템 파일, 건드리지 말 것)" if os.path.basename(path).lower() in SYSTEM_FILES else ""
        L.append(f"| {fmt_size(size)} | {fmt_date(mtime)} | `{path}`{mark} |")
    L.append("")

    cross = [(p, t) for p, t in scan.links if t != "?" and drive_of(t) and drive_of(t) != drive_of(p)]
    same = len(scan.links) - len(cross)
    L.append("## 6. 다른 드라이브로 연결된 링크 (지우면 안 됨)")
    L.append("")
    L.append("링크는 따라가지 않고 이름만 적었습니다. 링크를 PowerShell `Remove-Item -Recurse` 로 지우면")
    L.append("**연결된 실제 폴더 내용까지 지워질 수 있으니** 절대 그렇게 지우지 마세요.")
    L.append("")
    for p, t in sorted(cross):
        L.append(f"- `{p}` → `{t}`")
    if not cross:
        L.append("- (없음)")
    L.append(f"- 같은 드라이브 안의 링크 {same:,}개 (대부분 Windows 기본 호환 링크라 무시해도 됨)")
    L.append("")

    L.append("## 7. 참고")
    L.append("")
    L.append(f"- 걸린 시간 {elapsed / 60:,.1f}분, 확인한 폴더 {scan.ndirs:,}개, 읽지 못한 항목 {scan.errors:,}개")
    L.append("  (권한이 없는 시스템 폴더는 크기에서 빠집니다. 시스템 복원 지점도 여기 안 잡힙니다)")
    L.append(f"- OneDrive 온라인 전용 파일 {fmt_size(scan.cloud_bytes)} 은 디스크를 쓰지 않아 크기에서 뺐습니다")
    L.append("- `C:\\Windows` 는 같은 파일을 여러 곳에서 가리키는 구조라 실제보다 크게 나올 수 있습니다")
    L.append("")
    return "\n".join(L)


def default_out() -> str:
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    for d in (os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Desktop")):
        if os.path.isdir(d):
            return d
    return os.getcwd()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    default_roots = [r for r in ("C:\\", "D:\\") if os.path.isdir(r)] if os.name == "nt" else ["/"]
    ap = argparse.ArgumentParser(description="읽기 전용 드라이브 점검 (아무것도 지우지 않음)")
    ap.add_argument("--roots", nargs="+", default=default_roots)
    ap.add_argument("--out", default=None, help="리포트 저장 폴더 (기본: 바탕화면)")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--min-gb", type=float, default=1.0)
    args = ap.parse_args()
    sys.setrecursionlimit(10000)

    cand_paths = [(tier, p, note) for tier, pat, note in CANDIDATES for p in expand(pat)]
    scan = Scan(args.depth, {norm(p) for _, p, _ in cand_paths})
    t0 = time.time()
    for r in args.roots:
        print(f"{r} 확인 중... (몇 분 걸릴 수 있어요. 아무것도 지우지 않습니다)", flush=True)
        scan.walk(r)

    cands = []
    for tier, p, note in cand_paths:
        v = scan.dirs.get(norm(p))
        cands.append((tier, p, note, v[1] if v else None, v[2] if v else 0, v[3] if v else 0))

    report = build_report(scan, args.roots, cands, args, time.time() - t0)
    out_dir = args.out or default_out()
    out = os.path.join(out_dir, f"드라이브점검-{dt.datetime.now():%Y%m%d-%H%M}.md")
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write(report)
    safe = sum(c[3] or 0 for c in cands if c[0] == SAFE)
    check = sum(c[3] or 0 for c in cands if c[0] == CHECK)
    print(f"\n완료. 안전 후보 {fmt_size(safe)}, 확인 필요 후보 {fmt_size(check)}")
    print(f"리포트: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
