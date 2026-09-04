# 집가 마케팅 성과 리포트 만들기
#   실행: 리포트.bat  (또는  python report.py)
#
# 모으는 것
#   - 쓰레드: API로 글별 조회·좋아요·답글 (자동)
#   - 유튜브: 공개 페이지에서 조회수 (자동, tracked.json 에 영상 등록)
#   - 인스타: API 연결 전이라 수동 확인 안내
#   - 발행 이력: uploader/uploads_log.csv
# 결과: reports/리포트_YYYY-MM-DD.html  (브라우저로 열림)
import csv
import datetime
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import webbrowser
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = ROOT / "uploader" / "config.json"
LOG = ROOT / "uploader" / "uploads_log.csv"
TRACKED = HERE / "tracked.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def log(m):
    print(m, flush=True)


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------- 쓰레드 ----------

def threads_stats(cfg):
    th = cfg.get("threads", {})
    tok = th.get("access_token")
    if not tok:
        return {"ok": False, "why": "토큰이 없습니다 (설명서 5장 참고)"}

    def get(path, params):
        url = f"https://graph.threads.net/v1.0/{path}?" + urllib.parse.urlencode(
            {**params, "access_token": tok})
        try:
            return json.loads(urllib.request.urlopen(url, timeout=20).read().decode())
        except Exception as e:
            return {"_err": str(e)}

    me = get("me", {"fields": "id,username"})
    if "_err" in me:
        return {"ok": False, "why": f"연결 실패: {me['_err'][:80]}"}
    uid = me["id"]

    res = get(f"{uid}/threads", {"fields": "id,text,timestamp,permalink", "limit": 25})
    posts = []
    for p in res.get("data", []):
        ins = get(f"{p['id']}/insights", {"metric": "views,likes,replies,reposts"})
        vals = {m["name"]: (m.get("values", [{}])[0].get("value", 0))
                for m in ins.get("data", [])} if "_err" not in ins else {}
        replies = []
        if vals.get("replies"):
            r = get(f"{p['id']}/replies", {"fields": "text,username,timestamp"})
            replies = [{"who": x.get("username"), "text": x.get("text", "")}
                       for x in r.get("data", [])]
        posts.append({
            "text": (p.get("text") or "").strip(),
            "when": (p.get("timestamp") or "")[:16].replace("T", " "),
            "link": p.get("permalink", ""),
            "views": vals.get("views", 0), "likes": vals.get("likes", 0),
            "replies": vals.get("replies", 0), "reposts": vals.get("reposts", 0),
            "reply_list": replies,
        })
    return {"ok": True, "username": me.get("username"), "posts": posts}


# ---------- 유튜브 (공개 페이지에서 조회수) ----------

def youtube_stats(video_ids):
    out = []
    for vid in video_ids:
        item = {"id": vid, "title": "", "views": None,
                "link": f"https://youtu.be/{vid}"}
        try:
            req = urllib.request.Request(
                f"https://www.youtube.com/watch?v={vid}", headers=UA)
            page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
            m = re.search(r'"viewCount":"(\d+)"', page)
            if m:
                item["views"] = int(m.group(1))
            t = re.search(r'<meta name="title" content="([^"]*)"', page)
            if t:
                item["title"] = html.unescape(t.group(1))
        except Exception as e:
            item["err"] = str(e)[:60]
        out.append(item)
    return out


# ---------- 시청 지속(이탈률) ----------

def retention_stats():
    """유튜브 스튜디오에서 읽어 retention.json 에 적어 둔 값을 불러옵니다.

    Analytics API 연동 전까지는 사람이 채워 넣는 방식입니다.
    수집일을 같이 보여주므로 오래된 값을 최신인 것처럼 읽을 일은 없습니다.
    """
    d = load_json(HERE / "retention.json", {})
    rows = []
    for vid, v in (d.get("영상") or {}).items():
        pct = v.get("끝까지본비율")
        rows.append({
            "id": vid,
            "title": v.get("제목", vid),
            "sec": v.get("길이초"),
            "published": v.get("발행일", ""),
            "finish": pct,
            "bounce": None if pct is None else round(100 - pct, 1),
            "avg_sec": v.get("평균시청초"),
        })
    rows.sort(key=lambda r: r["published"])
    return {"collected": d.get("수집일", ""), "rows": rows}


# ---------- 발행 이력 ----------

def upload_history():
    if not LOG.exists():
        return {"total": 0, "by_platform": {}, "recent": []}
    rows = list(csv.DictReader(open(LOG, encoding="utf-8-sig")))
    by = Counter(r.get("플랫폼", "?") for r in rows)
    fails = [r for r in rows if "실패" in (r.get("결과") or "")]
    return {"total": len(rows), "by_platform": dict(by),
            "fails": len(fails), "recent": rows[-8:][::-1]}


# ---------- HTML ----------

CSS = """
:root{--bg:#faf9fb;--card:#fff;--ink:#1a1620;--sub:#6b6478;--line:#e6e2ea;--pt:#7c3aed;--ok:#16a34a;--warn:#d97706}
@media(prefers-color-scheme:dark){:root{--bg:#131019;--card:#1c1826;--ink:#f0edf5;--sub:#9a92a8;--line:#2c2637;--pt:#c4a8ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Malgun Gothic","맑은 고딕",system-ui,sans-serif;padding:28px 18px 70px}
.wrap{max-width:860px;margin:0 auto}
h1{font-size:1.7rem;margin:0 0 6px}
.date{color:var(--sub);margin-bottom:26px}
h2{font-size:1.15rem;margin:34px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .n{font-size:1.8rem;font-weight:700;color:var(--pt)}
.card .l{color:var(--sub);font-size:.85rem;margin-top:2px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:11px 13px;text-align:left;border-bottom:1px solid var(--line);font-size:.92rem;vertical-align:top}
th{background:rgba(124,58,237,.07);font-weight:600}
tr:last-child td{border-bottom:none}
.num{text-align:right;font-variant-numeric:tabular-nums}
.post{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px;margin-bottom:11px}
.post .meta{color:var(--sub);font-size:.83rem;margin-bottom:7px}
.post .body{white-space:pre-wrap;margin-bottom:9px}
.stat{display:inline-block;margin-right:14px;font-size:.9rem}
.stat b{color:var(--pt)}
.reply{background:rgba(124,58,237,.08);border-left:3px solid var(--pt);padding:9px 12px;border-radius:0 8px 8px 0;margin-top:9px;font-size:.9rem}
.note{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:0 10px 10px 0;padding:13px 16px;margin:12px 0}
a{color:var(--pt)}
.sub{color:var(--sub);font-size:.88rem}
"""


def esc(s):
    return html.escape(str(s or ""))


def build_html(th, yt, hist, ret, today):
    P = []
    A = P.append
    A(f"<h1>집가 마케팅 리포트</h1><div class='date'>{today}</div>")

    tv = sum(p["views"] for p in th["posts"]) if th.get("ok") else 0
    yv = sum(v["views"] or 0 for v in yt)
    rep = sum(p["replies"] for p in th["posts"]) if th.get("ok") else 0
    A("<div class='cards'>")
    for n, l in [(yv + tv, "총 조회수"), (yv, "유튜브"), (tv, "쓰레드"),
                 (rep, "받은 답글"), (hist["total"], "발행 기록")]:
        A(f"<div class='card'><div class='n'>{n:,}</div><div class='l'>{l}</div></div>")
    A("</div>")

    # 유튜브
    A("<h2>유튜브</h2>")
    if yt:
        A("<table><tr><th>영상</th><th class='num'>조회수</th></tr>")
        for v in yt:
            title = esc(v["title"] or v["id"])
            views = f"{v['views']:,}" if v["views"] is not None else "확인 실패"
            A(f"<tr><td><a href='{v['link']}' target='_blank'>{title}</a></td>"
              f"<td class='num'>{views}</td></tr>")
        A("</table>")
        A("<div class='note'>좋아요·구독 전환은 유튜브 스튜디오에서만 볼 수 있습니다. "
          "<a href='https://studio.youtube.com/' target='_blank'>스튜디오 열기</a></div>")

    else:
        A("<div class='note'>추적할 영상이 없습니다. <code>reports\tracked.json</code> 에 영상 ID를 넣으세요.</div>")

    # 시청 지속 / 이탈률
    A("<h2>시청 지속 · 이탈률 <span class='sub'>유튜브 쇼츠</span></h2>")
    if not ret["rows"]:
        A("<div class='note'>retention.json 이 비어 있습니다.</div>")
    else:
        A("<table><tr><th>영상</th><th class='num'>길이</th>"
          "<th class='num'>끝까지 봤어요</th><th class='num'>이탈률</th>"
          "<th class='num'>평균 시청</th></tr>")
        for r in ret["rows"]:
            if r["finish"] is None:
                cells = ("<td class='num' colspan='3' style='opacity:.55'>"
                         f"{esc(r['published'])} 발행 예정 — 데이터 없음</td>")
            else:
                cells = (f"<td class='num'>{r['finish']}%</td>"
                         f"<td class='num'><b>{r['bounce']}%</b></td>"
                         f"<td class='num'>{r['avg_sec'] // 60}:{r['avg_sec'] % 60:02d}</td>")
            dur = f"{r['sec']}초" if r["sec"] else "-"
            A(f"<tr><td>{esc(r['title'])}</td><td class='num'>{dur}</td>{cells}</tr>")
        A("</table>")
        A(f"<div class='note'>수집일 <b>{esc(ret['collected'])}</b> · "
          "유튜브 스튜디오에서 직접 읽은 값입니다. 자동 수집하려면 YouTube Analytics API 연동이 필요합니다.<br>"
          "쓰레드는 텍스트 글이라 이탈률 개념이 없고, 인스타 릴스는 평균 시청 시간까지만 제공합니다.</div>")

    # 쓰레드
    A("<h2>쓰레드</h2>")
    if not th.get("ok"):
        A(f"<div class='note'>{esc(th.get('why'))}</div>")
    else:
        A(f"<div class='sub'>@{esc(th['username'])} · 글 {len(th['posts'])}개</div>")
        for p in th["posts"]:
            A("<div class='post'>")
            A(f"<div class='meta'>{esc(p['when'])} · <a href='{p['link']}' target='_blank'>글 보기</a></div>")
            body = p["text"][:220] + ("…" if len(p["text"]) > 220 else "")
            A(f"<div class='body'>{esc(body)}</div>")
            A(f"<span class='stat'>조회 <b>{p['views']:,}</b></span>"
              f"<span class='stat'>좋아요 <b>{p['likes']}</b></span>"
              f"<span class='stat'>답글 <b>{p['replies']}</b></span>"
              f"<span class='stat'>리포스트 <b>{p['reposts']}</b></span>")
            for r in p["reply_list"]:
                A(f"<div class='reply'><b>@{esc(r['who'])}</b><br>{esc(r['text'])}</div>")
            A("</div>")

    # 인스타
    A("<h2>인스타그램</h2>")
    A("<div class='note'>API가 아직 연결되지 않아 자동 수집이 안 됩니다.<br>"
      "인스타 앱 → 릴스 → <b>인사이트</b> 에서 조회수·좋아요·저장수를 확인하세요.<br>"
      "연결 방법은 <code>uploader\\마케팅자동화 설명서.md</code> 4장에 있습니다.</div>")

    # 발행 이력 — 안 올린 채널도 0으로 보여줘야 오해가 없습니다
    A("<h2>발행 이력</h2>")
    A("<div class='sub'>실제로 발행한 것만 셉니다. 테스트 실행은 기록되지 않습니다.</div>")
    A("<div class='cards'>")
    all_ch = ["유튜브", "인스타그램", "쓰레드", "네이버 블로그", "티스토리"]
    for k in all_ch:
        v = hist["by_platform"].get(k, 0)
        A(f"<div class='card'><div class='n'>{v}</div><div class='l'>{esc(k)}"
          + ("" if v else " <span style='color:var(--warn)'>미발행</span>") + "</div></div>")
    A("</div>")
    if hist.get("fails"):
        A(f"<div class='note'>실패 {hist['fails']}건이 있습니다. uploads_log.csv 를 확인하세요.</div>")
    else:
        A("<div class='sub'>실패 0건</div>")

    # 측정 안 되는 것
    A("<h2>아직 측정 못 하는 것</h2>")
    A("<table><tr><th>항목</th><th>필요한 것</th></tr>"
      "<tr><td>링크 클릭수</td><td>링크에 UTM 파라미터 + 사이트에 Vercel Analytics 켜기</td></tr>"
      "<tr><td>인스타 지표</td><td>인스타 API 연결 (앱 검수 필요)</td></tr>"
      "<tr><td>유튜브 상세 지표</td><td>유튜브 스튜디오에서 직접 확인</td></tr></table>")

    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            f"<title>집가 마케팅 리포트 {today}</title><style>{CSS}</style></head>"
            f"<body><div class='wrap'>{''.join(P)}</div></body></html>")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = datetime.date.today().isoformat()

    cfg = load_json(CONFIG, {})
    tracked = load_json(TRACKED, {"youtube": []})

    log("쓰레드 지표 수집 중...")
    th = threads_stats(cfg)
    log("  " + ("완료" if th.get("ok") else "건너뜀 — " + th.get("why", "")))

    log("유튜브 조회수 수집 중...")
    yt = youtube_stats(tracked.get("youtube", []))
    log(f"  영상 {len(yt)}개")

    hist = upload_history()
    log(f"발행 기록 {hist['total']}건 (실패 {hist.get('fails', 0)})")

    out = HERE / f"리포트_{today}.html"
    out.write_text(build_html(th, yt, hist, retention_stats(), today), encoding="utf-8")
    log(f"\n=== 완성 ===\n  {out}")
    try:
        webbrowser.open(out.as_uri())
    except Exception:
        pass


if __name__ == "__main__":
    main()
