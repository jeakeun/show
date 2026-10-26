"""평가: 공고 분석가 결과를 정답표와 비교한다 (설계 결정 J-15).

- 요구 항목: 재현율(정답 중 몇 개를 찾았나) · 정밀도(낸 것 중 몇 개가 정답인가). 5교시 계산 그대로.
- 회사 읽기: 멘토가 해석한 공고에서 회사 유형이 같은가. 중요 지표는 나란히 놓고 사람이 본다.

짝 맞추기 규칙 (단순하고 설명 가능하게):
  정답 항목과 낸 항목이 기술 키워드를 하나라도 공유하거나, 글자 두 개씩 조각의 겹침(자카드)이 0.3 이상이면 같은 항목으로 본다.
  한 항목은 한 번만 짝지어진다. 한계: 같은 뜻을 다른 말로 쓰면 놓칠 수 있어, 숫자와 함께 놓친 항목 목록을 사람이 확인한다.
"""


def _norm(s: str) -> str:
    return "".join(str(s).lower().split())


def _bigrams(s: str) -> set:
    n = _norm(s)
    return {n[i:i + 2] for i in range(len(n) - 1)}


def _jaccard(a: str, b: str) -> float:
    x, y = _bigrams(a), _bigrams(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def _shares_skill(g: dict, p: dict) -> bool:
    gs = {_norm(s) for s in g.get("skills") or [] if _norm(s)}
    ps = {_norm(s) for s in p.get("skills") or [] if _norm(s)}
    return any(a == b or (len(a) > 2 and len(b) > 2 and (a in b or b in a)) for a in gs for b in ps)


def similarity(g: dict, p: dict) -> float:
    j = _jaccard(g.get("text", ""), p.get("text", ""))
    return max(j, 0.5) if _shares_skill(g, p) else j


def match_requirements(gold: list[dict], pred: list[dict], threshold: float = 0.3):
    pairs = sorted(((similarity(g, p), gi, pi) for gi, g in enumerate(gold) for pi, p in enumerate(pred)), reverse=True)
    used_g, used_p, matches = set(), set(), []
    for sim, gi, pi in pairs:
        if sim < threshold:
            break
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        matches.append((gold[gi], pred[pi], round(sim, 2)))
    missed = [g for i, g in enumerate(gold) if i not in used_g]
    extra = [p for i, p in enumerate(pred) if i not in used_p]
    return matches, missed, extra


def requirement_scores(gold: list[dict], pred: list[dict]) -> dict:
    matches, missed, extra = match_requirements(gold, pred)
    return {
        "recall": len(matches) / len(gold) if gold else None,
        "precision": len(matches) / len(pred) if pred else None,
        "matched": len(matches), "gold": len(gold), "pred": len(pred),
        "missed": [g["text"] for g in missed], "extra": [p["text"] for p in extra],
    }


def company_type_hit(answer: dict, company: dict):
    """멘토 라벨이 있는 공고만 채점한다. 라벨이 없으면 None."""
    label = (answer.get("mentor_reading") or {}).get("company_type")
    if not label:
        return None
    return (company or {}).get("company_type") == label


def pct(x) -> str:
    return "-" if x is None else f"{round(100 * x)}%"
