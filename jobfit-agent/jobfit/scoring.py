"""적합도 계산 (코드). 숫자는 AI가 아니라 여기서 만든다 (설계 결정 J-04).

규칙:
- 요구 항목의 기술 키워드가 근거 조각 본문에 실제로 나오는지 본다.
- 키워드가 "운영" 문서에서 나오면 운영 근거, "학습" 문서에서만 나오면 학습 근거, 어디에도 없으면 근거 없음.
- 한계: 키워드가 나와도 "아직 안 해봤다"는 문맥일 수 있다. 그건 검증가가 잡고, 평가셋으로 정확도를 잰다.
"""
WEIGHT = {"담당": 2, "필수": 2, "우대": 1, "스킬": 1}
CREDIT = {"운영": 1.0, "학습": 0.5, "없음": 0.0}


def judge(requirement: dict, chunks: list[dict]) -> dict:
    skills = requirement.get("skills") or []
    found_in: dict[str, set] = {}
    for s in skills:
        kinds = {c["kind"] for c in chunks if s.lower() in c["text"].lower()}
        if kinds:
            found_in[s] = kinds
    if skills:
        all_kinds = set().union(*found_in.values()) if found_in else set()
    else:
        all_kinds = {c["kind"] for c in chunks}   # 키워드가 없는 항목은 검색 결과가 있는지만 본다
    status = "운영" if "운영" in all_kinds else "학습" if "학습" in all_kinds else "없음"
    return {
        "id": requirement["id"],
        "kind": requirement["kind"],
        "text": requirement["text"],
        "status": status,
        "matched": sorted(found_in),
        "missing": [s for s in skills if s not in found_in],
    }


def overall(judged: list[dict]) -> int:
    """가중 평균 적합도 (0~100). 담당·필수는 2배 가중."""
    total = sum(WEIGHT.get(j["kind"], 1) for j in judged)
    if total == 0:
        return 0
    got = sum(WEIGHT.get(j["kind"], 1) * CREDIT[j["status"]] for j in judged)
    return round(100 * got / total)


def fit_table(judged: list[dict]) -> str:
    rows = ["| 항목 | 구분 | 요구 | 근거 | 찾은 키워드 | 못 찾은 키워드 |", "|---|---|---|---|---|---|"]
    for j in judged:
        rows.append(f"| {j['id']} | {j['kind']} | {j['text']} | {j['status']} | "
                    f"{', '.join(j['matched']) or '-'} | {', '.join(j['missing']) or '-'} |")
    return "\n".join(rows)
