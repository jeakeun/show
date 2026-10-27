"""근거 검색 채점 (2-2 단계). 모델을 부르지 않는다 → 비용 없음.

정답 요구 항목(answers/NNN.json)마다 검색가와 적합도 계산만 돌려서, 정답 근거(evidence.json)와 비교한다.
공고 분석가의 흔들림과 섞이지 않게, 분석가가 뽑은 항목이 아니라 사람이 만든 정답 항목을 쓴다.

잴 것
- 운영 근거 적중: 정답이 "운영"인 항목에서, 정답으로 적은 운영 문서 절이 검색 결과에 하나라도 들어왔나
- 학습 근거 적중: 정답 학습 근거가 있는 항목에서, 그 절이 하나라도 들어왔나 (운영을 찾느라 학습을 놓치면 안 됨)
- 판정 일치: 코드 판정(운영/학습/없음)이 정답과 같은가
- 부풀림: 정답보다 높게 판정 (없음→학습·운영, 학습→운영). 지어낸 경력의 씨앗이라 가장 중요
- 깎임: 정답보다 낮게 판정
- 조각 수: 항목당 근거 조각 수, 공고당 서로 다른 조각 수 (작성자에게 가는 글 양 = 비용)
- 적합도 차이: 정답 판정으로 계산한 적합도와 코드 판정 적합도의 차이 (공고별 평균)
"""
import json
from dataclasses import replace
from pathlib import Path

from . import scoring
from .career import Retriever, load_career
from .config import ROOT, Config
from .graph import find_evidence

RANK = {"없음": 0, "학습": 1, "운영": 2}

# (이름, 설정). 위에서부터 하나씩 켠다. "종류별 검색만"은 문서 정리 없이 넓히기만 하면 어떻게 되는지 보여준다.
VARIANTS = [
    ("2-1 방식", dict(clean_sources=False, match_words=False, per_kind=0)),
    ("종류별 검색만", dict(clean_sources=False, match_words=False, per_kind=2)),
    ("① 근거 아닌 부분 빼기", dict(clean_sources=True, match_words=False, per_kind=0)),
    ("①+② 말 맞추기", dict(clean_sources=True, match_words=True, per_kind=0)),
    ("①+②+③ 종류별 1개", dict(clean_sources=True, match_words=True, per_kind=1)),
    ("①+②+③ 종류별 2개 (지금 설정)", dict(clean_sources=True, match_words=True, per_kind=2)),
]


def load_gold(root: Path = ROOT / "eval") -> list[dict]:
    labels = json.loads((root / "evidence.json").read_text(encoding="utf-8"))["labels"]
    items = []
    for pid, by_req in sorted(labels.items()):
        answer = json.loads((root / "answers" / f"{pid}.json").read_text(encoding="utf-8"))
        for req in answer["requirements"]:
            if req["id"] in by_req:
                items.append({"posting": pid, "req": req, "gold": by_req[req["id"]]})
    return items


def matches(chunk: dict, ref: str) -> bool:
    """근거 위치 "문서#절 제목에 든 말" 이 이 조각인가. 문서는 README 또는 번호(02, 03 …)."""
    doc, _, section = ref.partition("#")
    stem = Path(chunk["source"]).stem
    same_doc = stem == doc if doc == "README" else stem.startswith(doc + "-")
    return same_doc and section in chunk["section"]


def hit(chunks: list[dict], refs: list[str]) -> bool:
    return any(matches(c, r) for c in chunks for r in refs)


def run_variant(cfg: Config, gold: list[dict]) -> dict:
    retriever = Retriever(load_career(cfg), cfg.match_words)
    rows = []
    for g in gold:
        found = find_evidence(retriever, cfg, g["req"])
        j = scoring.judge(g["req"], found["chunks"], cfg.match_words)
        rows.append({**g, "chunks": found["chunks"], "judged": j})
    return {"rows": rows, **measure(rows)}


def _rate(n: int, d: int) -> str:
    return f"{n}/{d} ({round(100 * n / d)}%)" if d else "-"


def measure(rows: list[dict]) -> dict:
    ops = [r for r in rows if r["gold"]["status"] == "운영"]
    learn = [r for r in rows if r["gold"].get("학습")]
    agree = sum(r["judged"]["status"] == r["gold"]["status"] for r in rows)
    over = [r for r in rows if RANK[r["judged"]["status"]] > RANK[r["gold"]["status"]]]
    under = [r for r in rows if RANK[r["judged"]["status"]] < RANK[r["gold"]["status"]]]
    by_posting: dict[str, list[dict]] = {}
    for r in rows:
        by_posting.setdefault(r["posting"], []).append(r)
    fit_gap, uniq = [], []
    for pid, rs in by_posting.items():
        gold_fit = scoring.overall([{"kind": r["req"]["kind"], "status": r["gold"]["status"]} for r in rs])
        code_fit = scoring.overall([r["judged"] for r in rs])
        fit_gap.append((pid, gold_fit, code_fit))
        uniq.append(len({c["id"] for r in rs for c in r["chunks"]}))
    return {
        "ops_hit": sum(hit(r["chunks"], r["gold"]["운영"]) for r in ops), "ops_n": len(ops),
        "learn_hit": sum(hit(r["chunks"], r["gold"]["학습"]) for r in learn), "learn_n": len(learn),
        "agree": agree, "n": len(rows), "over": over, "under": under,
        "fake_ops": [r for r in over if r["judged"]["status"] == "운영"],
        "per_req": sum(len(r["chunks"]) for r in rows) / len(rows) if rows else 0,
        "per_posting": sum(uniq) / len(uniq) if uniq else 0,
        "fit": fit_gap,
        "fit_gap": sum(abs(a - b) for _, a, b in fit_gap) / len(fit_gap) if fit_gap else 0,
    }


def compare(variants=VARIANTS, gold: list[dict] | None = None) -> list[tuple[str, dict]]:
    gold = gold if gold is not None else load_gold()
    return [(name, run_variant(replace(Config(), **opts), gold)) for name, opts in variants]


def report(results: list[tuple[str, dict]]) -> str:
    lines = ["# 근거 검색 채점", "",
             "정답 요구 항목(사람이 만든 것)으로 검색가와 적합도 계산만 돌렸습니다. 모델 호출 없음, 비용 없음.",
             "정답 근거(eval/evidence.json)는 클로드가 검색 결과를 보기 전에 붙였고, 사람 확인이 필요합니다.", "",
             "| 방식 | 운영 근거 적중 | 학습 근거 적중 | 판정 일치 | 부풀림 (그중 가짜 운영) | 깎임 | 항목당 조각 | 공고당 조각 | 적합도 차이 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, m in results:
        lines.append(f"| {name} | {_rate(m['ops_hit'], m['ops_n'])} | {_rate(m['learn_hit'], m['learn_n'])} | "
                     f"{_rate(m['agree'], m['n'])} | {len(m['over'])} ({len(m['fake_ops'])}) | {len(m['under'])} | "
                     f"{m['per_req']:.1f} | {m['per_posting']:.1f} | {m['fit_gap']:.1f}점 |")
    name, final = results[-1]
    lines += ["", f"## 공고별 적합도 ({name})", "", "| 공고 | 정답 판정으로 계산 | 코드 판정 |", "|---|---|---|"]
    lines += [f"| {pid} | {a} | {b} |" for pid, a, b in final["fit"]]
    lines += ["", f"## 판정이 정답과 다른 항목 ({name})", "",
              "| 공고 | 항목 | 요구 | 정답 | 코드 | 찾은 키워드 | 운영 근거 적중 |", "|---|---|---|---|---|---|---|"]
    for r in final["rows"]:
        j, gold = r["judged"], r["gold"]
        if j["status"] == gold["status"]:
            continue
        kinds = j.get("matched_kinds") or {}
        found = ", ".join(f"{s}({kinds.get(s, '')})" for s in j["matched"]) or "-"
        ops = ("O" if hit(r["chunks"], gold["운영"]) else "X") if gold["status"] == "운영" else "-"
        lines.append(f"| {r['posting']} | {r['req']['id']} | {r['req']['text'][:40]} | {gold['status']} | {j['status']} | {found} | {ops} |")
    missed = [r for r in final["rows"] if r["gold"]["status"] == "운영" and not hit(r["chunks"], r["gold"]["운영"])]
    lines += ["", f"## 운영 근거를 못 찾은 항목 ({name})", ""]
    lines += [f"- {r['posting']} {r['req']['id']} {r['req']['text'][:50]} — 정답 근거 {', '.join(r['gold']['운영'])}" for r in missed] or ["- 없음"]
    return "\n".join(lines) + "\n"
