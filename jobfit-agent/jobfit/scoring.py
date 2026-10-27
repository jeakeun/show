"""적합도 계산 (코드). 숫자는 AI가 아니라 여기서 만든다 (설계 결정 J-04).

규칙:
- 요구 항목의 기술 키워드가 근거 조각 본문에 실제로 나오는지 본다.
- 키워드가 "운영" 문서에서 나오면 운영 근거, "학습" 문서에서만 나오면 학습 근거, 어디에도 없으면 근거 없음.
- 한계: 키워드가 나와도 "아직 안 해봤다"는 문맥일 수 있다. 그건 검증가가 잡고, 평가셋으로 정확도를 잰다.
- 2-2 (2026-10-27): 키워드는 동의어까지 본다 (Python → 파이썬, .py). 영어 키워드는 단어 경계로 찾는다 (GA ≠ ZipGa).
"""
from . import words

WEIGHT = {"담당": 2, "필수": 2, "우대": 1, "스킬": 1}
CREDIT = {"운영": 1.0, "학습": 0.5, "없음": 0.0}


def _found(skill: str, text: str, match_words: bool) -> bool:
    if not match_words:
        return skill.lower() in text.lower()      # 2-1 단계 방식 (비교용)
    return any(words.contains(text, v) for v in words.variants(skill))


def judge(requirement: dict, chunks: list[dict], match_words: bool = True) -> dict:
    skills = requirement.get("skills") or []
    found_in: dict[str, set] = {}
    for s in skills:
        kinds = {c["kind"] for c in chunks if _found(s, c["text"], match_words)}
        if kinds:
            found_in[s] = kinds
    if skills:
        all_kinds = set().union(*found_in.values()) if found_in else set()
    else:
        # 키워드가 없는 항목은 검색 결과가 있는지만 본다. 이 규칙이 적합도를 흔드는 문제는 2-3에서 고친다.
        # 그 전까지는 종류별로 더 붙인 조각(extra)은 빼고 상위 k개만 봐서, 검색 개선 때문에 더 부풀지 않게 한다.
        all_kinds = {c["kind"] for c in chunks if not c.get("extra")}
    status = "운영" if "운영" in all_kinds else "학습" if "학습" in all_kinds else "없음"
    return {
        "id": requirement["id"],
        "kind": requirement["kind"],
        "text": requirement["text"],
        "status": status,
        "matched": sorted(found_in),
        "matched_kinds": {s: ("운영" if "운영" in k else "학습") for s, k in sorted(found_in.items())},
        "missing": [s for s in skills if s not in found_in],
    }


def number_sources(found: list[dict], order: dict | None = None):
    """검색 결과 조각에 근거 번호(E1, E2 …)를 붙인다. 돌려주는 것: (번호→조각, 요구 항목→후보 번호 목록)."""
    order = order or {}
    sources, chunk_to_eid, candidates = {}, {}, {}
    for item in sorted(found, key=lambda f: order.get(f["req"]["id"], 0)):
        for c in item["chunks"]:
            if c["id"] not in chunk_to_eid:
                eid = f"E{len(sources) + 1}"
                chunk_to_eid[c["id"]] = eid
                sources[eid] = c
        candidates[item["req"]["id"]] = [chunk_to_eid[c["id"]] for c in item["chunks"]]
    return sources, candidates


def apply_judgments(judged: list[dict], candidates: dict, sources: dict, ai: list[dict]) -> list[dict]:
    """AI 근거 판정을 코드가 검사해 받아들인다 (2-3). AI는 해석, 코드는 검사 (ADR-04와 같은 원칙).
    - 근거 번호는 그 항목의 검색 후보 안에 있는 것만 인정한다.
    - "운영"인데 운영 조각 번호가 없으면 학습(근거가 있으면) 또는 없음으로 낮춘다. "학습"인데 번호가 없으면 없음.
    - AI가 판정하지 않은 항목은 키워드 판정을 그대로 쓴다.
    """
    by_id = {a.get("id"): a for a in ai}
    out = []
    for j in judged:
        j = {**j, "keyword_status": j["status"]}
        a = by_id.get(j["id"])
        if not a:
            out.append({**j, "basis": "키워드"})
            continue
        allowed = set(candidates.get(j["id"]) or [])
        ev = [e for e in a.get("evidence") or [] if e in allowed]
        kinds = {sources[e]["kind"] for e in ev}
        said = a.get("status") if a.get("status") in CREDIT else "없음"
        status = said
        if status == "운영" and "운영" not in kinds:
            status = "학습" if ev else "없음"
        if status == "학습" and not ev:
            status = "없음"
        out.append({**j, "status": status, "evidence": ev if status != "없음" else [], "reason": a.get("reason", ""),
                    "basis": "AI", "lowered": status != said})
    return out


def overall(judged: list[dict]) -> int:
    """가중 평균 적합도 (0~100). 담당·필수는 2배 가중."""
    total = sum(WEIGHT.get(j["kind"], 1) for j in judged)
    if total == 0:
        return 0
    got = sum(WEIGHT.get(j["kind"], 1) * CREDIT[j["status"]] for j in judged)
    return round(100 * got / total)


def fit_table(judged: list[dict]) -> str:
    rows = ["| 항목 | 구분 | 요구 | 근거 | 근거 번호 | 찾은 키워드 | 못 찾은 키워드 | 판정 이유 |",
            "|---|---|---|---|---|---|---|---|"]
    for j in judged:
        # 키워드마다 어느 종류 문서에서 찾았는지 붙인다. "LLM(운영), LangChain(학습)" — 작성자가 학습을 운영처럼 쓰지 않게
        kinds = j.get("matched_kinds") or {}
        found = ", ".join(f"{s}({kinds[s]})" if s in kinds else s for s in j["matched"])
        status = j["status"] + (" (코드가 낮춤)" if j.get("lowered") else "")
        reason = (j.get("reason") or "").replace("|", "/") or ("키워드 판정" if j.get("basis") != "AI" else "-")
        rows.append(f"| {j['id']} | {j['kind']} | {j['text']} | {status} | {', '.join(j.get('evidence') or []) or '-'} | "
                    f"{found or '-'} | {', '.join(j['missing']) or '-'} | {reason} |")
    return "\n".join(rows)
