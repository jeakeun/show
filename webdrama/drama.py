# -*- coding: utf-8 -*-
"""웹드라마 반자동 파이프라인 — 명령 하나로 각 단계를 실행한다.

  python drama.py series "로그라인"   시리즈 설정 + 인물 사진 작업지시서 (처음 한 번)
  python drama.py write              다음 회차 대본 + 장면 작업지시서
  python drama.py collect [--shot N] 다운로드 폴더의 장면 영상을 회차 폴더로
  python drama.py build              장면을 이어 붙여 자막·음악 넣은 완성본
  python drama.py publish            올릴 차례인 회차 1편을 켜진 플랫폼에 업로드 (작업 스케줄러용)
  python drama.py binge [1-10]       10화 묶음 몰아보기 롱폼을 유튜브에 (비우면 올릴 차례인 것, 작업 스케줄러용)
  python drama.py binge --build-only 다음 몰아보기를 만들기만 해서 미리보기
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
    state = read_json(STATE_PATH, {})  # 업로드 중에 재생목록 ID 가 저장됐을 수 있어 다시 읽는다
    state["last_publish"] = today
    write_json(STATE_PATH, state)
    left = len([k for k in nums if load_status(k).get("built") and not load_status(k).get("published_done")])
    msg = f"{n}화 「{ep['title']}」\n" + "\n".join(results) + f"\n남은 완성 회차: {left}편"
    if left == 0:
        msg += "\n다음 회차 영상을 만들어 주세요."
    print(msg)
    notify("Webdrama", msg)


def cmd_binge(a) -> None:
    """몰아보기 롱폼. 범위 없이 실행하면 작업 스케줄러용 자동 모드 (올릴 차례인 묶음 1편)."""
    import binge
    today = datetime.date.today().isoformat()
    done = read_json(STATE_PATH, {}).get("binges", {})
    auto = not a.range and not a.build_only
    if a.range:
        r = binge.parse_range(a.range)
        prev = done.get(binge.key(*r))
        if prev and not (a.force or a.build_only or a.dry_run):
            raise SystemExit(f"{r[0]}~{r[1]}화 몰아보기는 이미 {'올렸습니다' if prev.get('ok') else '올리다 실패했습니다'}"
                             f" ({prev.get('at', '')}). 다시 올리려면 --force (유튜브에 한 편 더 생깁니다).")
    elif a.build_only:
        r = binge.next_preview()
        if not r:
            print("미리 만들 몰아보기가 없습니다 (다음 묶음의 회차가 모두 편집돼야 합니다. 현황보기.bat 참고).")
            return
    else:
        if not binge.cfg()["enabled"]:
            print("몰아보기가 꺼져 있습니다 (config.json 의 binge.enabled).")
            return
        if not CONFIG["platforms"]["youtube"].get("enabled"):
            print("유튜브가 꺼져 있어 몰아보기를 건너뜁니다.")
            return
        if read_json(STATE_PATH, {}).get("last_binge") == today and not a.force:
            print("오늘은 이미 몰아보기를 올렸습니다.")
            return
        r = binge.due(today)
        if not r:
            print("올릴 차례인 몰아보기가 없습니다.")
            _warn_blocked(binge)
            return
    lo, hi = r
    bible = load_bible()
    if a.dry_run:
        try:
            chaps = binge.chapters(lo, hi)
        except SystemExit as e:
            print(e)
            chaps = [(0, k, "?") for k in range(lo, hi + 1)]
        meta = binge.texts(bible, lo, hi, chaps, read_json(STATE_PATH, {}).get("youtube_playlist", ""))
        print(f"(테스트) {lo}~{hi}화 몰아보기를 올릴 예정\n\n제목: {meta['title']}\n\n{meta['description']}")
        return

    print(f"{lo}~{hi}화 몰아보기 만드는 중... (몇 분 걸립니다)")
    try:
        res = binge.build(lo, hi, bible["title"])
    except (Exception, SystemExit) as e:  # 열어 둔 파일·깨진 json 등 무엇이든 알림은 가게
        msg = f"{lo}~{hi}화 몰아보기 만들기 실패 (다음 업로드 날 다시 시도)\n{e}"
        print(msg)
        if auto:
            notify("Webdrama", msg)
        raise SystemExit(1)
    length = f"{int(res['seconds'] // 60)}분 {int(res['seconds'] % 60)}초"
    extra = "\n8분이 안 돼 중간 광고는 붙지 않습니다." if res["seconds"] < 480 else ""
    if res["thumb_error"]:
        extra += f"\n썸네일 만들기 실패: {res['thumb_error'][-150:]}"
    if a.build_only:
        print(f"완성: {res['path']} ({length}){extra}\n썸네일: {res['thumb'] or '없음'}\n(올리지는 않았습니다)")
        _open(res["path"])
        return

    from publisher import NotStarted, upload_youtube_long
    meta = binge.texts(bible, lo, hi, res["chapters"], read_json(STATE_PATH, {}).get("youtube_playlist", ""))
    print(f"유튜브 롱폼 업로드 중... ({length})")
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        url, note = upload_youtube_long(res["path"], bible, meta, res["thumb"])
        rec = {"ok": True, "at": now, "where": url, "seconds": round(res["seconds"], 1), "note": note}
        msg = f"몰아보기 {lo}~{hi}화 올림 ({length})\n{url}" + (f"\n{note}" if note else "") + extra
    except NotStarted as e:  # 아무것도 안 올라갔으니 기록하지 않고 다음 업로드 날 다시
        msg = f"몰아보기 {lo}~{hi}화를 못 올렸습니다 (업로드 시작 전 실패, 다음 업로드 날 다시 시도)\n{e}"
        print(msg)
        notify("Webdrama", msg)
        raise SystemExit(1)
    except Exception as e:  # 재시도 안 함 — 중복 게시 방지
        rec = {"ok": False, "at": now, "error": str(e)[:300]}
        msg = (f"몰아보기 {lo}~{hi}화 업로드 실패: {e}\n"
               f"유튜브 스튜디오에서 올라갔는지 먼저 확인하고, 안 올라갔으면 python drama.py binge {lo}-{hi} --force")
    try:
        state = read_json(STATE_PATH, {})
        state.setdefault("binges", {})[binge.key(lo, hi)] = rec
        state["last_binge"] = today
        write_json(STATE_PATH, state)
    except Exception as e:  # 기록을 못 남기면 다음에 또 올릴 수 있으니 반드시 알린다
        msg += (f"\n\n⚠ 기록 저장 실패({e}). 다음 업로드 날 같은 몰아보기가 또 올라가지 않게 "
                f"series\\state.json 을 확인해 주세요.")
    print(msg)
    notify("Webdrama", msg)
    if rec["ok"]:
        try:
            res["path"].unlink(missing_ok=True)  # 1GB 안팎이라 올린 뒤에는 지운다 (썸네일은 남김)
        except OSError:
            pass


def _warn_blocked(binge) -> None:
    """유튜브 기록이 빠진 회차 때문에 멈춘 묶음을 묶음마다 한 번만 알린다."""
    state = read_json(STATE_PATH, {})
    warned = set(state.get("binge_warned", []))
    for lo, hi, missing in binge.blocked():
        if binge.key(lo, hi) in warned:
            continue
        eps = ", ".join(map(str, missing))
        msg = (f"몰아보기 {lo}~{hi}화가 멈춰 있습니다: {eps}화가 유튜브에 올라간 기록이 없습니다.\n"
               f"다시 올리기: python drama.py publish --ep {missing[0]} --only youtube --force\n"
               f"(직접 올렸다면 그냥 python drama.py binge {lo}-{hi})")
        print(msg)
        notify("Webdrama", msg)
        warned.add(binge.key(lo, hi))
        state["binge_warned"] = sorted(warned)
        write_json(STATE_PATH, state)


def _binge_status() -> None:
    import binge
    c = binge.cfg()
    if not c["enabled"]:
        return
    done = read_json(STATE_PATH, {}).get("binges", {})
    nums = episode_numbers()
    print("\n몰아보기 (유튜브 롱폼)" + ("" if CONFIG["platforms"]["youtube"].get("enabled") else " — 유튜브 연결 후 시작") + ":")
    for k, r in done.items():
        lo, hi = k.split("-")
        print(f"  {lo}~{hi}화 — " + (f"올림 ✓ {r.get('where', '')}" if r.get("ok") else f"실패 ✗ {r.get('error', '')[:80]}"))
    last = max(nums, default=0)
    pending = [r for r in binge.candidates(last + c["every"]) if binge.key(*r) not in done]
    if pending:
        lo, hi = pending[0]
        print(f"  다음: {lo}~{hi}화 — {hi}화가 유튜브에 올라간 다음 업로드 날 자동으로 올라갑니다")
    for lo, hi, missing in binge.blocked():
        print(f"  ⚠ {lo}~{hi}화 멈춤: {', '.join(map(str, missing))}화의 유튜브 업로드 기록이 없음 (README 규칙 참고)")


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
    _binge_status()


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
    p = sub.add_parser("binge"); p.add_argument("range", nargs="?", help="예: 1-10 (비우면 올릴 차례인 묶음)")
    p.add_argument("--build-only", action="store_true", help="만들기만 하고 올리지 않음 (미리보기)")
    p.add_argument("--force", action="store_true"); p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("connect"); p.add_argument("platform", choices=["youtube"])
    a = ap.parse_args()
    globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()
