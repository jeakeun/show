"""경력 문서를 읽어 자르고(청킹), 요구 항목마다 근거 조각을 찾는다(키워드 검색 BM25).

왜 키워드 검색부터 하나 (설계 결정 J-11):
- 임베딩 모델 없이 어디서나 돌아가서, 나중에 뜻 검색·하이브리드와 비교할 기준선이 된다.
- 공고의 기술 이름(LangGraph, RAG 등)은 정확한 단어라 키워드 검색이 강하다.

2-2 단계에서 고친 것 (2026-10-27, 001에서 운영 경험을 못 찾은 원인 세 가지):
- 근거가 아닌 부분을 뺀다: 폴더 지도, "아직 약한 곳"(없는 경험 목록), 개발 중인 프로젝트 줄. (load_chunks 의 rules·drop_lines)
- 말을 맞춘다: 영어는 단어 통째로, 동의어 사전으로 "LLM ↔ 클로드", "Python ↔ 파이썬"을 잇는다. (words.py)
- 종류별로 찾는다: 학습 문서가 LangChain·RAG를 직접 다뤄서 상위 3개를 늘 차지한다.
  그래서 상위 k개에 더해 운영·학습 문서에서 각각 가장 맞는 조각을 per_kind 개씩 더 가져온다. (Retriever.search)
"""
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

from . import words


@dataclass(frozen=True)
class Chunk:
    id: str        # 예: "02-내-설계결정-기록#7"
    source: str    # 문서 경로
    kind: str      # "운영" | "학습"
    section: str   # 조각이 속한 제목
    text: str      # 조각 본문


def _drop(text: str, drop_lines) -> str:
    """표 한 줄·인용 한 줄에 섞인 것만 뺀다. 제목 줄은 건드리지 않는다 (절이 합쳐지지 않게)."""
    keep = [line for line in text.splitlines()
            if not (line.lstrip().startswith(("|", ">")) and any(d in line for d in drop_lines))]
    return "\n".join(keep)


def load_chunks(sources, root: Path, chunk_size: int = 600, overlap: int = 80,
                rules=(), drop_lines=()) -> list[Chunk]:
    """rules: (문서, 절 제목에 든 말, 바꿀 종류 또는 None=뺌, 이유). drop_lines: 표·인용 줄에서 뺄 말."""
    # strip_headers=False: 제목을 본문에서 빼지 않는다. 빼면 제목에 있는 말로 검색이 안 된다 (04-RAG 실험 3).
    by_header = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2"), ("###", "h3")], strip_headers=False)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks: list[Chunk] = []
    for rel, kind in sources:
        path = Path(root) / rel
        if not path.exists():
            print(f"[경고] 경력 문서가 없어 건너뜀: {path}")
            continue
        text = _drop(path.read_text(encoding="utf-8"), drop_lines) if drop_lines else path.read_text(encoding="utf-8")
        docs = splitter.split_documents(by_header.split_text(text))
        for i, d in enumerate(docs, start=1):
            m = d.metadata
            section = m.get("h3") or m.get("h2") or m.get("h1") or ""
            heading = " / ".join(m[h] for h in ("h1", "h2", "h3") if m.get(h))
            this_kind = kind
            for r_source, r_section, r_kind, _why in rules:
                if r_source == rel and r_section in heading:
                    this_kind = r_kind
            if this_kind is None:
                continue
            chunks.append(Chunk(f"{Path(rel).stem}#{i}", rel, this_kind, section, d.page_content))
    return chunks


def load_career(cfg) -> list[Chunk]:
    """설정대로 경력 문서를 읽는다. clean_sources=False 면 2-1 단계처럼 문서를 그대로 쓴다 (비교용)."""
    clean = getattr(cfg, "clean_sources", True)
    return load_chunks(cfg.sources, cfg.source_root, cfg.chunk_size, cfg.chunk_overlap,
                       rules=cfg.source_rules if clean else (), drop_lines=cfg.drop_lines if clean else ())


def ko_tokens(text: str) -> list[str]:
    """검색 토큰 (words.tokens). 한글은 두 글자씩: "사람 승인" → 사람, 람승, 승인"""
    return words.tokens(text)


class Retriever:
    def __init__(self, chunks: list[Chunk], match_words: bool = True):
        self.chunks = chunks
        self.match_words = match_words
        self.tokenize = words.tokens if match_words else words.old_tokens
        # 긴 조각의 둘째 부분부터는 제목 줄이 없으므로, 색인할 때 제목을 앞에 붙인다.
        self.bm25 = BM25Okapi([self.tokenize(f"{c.section}\n{c.text}") for c in chunks])

    def search(self, query: str, k: int = 3, per_kind: int = 0, skills: list[str] | None = None):
        """상위 k개 + (per_kind>0 이면) 운영·학습 문서 각각에서 최소 per_kind 개가 되도록 더 붙인다.
        돌려주는 것: (조각, 점수, 더붙임 여부). 더 붙인 조각은 상위 k개가 아니라는 표시다."""
        if self.match_words:
            query = words.expand_query(query, skills or [])
        elif skills:
            query = " ".join([query, *skills])
        scores = self.bm25.get_scores(self.tokenize(query))
        ranked = [(c, float(s)) for c, s in sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True) if s > 0]
        hits = [(c, s, False) for c, s in ranked[:k]]
        if per_kind:
            taken = {c.id for c, _, _ in hits}
            for kind in sorted({c.kind for c in self.chunks}):
                have = sum(1 for c, _, _ in hits if c.kind == kind)
                for c, s in ranked:
                    if have >= per_kind:
                        break
                    if c.kind == kind and c.id not in taken:
                        hits.append((c, s, True))
                        taken.add(c.id)
                        have += 1
        return hits
