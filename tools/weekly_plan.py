# -*- coding: utf-8 -*-
"""월요일 아침 "이번 주 계획" 한 장 (유튜브 3채널: 1분호기심·뿅뿅마을·숏드라마).

새 AI 호출 없음. 회고 보고서·설정 파일에 이미 있는 내용을 코드로 모아 정리만 한다.
결과: D:\\hub\\weekly_plan\\YYYY-MM-DD.md + 폰 알림(요약).
실행: python tools/weekly_plan.py [--date 2026-11-23] [--no-push]
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

YT = Path(r"D:\yt-auto")
KIDS = Path(r"D:\kids-toon")
DRAMA = Path(__file__).resolve().parent.parent / "webdrama"
OUT = Path(r"D:\hub\weekly_plan")
NOTIFY = Path(r"D:\notify")
DOW = "월화수목금토일"


def md(d):
    return f"{d.month}/{d.day}({DOW[d.weekday()]})"


def jload(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def section(text, head):
    """'## <head>' 부터 다음 '## ' 전까지."""
    m = re.search(r"^## [^\n]*" + re.escape(head) + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


ANSWERED = OUT / "answered.json"  # {"회고날짜": {"결정번호": "고른 답"}} - 사용자가 답하면 클로드가 적음


def answered_decisions(report_day):
    """설정 메모의 결정 번호는 회고 번호와 다를 때가 있어 추측하지 않고 기록 파일만 믿는다."""
    return {int(k): v for k, v in jload(ANSWERED).get(report_day.isoformat(), {}).items()}


def yt_part(mon, days):
    cfg = jload(YT / "config.json")
    lines = ["## 1분호기심", "", "**이번 주에 도는 것**",
             "- 매일 아침 7시·저녁 6시 쇼츠 자동 업로드"]
    st = cfg.get("style_test", {})
    if st.get("enabled"):
        start, arms = date.fromisoformat(st["start"]), st.get("arms", [])
        name = {"control": "기존", "sentence": "문장 자막", "sentence_sfx": "문장 자막+효과음"}
        if arms:
            row = " / ".join(f"{d.month}/{d.day} {name.get(arms[(d - start).days % len(arms)], '?')}"
                             for d in days if d >= start)
            lines.append(f"- 자막·소리 시험(날짜마다 교대): {row}")
    story = cfg.get("story_test", {})
    if story.get("enabled"):
        hits = [f"{md(d)} {story['dates'][d.isoformat()]}" for d in days if d.isoformat() in story.get("dates", {})]
        if hits:
            lines.append("- 저녁 이야기 시험: " + ", ".join(hits))
    comp = cfg.get("compilation", {})
    if comp.get("enabled"):
        ds = [md(d) for d in days if d.weekday() in comp.get("weekdays", [])]
        lines.append(f"- 몰아보기 롱폼 예약 공개: {', '.join(ds)} 저녁 {comp.get('hour', 20)}시")
    if cfg.get("image_test", {}).get("dates"):
        lines.append(f"- 그림 엔진 시험: {cfg['image_test']['dates']}")
    lines.append(f"- 주간 회고: {md(days[-1])} 밤 11시 50분")

    reps = sorted((YT / "reports").glob("*-주간리포트.md"))
    if not reps:
        return lines + ["", "(회고 보고서 없음)"]
    rep = reps[-1]
    rday = date.fromisoformat(rep.name[:10])
    text = rep.read_text(encoding="utf-8")
    strat = section(text, "다음 기간 전략")
    if strat:
        lines += ["", f"**이번 주 시험과 합격선** ({rep.name[:10]} 회고)"]
        for item in re.split(r"\n(?=\d+\. )", strat):
            first = item.strip().splitlines()[0] if item.strip() else ""
            if not re.match(r"\d+\. ", first):
                continue
            exp = re.search(r"예상:\s*(.+)", item)
            lines.append(f"- {first[3:].strip().strip('*')}" + (f" → {exp.group(1).strip()}" if exp else ""))
    dec = section(text, "결정 필요")
    if dec:
        done = answered_decisions(rday)
        todo, did = [], []
        for item in re.split(r"\n(?=\d+\. )", dec):
            m = re.match(r"(\d+)\. (.+)", item.strip())
            if not m:
                continue
            n, title = int(m.group(1)), m.group(2).strip()
            if n in done:
                did.append(f"{n}{done[n]}")
            else:
                rec = re.search(r"추천:\s*([A-D])", item)
                dflt = re.search(r"안 정하면:\s*(.+)", item)
                todo.append(f"- {n}. {title}" + (f" (추천 {rec.group(1)})" if rec else "")
                            + (f"\n  - 안 정하면: {dflt.group(1).strip()}" if dflt else ""))
        lines += ["", "**아직 답 안 한 결정** (유튜브 세션에 \"결정 N번 A\"처럼 답하면 됨)"] + (todo or ["- 없음"])
        if did:
            lines.append(f"- (답한 것: {', '.join(did)})")
    return lines


def kids_part(days):
    cfg = jload(KIDS / "config.json")
    lines = ["## 뿅뿅마을", "", "**이번 주에 도는 것**"]
    if not cfg.get("enabled", True):
        lines.append("- 자동 제작 꺼져 있음")
    for k, s in cfg.get("series", {}).items():
        lines.append(f"- {k} {s.get('name', '')}: 매일 {s.get('upload_kst', '?')} 업로드, 캐릭터 {'→'.join(s.get('rotation', []))} 순서")
    lines.append(f"- 매일 새벽 {cfg.get('make_time_kst', '03:00')} 제작 / 주간 회고 월요일 새벽 2시 20분")
    exp = jload(KIDS / "experiments.json")
    act = exp.get("active")
    lines += ["", "**실험**"]
    if act:
        lines.append(f"- 진행 중: {act.get('question', act) if isinstance(act, dict) else act}")
    else:
        lines.append("- 진행 중인 실험 없음")
    props = [p for p in exp.get("proposals", []) if p.get("status") != "done"]
    for p in props:
        lines.append(f"- 제안 대기({p.get('proposed', '')}, {p.get('status', '')}): {p.get('question', '')}")
    retro = sorted((KIDS / "retro").glob("*.md"))
    if retro:
        lines.append(f"- 최신 회고: {retro[-1]}")
    else:
        lines.append("- 회고 보고서 아직 없음(첫 회고 전)")
    return lines


def drama_part():
    lines = ["## 숏드라마", ""]
    eps = sorted(p.name for p in (DRAMA / "episodes").glob("ep*") if p.is_dir())
    lines.append(f"- 만든 회차 폴더: {len(eps)}개 ({', '.join(eps) or '없음'})")
    lines.append("- 자동 실행 없음(영상 생성은 사람이 직접). 진행은 숏드라마 세션에서")
    return lines


def main():
    args = sys.argv[1:]
    today = date.fromisoformat(args[args.index("--date") + 1]) if "--date" in args else date.today()
    mon = today - timedelta(days=today.weekday())
    days = [mon + timedelta(days=i) for i in range(7)]
    lines = [f"# 이번 주 계획 ({md(days[0])} ~ {md(days[-1])})", "",
             f"> {datetime.now():%Y-%m-%d %H:%M} 자동 작성. 회고·설정 파일 내용만 모음(새 AI 판단 없음).", ""]
    for part in (lambda: yt_part(mon, days), lambda: kids_part(days), drama_part):
        try:
            lines += part()
        except Exception as e:  # 한 채널 자료가 깨져도 나머지는 만든다
            lines += [f"(이 부분 만들다 오류: {e})"]
        lines.append("")
    text = "\n".join(lines)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{mon.isoformat()}.md"
    p.write_text(text, encoding="utf-8")
    print(text)
    if "--no-push" not in args:
        try:
            sys.path.insert(0, str(NOTIFY))
            from push import push
            body = re.sub(r"\*\*|^> .*\n|^# .*\n", "", text, flags=re.M)
            body = body.encode("utf-8")[:3800].decode("utf-8", "ignore")
            push("Weekly plan", body)
        except Exception:
            pass


if __name__ == "__main__":
    main()
