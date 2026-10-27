"""말 맞추기: 검색 토큰, 동의어 사전, 키워드가 글에 있는지 확인 (2-2 단계, 2026-10-27).

왜 필요한가 (001 재현에서 찾은 것):
- 공고는 "LLM", "AI Agent", "Python" 이라고 쓰고 운영 문서는 "클로드", "에이전트", "파이썬", "streaks.py" 라고 쓴다.
- 영어를 두 글자씩 자르면 "LangChain" 안의 "ai" 가 "AI" 와 맞고, "ZipGa" 안의 "ga" 가 "GA" 와 맞는다.
그래서 영어·숫자는 단어 통째로, 한글은 두 글자씩 자르고, 동의어는 사전으로 잇는다.
"""
import re

# 같은 뜻으로 보는 말 묶음. 공고에 나오는 말 → 운영 문서에 실제로 쓰인 말.
# 너무 넓은 말(AI, 비용, 평가)은 넣지 않는다. 아무 문서에나 맞아서 근거가 부풀기 때문이다.
GROUPS = [
    ["AI Agent", "AI 에이전트", "Agent", "Agents", "에이전트"],
    ["Multi Agent", "Multi-Agent", "멀티 에이전트", "멀티에이전트", "여러 에이전트"],
    ["LLM", "LLM API", "언어 모델", "Claude", "클로드", "Gemini", "제미나이", "GPT", "Opus", "Sonnet", "소넷", "Haiku", "하이쿠"],
    ["Claude Code", "클로드 코드", "클로드 코딩", "AI 코딩 도구", "AI 코딩 에이전트", "AI 코딩 Agent"],
    ["Python", "파이썬", ".py"],
    ["Workflow", "워크플로우", "워크플로", "Pipeline", "파이프라인"],
    ["Human-in-the-loop", "HITL", "사람 승인"],
    ["Prompt", "프롬프트"],
    ["Observability", "관측성", "관측 가능성", "Monitoring", "모니터링"],
    ["Tool Calling", "Function Calling", "Tool Use", "도구 호출"],
    ["Legacy System", "Legacy", "레거시", "레거시 시스템"],
    ["업무 자동화", "Automation", "자동화"],
    ["Git", "GitHub", "깃", "깃허브"],
    ["Chunking", "청킹"],
    ["Embedding", "임베딩"],
    ["Vector 검색", "Vector Search", "벡터 검색"],
    ["LangChain", "랭체인"],
    ["LangGraph", "랭그래프"],
    ["Java", "자바"],
    ["Spring Boot", "스프링 부트"],
    ["React", "리액트"],
    ["Kubernetes", "쿠버네티스", "k8s"],
    ["Docker", "도커"],
    ["Fine-tuning", "파인튜닝", "미세조정"],
]

LATIN = re.compile(r"[a-z0-9]+")
HANGUL_RUN = re.compile(r"[가-힣]+(?:\s+[가-힣]+)*")
HANGUL = re.compile(r"[가-힣]")


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]", "", s.lower())


_INDEX: dict[str, list[str]] = {}
for _group in GROUPS:
    for _member in _group:
        _INDEX.setdefault(_norm(_member), [])
        _INDEX[_norm(_member)] += [m for m in _group if m not in _INDEX[_norm(_member)]]


def tokens(text: str) -> list[str]:
    """검색 토큰: 영어·숫자는 단어 통째로, 한글은 공백을 없애고 두 글자씩. "사람 승인" → 사람, 람승, 승인"""
    t = text.lower()
    out = LATIN.findall(t)
    for run in HANGUL_RUN.findall(t):
        s = "".join(run.split())
        out += [s[i:i + 2] for i in range(len(s) - 1)]
    return out


def old_tokens(text: str) -> list[str]:
    """2-1 단계 방식 (비교용): 공백을 없애고 영어까지 전부 두 글자씩 자른다."""
    s = "".join(text.lower().split())
    return [s[i:i + 2] for i in range(len(s) - 1)]


def variants(term: str) -> list[str]:
    """키워드와 같은 뜻으로 보는 말. 사전에 정확히 같은 말이 있을 때만 넓힌다 ("Agent Action" 은 넓히지 않음)."""
    return _INDEX.get(_norm(term), [term]) if term.strip() else []


def _pattern(term: str) -> re.Pattern:
    t = re.escape(term.lower()).replace(r"\ ", r"\s*")
    head = r"(?<![a-z0-9])" if term[:1].isascii() and term[:1].isalnum() else ""
    tail = r"(?![a-z0-9])" if term[-1:].isascii() and term[-1:].isalnum() else ""
    return re.compile(head + t + tail)


def contains(text: str, term: str) -> bool:
    """글에 키워드가 있는가. 한글이 섞인 말은 그대로 찾고(조사가 붙으므로), 영어 말은 단어 경계로 찾는다 (GA ≠ ZipGa)."""
    if HANGUL.search(term):
        return _norm(term) in _norm(text)
    return bool(_pattern(term).search(text.lower()))


def expand_query(text: str, skills: list[str]) -> str:
    """검색어 넓히기: 요구 문장과 키워드에 사전의 말이 있으면 같은 묶음의 말을 덧붙인다."""
    extra: list[str] = []
    source = " ".join([text, *skills])
    for group in GROUPS:
        if any(contains(source, m) for m in group):
            extra += [m for m in group if not contains(source, m)]
    return " ".join([source, *extra])
