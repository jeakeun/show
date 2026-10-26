# -*- coding: utf-8 -*-
"""사람이 영상 사이트(config video_tool)에서 따라 할 작업지시서(HTML)를 만든다. 복사 버튼·참고 이미지·체크박스."""
import html
import os
from pathlib import Path

from common import CONFIG, SERIES_DIR

CSS = """
:root{--bg:#fafaf7;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--line:#e4e2dc;--acc:#d9480f}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mut:#a3a29c;--card:#201f1d;--line:#34332f;--acc:#ff8a4c}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 "Malgun Gothic",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:24px;margin:0 0 4px}.mut{color:var(--mut)}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}
.shot{display:grid;grid-template-columns:auto 1fr;gap:12px}
.no{font-size:28px;font-weight:700;color:var(--acc);min-width:44px}
textarea{width:100%;box-sizing:border-box;min-height:120px;font:13px/1.5 Consolas,monospace;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:8px 14px;font-size:15px;cursor:pointer}
.refs{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}.refs figure{margin:0;text-align:center;font-size:12px}
.refs img{width:72px;height:96px;object-fit:cover;border-radius:6px;border:1px solid var(--line)}
.missing{width:72px;height:96px;display:flex;align-items:center;justify-content:center;border:1px dashed var(--acc);border-radius:6px;font-size:11px;color:var(--acc)}
label{cursor:pointer}.done{opacity:.45}
ol li{margin:4px 0}
"""

JS = """
const KEY=location.pathname;
function cp(id,btn){navigator.clipboard.writeText(document.getElementById(id).value);btn.textContent='복사됨 ✓';setTimeout(()=>btn.textContent='프롬프트 복사',1500)}
function mark(cb){cb.closest('.box').classList.toggle('done',cb.checked);try{const s=JSON.parse(localStorage.getItem(KEY)||'{}');s[cb.id]=cb.checked;localStorage.setItem(KEY,JSON.stringify(s))}catch(e){}}
window.onload=()=>{try{const s=JSON.parse(localStorage.getItem(KEY)||'{}');for(const k in s){const c=document.getElementById(k);if(c&&s[k]){c.checked=true;mark(c)}}}catch(e){}}
"""


def _ref_html(char_ids: list[str], names: dict, base: Path) -> str:
    out = []
    for cid in char_ids:
        img = SERIES_DIR / "characters" / f"{cid}.png"
        nm = html.escape(names.get(cid, cid))
        if img.exists():
            rel = os.path.relpath(img, base).replace("\\", "/")
            out.append(f'<figure><img src="{rel}"><figcaption>{nm}</figcaption></figure>')
        else:
            out.append(f'<figure><div class="missing">사진 없음</div><figcaption>{nm}</figcaption></figure>')
    return f'<div class="refs">{"".join(out)}</div>' if out else ""


def _page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head>'
            f'<body><main>{body}</main><script>{JS}</script></body></html>')


def episode_sheet(bible: dict, n: int, ep: dict, folder: Path) -> Path:
    names = {c["id"]: c["name"] for c in bible["characters"]}
    total = sum(s["seconds"] for s in ep["shots"])
    tool = CONFIG.get("video_tool", {})
    site = html.escape(tool.get("site", "영상 사이트"))
    model = html.escape(tool.get("model", "영상 모델"))
    res = html.escape(tool.get("resolution", "720p"))
    payoff = f"<br><b>보상</b>: {html.escape(ep['payoff'])}" if ep.get("payoff") else ""
    head = f"""<h1>{n}화 「{html.escape(ep['title'])}」</h1>
<p class="mut">{html.escape(bible['title'])} · 장면 {len(ep['shots'])}개 · 약 {total}초</p>
<div class="box"><b>순서</b><ol>
<li>{site} → <b>Video</b> → 모델 <b>{model}</b> → <b>Unlimited(무제한) 스위치가 있으면 켜기</b> (안 켜면 크레딧이 깎입니다)</li>
<li>화면 비율 <b>9:16</b>, 화질 <b>{res}</b>, 길이는 장면마다 적힌 초로 맞추기</li>
<li>장면 옆의 인물 사진을 참고 이미지(캐릭터·Elements 등)로 넣고 → 「프롬프트 복사」 → 붙여넣기 → 생성</li>
<li>마음에 들면 다운로드. <b>1번 장면부터 순서대로</b> 받으세요. 이상하면 다시 생성</li>
<li>다 받았으면 <b>2_영상가져오기.bat</b> → <b>3_편집하기.bat</b></li></ol>
<p class="mut">중간에 한 장면만 다시 받았을 때: 2_영상가져오기.bat 대신 명령창에서 <code>python drama.py collect --shot 3</code></p></div>
<div class="box"><b>줄거리</b><br>{html.escape(ep['summary'])}{payoff}<br><span class="mut">끝 5초 떡밥: {html.escape(ep['cliffhanger'])}</span></div>"""
    shots = []
    for i, s in enumerate(ep["shots"], 1):
        lines = "<br>".join(f"<b>{html.escape(names.get(d['speaker'], d['speaker']))}</b>: {html.escape(d['line'])}"
                            for d in s["dialogue"])
        shots.append(f"""<div class="box"><div class="shot"><div class="no">{i}</div><div>
<label><input type="checkbox" id="s{i}" onchange="mark(this)"> <b>{s['seconds']}초</b> · {html.escape(s['action_ko'])}</label>
{_ref_html(s['character_ids'], names, folder)}
{f'<p>{lines}</p>' if lines else ''}
<textarea id="p{i}" readonly>{html.escape(s['prompt_en'])}</textarea>
<button onclick="cp('p{i}',this)">프롬프트 복사</button></div></div></div>""")
    path = folder / "작업지시서.html"
    path.write_text(_page(f"{n}화 작업지시서", head + "".join(shots)), encoding="utf-8")
    return path


def character_sheet(bible: dict) -> Path:
    folder = SERIES_DIR
    style = bible["visual_style_en"]
    head = f"""<h1>{html.escape(bible['title'])} — 인물 사진 만들기 (처음 한 번만)</h1>
<p class="mut">{html.escape(bible['logline'])}</p>
<div class="box"><b>왜 하나요?</b> AI 영상은 매번 얼굴이 조금씩 달라집니다. 인물마다 기준 사진을 한 장 정해 두고
모든 장면에 같이 넣으면 같은 사람으로 유지됩니다.<ol>
<li>제미나이 앱(gemini.google.com) 또는 {html.escape(CONFIG.get('video_tool', {}).get('site', '이미지 사이트'))}의 이미지 생성 → 비율 3:4</li>
<li>아래 프롬프트 복사 → 생성 → 가장 마음에 드는 한 장 다운로드</li>
<li>받은 사진을 <code>webdrama\\series\\characters\\</code> 폴더에 <b>영문 이름.png</b> 로 저장 (예: <code>{html.escape(bible['characters'][0]['id'])}.png</code>)</li>
<li>다 넣고 이 페이지를 새로고침하면 사진이 보입니다</li></ol></div>"""
    cards = []
    for i, c in enumerate(bible["characters"], 1):
        prompt = (f"{style}. Character reference portrait, front-facing, upper body, plain light grey background, "
                  f"natural expression, sharp focus on face. {c['look_en']}. {c['outfit_en']}.")
        cards.append(f"""<div class="box"><div class="shot"><div>{_ref_html([c['id']], {c['id']: c['id'] + '.png'}, folder)}</div><div>
<label><input type="checkbox" id="c{i}" onchange="mark(this)"> <b>{html.escape(c['name'])}</b> ({c['age']}세, {html.escape(c['role'])})</label>
<p class="mut">{html.escape(c['personality'])}</p>
<textarea id="p{i}" readonly>{html.escape(prompt)}</textarea>
<button onclick="cp('p{i}',this)">프롬프트 복사</button></div></div></div>""")
    path = folder / "인물사진_만들기.html"
    (folder / "characters").mkdir(parents=True, exist_ok=True)
    path.write_text(_page("인물 사진 만들기", head + "".join(cards)), encoding="utf-8")
    return path
