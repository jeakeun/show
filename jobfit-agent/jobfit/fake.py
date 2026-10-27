"""가짜 모델. API 키 없이 흐름을 시험할 때 쓴다 (--dry-run, 테스트).

진짜 모델과 같은 함수(analyze / write / verify / baseline)를 갖고 있어서 그래프에 그대로 끼워진다.
"""
import re


class FakeLLM:
    def __init__(self, drafts: list[str] | None = None, verdicts: list[list[dict]] | None = None):
        self.drafts = list(drafts or [])       # 정해진 초안을 차례로 돌려줌 (없으면 근거로 자동 생성)
        self.verdicts = list(verdicts or [])   # 정해진 검증 결과를 차례로 돌려줌 (없으면 문제 없음)
        self.calls: list[dict] = []

    def analyze(self, posting: str) -> dict:
        self.calls.append({"role": "analyzer"})
        reqs, kind = [], "담당"
        for line in posting.splitlines():
            line = line.strip()
            if not line.startswith(("-", "•")):
                if "우대" in line:
                    kind = "우대"
                elif "자격" in line or "필수" in line:
                    kind = "필수"
                elif "스킬" in line:
                    kind = "스킬"
                continue
            text = line.lstrip("-• ").strip()
            if not text or "기타" in text:
                continue
            skills = re.findall(r"[A-Za-z][A-Za-z ]*[A-Za-z]|RAG", text)
            reqs.append({"id": f"R{len(reqs) + 1}", "kind": kind, "text": text,
                         "skills": [s.strip() for s in skills][:5]})
        company = {"business_model": "가짜 모델이라 알 수 없음", "company_type": "기타", "key_metrics": [],
                   "weak_metrics": [], "basis": [], "confidence": "낮음"}
        return {"requirements": reqs, "company": company}

    def write(self, posting: str, fit_table: str, sources: dict, feedback: str = "", company: dict | None = None,
              previous: str = "") -> str:
        self.calls.append({"role": "writer", "feedback": bool(feedback), "company": company, "previous": previous})
        if self.drafts:
            return self.drafts.pop(0)
        lines = ["## 자기소개서"]
        for eid in sorted(sources, key=lambda e: int(e[1:]))[:3]:
            c = sources[eid]
            lines.append(f"{c['section'] or c['source']} 관련 경험이 있습니다 [{eid}].")
        lines += ["", "## 이력서 강조"] + [f"- {sources[e]['section']} [{e}]." for e in list(sources)[:3]]
        lines += ["", "## 보강할 증거", "- 이 회사 지표로 말할 숫자가 부족함"]
        return "\n".join(lines)

    def verify(self, draft: str, sources: dict, company: dict | None = None) -> list[dict]:
        self.calls.append({"role": "verifier"})
        return self.verdicts.pop(0) if self.verdicts else []

    def baseline(self, posting: str, sources: dict) -> str:
        self.calls.append({"role": "baseline"})
        return self.write(posting, "", sources)

    def cost_summary(self) -> str:
        return f"가짜 모델: 호출 {len(self.calls)}번 (비용 없음)"
