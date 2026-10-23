"""가짜 모델. API 키 없이 흐름을 시험할 때 쓴다 (--dry-run, 테스트).

진짜 모델과 같은 함수(analyze / write / verify / baseline)를 갖고 있어서 그래프에 그대로 끼워진다.
"""
import re


class FakeLLM:
    def __init__(self, drafts: list[str] | None = None, verdicts: list[list[dict]] | None = None):
        self.drafts = list(drafts or [])       # 정해진 초안을 차례로 돌려줌 (없으면 근거로 자동 생성)
        self.verdicts = list(verdicts or [])   # 정해진 검증 결과를 차례로 돌려줌 (없으면 문제 없음)
        self.calls: list[dict] = []

    def analyze(self, posting: str) -> list[dict]:
        self.calls.append({"role": "analyzer"})
        reqs, kind = [], "담당"
        for line in posting.splitlines():
            line = line.strip()
            if "우대" in line and not line.startswith("-"):
                kind = "우대"
            elif "스킬" in line and not line.startswith("-"):
                kind = "스킬"
            elif line.startswith("-") and "기타" not in line:
                text = line.lstrip("- ").strip()
                skills = re.findall(r"[A-Za-z][A-Za-z ]*[A-Za-z]|RAG", text)
                reqs.append({"id": f"R{len(reqs) + 1}", "kind": kind, "text": text,
                             "skills": [s.strip() for s in skills][:5]})
        return reqs

    def write(self, posting: str, fit_table: str, sources: dict, feedback: str = "") -> str:
        self.calls.append({"role": "writer", "feedback": bool(feedback)})
        if self.drafts:
            return self.drafts.pop(0)
        lines = ["## 자기소개서"]
        for eid in sorted(sources, key=lambda e: int(e[1:]))[:3]:
            c = sources[eid]
            lines.append(f"{c['section'] or c['source']} 관련 경험이 있습니다 [{eid}].")
        lines += ["", "## 이력서 강조"] + [f"- {sources[e]['section']} [{e}]." for e in list(sources)[:3]]
        return "\n".join(lines)

    def verify(self, draft: str, sources: dict) -> list[dict]:
        self.calls.append({"role": "verifier"})
        return self.verdicts.pop(0) if self.verdicts else []

    def baseline(self, posting: str, sources: dict) -> str:
        self.calls.append({"role": "baseline"})
        return self.write(posting, "", sources)

    def cost_summary(self) -> str:
        return f"가짜 모델: 호출 {len(self.calls)}번 (비용 없음)"
