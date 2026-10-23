# -*- coding: utf-8 -*-
"""웹드라마 반자동 파이프라인 — 명령 하나로 각 단계를 실행한다.

  python drama.py series "로그라인"   시리즈 설정 + 인물 사진 작업지시서 (처음 한 번)
  python drama.py write              다음 회차 대본 + 장면 작업지시서
  python drama.py collect [--shot N] 다운로드 폴더의 장면 영상을 회차 폴더로
  python drama.py build              장면을 이어 붙여 자막·음악 넣은 완성본
  python drama.py publish            올릴 차례인 회차 1편을 켜진 플랫폼에 업로드 (작업 스케줄러용)
  python drama.py status             회차별 진행 상황
  python drama.py connect youtube    유튜브 채널 연결 (최초 1회)
"""
import argparse
import datetime
import os
import time

from common import (BIBLE_PATH, CONFIG, STATE_PATH, ep_dir, episode_numbers, load_bible, load_status,
                    notify, read_json, save_status, setup_console, write_json)


def _open(path) -> None:
    if os.getenv("WEBDRAMA_NO_OPEN"):
        return
    try:
        os.startfile(str(path))
    except Exception:
        pass


def _pick(n: int | None, want: str) -> int:
    """회차 번호를 안 주면 해당 단계를 기다리는 가장 앞 회차를 고른다."""
    nums = episode_numbers()
    if not nums:
        raise SystemExit("아직 만든 회차가 없습니다. 1_대본만들기.bat 부터 실행하세요.")
    if n:
        if n not in nums:
            raise SystemExit(f"{n}화가 없습니다.")
        return n
    for k in nums:
        st = load_status(k)
        if want == "clips" and not st.get("built"):
            return k
    return nums[-1]


def cmd_series(a) -> None:
    from sheet import character_sheet
    from writer import make_bible
    if BIBLE_PATH.exists() and not a.force:
        raise SystemExit("이미 시리즈가 있습니다. 새로 만들려면 --force (기존 설정은 series/bible.json 백업 후).")
    logline = a.logline or input("어떤 드라마인가요? 한두 문장으로 적고 엔터:\n> ").strip()
    if not logline:
        raise SystemExit("내용이 비어 있습니다.")
    print("시리즈 설정을 만드는 중... (1~2분)")
    bible = make_bible(logline)
    write_json(BIBLE_PATH, bible)
    page = character_sheet(bible)
    print(f"\n시리즈: {bible['title']}\n{bible['logline']}\n")
    print("인물:", ", ".join(f"{c['name']}({c['id']})" for c in bible["characters"]))
    print(f"\n다음 할 일: 열리는 페이지를 보고 인물 사진을 만들어 series\\characters 에 넣으세요.\n{page}")
    _open(page)


def cmd_write(a) -> None:
    from sheet import episode_sheet
    from writer import make_episode
    bible = load_bible()
    nums = episode_numbers()
    n = (nums[-1] + 1) if nums else 1
    previous = [dict(n=k, **{f: read_json(ep_dir(k) / "script.json")[f] for f in ("title", "summary")})
                for k in nums]
    titles = {p["title"] for p in previous}
    print(f"{n}화 대본을 쓰는 중... (1~2분)")
    ep = make_episode(bible, n, previous)
    if ep["title"] in titles:
        ep = make_episode(bible, n, previous)
    folder = ep_dir(n)
    (folder / "clips").mkdir(parents=True, exist_ok=True)
    write_json(folder / "script.json", ep)
    save_status(n, {"written": datetime.datetime.now().isoformat(timespec="seconds"),
                    "written_ts": time.time()})
    page = episode_sheet(bible, n, ep, folder)
    total = sum(s["seconds"] for s in ep["shots"])
    print(f"\n{n}화 「{ep['title']}」 장면 {len(ep['shots'])}개 · 약 {total}초")
    print(f"작업지시서: {page}")
    _open(page)


def cmd_sheet(a) -> None:
    from sheet import character_sheet, episode_sheet
    bible = load_bible()
    if a.characters:
        _open(character_sheet(bible))
        return
    n = _pick(a.ep, "clips")
    _open(episode_sheet(bible, n, read_json(ep_dir(n) / "script.json"), ep_dir(n)))


def cmd_collect(a) -> None:
    from editor import clip_path, collect, downloads_dir
    n = _pick(a.ep, "clips")
    folder = ep_dir(n)
    ep = read_json(folder / "script.json")
    st = load_status(n)
    moved = collect(folder, ep, st.get("written_ts", 0), a.shot)
    print(f"{n}화 — 다운로드 폴더: {downloads_dir()}")
    for m in moved:
        print("  " + m)
    if not moved:
        print("  새로 받은 영상이 없습니다. 힉스필드에서 다운로드했는지 확인하세요.")
    have = [i for i in range(1, len(ep["shots"]) + 1) if clip_path(folder, i).exists()]
    left = len(ep["shots"]) - len(have)
    print(f"\n장면 {len(have)}/{len(ep['shots'])}개 준비됨." +
          (f" 아직 {left}개 남았습니다." if left else " 모두 모였습니다 → 3_편집하기.bat"))


def cmd_build(a) -> None:
    from editor import build
    from publisher import texts
    n = _pick(a.ep, "clips")
    folder = ep_dir(n)
    ep = read_json(folder / "script.json")
    print(f"{n}화 편집 중... (장면 수에 따라 1~3분)")
    final, total, bgm = build(folder, ep, n)
    t = texts(load_bible(), n, ep)
    (folder / "업로드문구.txt").write_text(t["short"] + "\n", encoding="utf-8")
    st = load_status(n)
    st.update(built=datetime.datetime.now().isoformat(timespec="seconds"), seconds=round(total, 1), bgm=bgm)
    save_status(n, st)
    print(f"완성: {final} ({total:.0f}초)")
    print("올릴 차례가 되면 자동으로 올라갑니다. 먼저 한 번 확인해 보세요.")
    _open(final)


def _enabled() -> list[str]:
    return [k for k, v in CONFIG["platforms"].items() if v.get("enabled")]


def cmd_publish(a) -> None:
    from publisher import HANDLERS, NAMES
    bible = load_bible()
    state = read_json(STATE_PATH, {})
    today = datetime.date.today().isoformat()
    if state.get("last_publish") == today and not a.force:
        print("오늘은 이미 올렸습니다.")
        return
    targets = _enabled()
    if a.only:
        targets = [a.only]
    if not targets:
        print("켜진 플랫폼이 없습니다 (config.json 의 platforms.*.enabled).")
        return
    nums = episode_numbers()
    ready = [k for k in nums if load_status(k).get("built") and not load_status(k).get("published_done")]
    if a.ep:
        ready = [a.ep]
    if not ready:
        notify("Webdrama", "올릴 완성 회차가 없습니다. 1_대본만들기 → 힉스필드 → 편집을 해 주세요.")
        print("올릴 완성 회차가 없습니다.")
        return
    n = ready[0]
    folder = ep_dir(n)
    ep = read_json(folder / "script.json")
    st = load_status(n)
    pub = st.setdefault("published", {})
    results = []
    for key in targets:
        if key in pub and not a.force:
            continue
        if a.dry_run:
            results.append(f"{NAMES[key]}: (테스트) 올릴 예정")
            continue
        print(f"{n}화 → {NAMES[key]} 업로드 중...")
        try:
            where = HANDLERS[key](folder / "final.mp4", bible, n, ep)
            pub[key] = {"ok": True, "at": datetime.datetime.now().isoformat(timespec="seconds"), "where": where}
            results.append(f"{NAMES[key]}: 성공 {where}")
        except Exception as e:  # 재시도 안 함 — 중복 게시 방지
            pub[key] = {"ok": False, "at": datetime.datetime.now().isoformat(timespec="seconds"), "error": str(e)[:300]}
            results.append(f"{NAMES[key]}: 실패 {e}")
    if a.dry_run:
        print("\n".join(results))
        return
    st["published_done"] = all(k in pub for k in _enabled())
    save_status(n, st)
    state["last_publish"] = today
    write_json(STATE_PATH, state)
    left = len([k for k in nums if load_status(k).get("built") and not load_status(k).get("published_done")])
    msg = f"{n}화 「{ep['title']}」\n" + "\n".join(results) + f"\n남은 완성 회차: {left}편"
    if left == 0:
        msg += "\n다음 회차 영상을 만들어 주세요."
    print(msg)
    notify("Webdrama", msg)


def cmd_status(a) -> None:
    bible = read_json(BIBLE_PATH)
    if not bible:
        print("시리즈 없음 → 0_시리즈만들기.bat")
        return
    from editor import clip_path
    print(f"「{bible['title']}」  켜진 플랫폼: {', '.join(_enabled()) or '없음'}")
    print(f"올리는 요일: {', '.join(CONFIG['publish_days'])} {CONFIG['publish_time']}\n")
    for k in episode_numbers():
        ep = read_json(ep_dir(k) / "script.json")
        st = load_status(k)
        have = sum(clip_path(ep_dir(k), i).exists() for i in range(1, len(ep["shots"]) + 1))
        if st.get("published_done") or st.get("published"):
            stage = "업로드: " + ", ".join(f"{p}{'✓' if r['ok'] else '✗'}" for p, r in st.get("published", {}).items())
        elif st.get("built"):
            stage = "완성 · 올릴 차례 기다리는 중"
        else:
            stage = f"장면 {have}/{len(ep['shots'])}"
        print(f"{k:>3}화 「{ep['title']}」 — {stage}")


def cmd_connect(a) -> None:
    from publisher import youtube_whoami
    if a.platform == "youtube":
        print("연결된 유튜브 채널:", youtube_whoami())
        print("이 채널이 웹드라마 채널이 아니면 secrets\\yt_token.json 을 지우고 다시 실행하세요.")


def main() -> None:
    setup_console()
    ap = argparse.ArgumentParser(description="웹드라마 반자동 파이프라인")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("series"); p.add_argument("logline", nargs="?"); p.add_argument("--force", action="store_true")
    sub.add_parser("write")
    p = sub.add_parser("sheet"); p.add_argument("ep", type=int, nargs="?"); p.add_argument("--characters", action="store_true")
    p = sub.add_parser("collect"); p.add_argument("ep", type=int, nargs="?"); p.add_argument("--shot", type=int)
    p = sub.add_parser("build"); p.add_argument("ep", type=int, nargs="?")
    p = sub.add_parser("publish"); p.add_argument("--ep", type=int); p.add_argument("--only", choices=["youtube", "instagram", "tiktok"])
    p.add_argument("--force", action="store_true"); p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("connect"); p.add_argument("platform", choices=["youtube"])
    a = ap.parse_args()
    globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()
