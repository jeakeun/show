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


PROBLEMS = []  # 읽기 실패 기록 (Codex 검토: '실험 없음'과 '파일을 못 읽음'을 구분해 계획 맨 아래에 표시)


def jload(p, optional=False):
    p = Path(p)
    if not p.exists():
        if not optional:
            PROBLEMS.append(f"{p} 없음")
        return {}
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(v, dict):
            raise ValueError("형식이 dict 가 아님")
        return v
    except Exception as e:
        PROBLEMS.append(f"{p} 읽기 실패({type(e).__name__})")
        return {}


def section(text, head):
    """'## <head>' 부터 다음 '## ' 전까지."""
    m = re.search(r"^## [^\n]*" + re.escape(head) + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


ANSWERED = OUT / "answered.json"  # {"회고날짜": {"결정번호": "고른 답"}} - 사용자가 답하면 클로드가 적음


def answered_decisions(report_day):
    """설정 메모의 결정 번호는 회고 번호와 다를 때가 있어 추측하지 않고 기록 파일만 믿는다."""
    out = {}
    for k, v in (jload(ANSWERED, optional=True).get(report_day.isoformat()) or {}).items():
        try:
            out[int(k)] = v
        except ValueError:
            PROBLEMS.append(f"answered.json 번호 형식 오류: {k}")
    return out


def yt_part(mon, days):
    cfg = jload(YT / "config.json")
    lines = ["## 1분호기심", "", "**이번 주에 도는 것**",
             "- 매일 아침 7시·저녁 6시 쇼츠 자동 업로드"]
    st = cfg.get("style_test", {})
    if st.get("enabled"):
        # 운영 코드(src/pipeline.py)와 같은 기본값: 시작일 2026-11-17, 시험군 sentence→sentence_sfx→control
        start = date.fromisoformat(st.get("start") or "2026-11-17")
        arms = st.get("arms") or ["sentence", "sentence_sfx", "control"]
        name = {"control": "기존", "sentence": "문장 자막", "sentence_sfx": "문장 자막+효과음"}
        row = " / ".join(f"{d.month}/{d.day} {name.get(arms[(d - start).days % len(arms)], '?')}"
                         for d in days if d >= start)
        lines.append(f"- 자막·소리 시험(쇼츠, 날짜마다 교대, 대화형 제외): {row}")
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

    reps = []  # 계획 주 시작(월요일) 전날까지의 회고 중 최신 (과거 주를 --date 로 볼 때 미래 회고를 끌어오지 않게)
    for r in (YT / "reports").glob("*-주간리포트.md"):
        try:
            rd = date.fromisoformat(r.name[:10])
        except ValueError:
            PROBLEMS.append(f"회고 파일 이름 날짜 형식 오류: {r.name}")
            continue
        if rd < mon:
            reps.append((rd, r))
    if not reps:
        return lines + ["", "(이 주 이전 회고 보고서 없음)"]
    rday, rep = max(reps)
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
        if not todo and not did:  # 제목은 있는데 항목을 못 읽음 → '없음'이라고 하지 않는다
            PROBLEMS.append(f"{rep.name} '결정 필요' 항목 형식을 못 읽음 - 원본 확인")
        lines += ["", "**아직 답 안 한 결정** (유튜브 세션에 \"결정 N번 A\"처럼 답하면 됨)"] + (
            todo or ["- 없음" if did else "- (읽지 못함 - 회고 원본 확인)"])
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
            lines += [f"(이 부분 만들다 오류: {type(e).__name__}: {e})"]
        lines.append("")
    if PROBLEMS:
        lines += ["## ⚠️ 자료 확인 필요", ""] + [f"- {x}" for x in PROBLEMS] + [""]
    text = "\n".join(lines)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{mon.isoformat()}.md"
    tmp = p.with_suffix(".tmp")  # 임시 파일 → 교체 (쓰다 꺼져도 잘린 계획이 안 남게)
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)
    try:
        print(text)
    except Exception:  # pythonw 는 출력 창이 없음
        pass
    if "--no-push" not in args:
        body = re.sub(r"\*\*|^> .*\n|^# .*\n", "", text, flags=re.M)
        raw = body.encode("utf-8")
        if len(raw) > 3800:  # 알림 길이 한도 → 잘렸다고 표시하고 파일 위치 안내
            body = raw[:3600].decode("utf-8", "ignore") + f"\n\n(길어서 잘림 - 전체: {p})"
        try:
            sys.path.insert(0, str(NOTIFY))
            from push import push
            push("Weekly plan", body)
            status = "알림 보냄"
        except Exception as e:
            status = f"알림 실패 {type(e).__name__}"
        with (OUT / "send.log").open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M} {p.name} {status}\n")


if __name__ == "__main__":
    main()
