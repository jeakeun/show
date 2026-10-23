"""경력 문서를 읽어 자르고(청킹), 요구 항목마다 근거 조각을 찾는다(키워드 검색 BM25).

왜 키워드 검색부터 하나 (설계 결정 J-11):
- 임베딩 모델 없이 어디서나 돌아가서, 나중에 뜻 검색·하이브리드와 비교할 기준선이 된다.
- 공고의 기술 이름(LangGraph, RAG 등)은 정확한 단어라 키워드 검색이 강하다.
"""
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi


@dataclass(frozen=True)
class Chunk:
    id: str        # 예: "02-내-설계결정-기록#7"
    source: str    # 문서 경로
    kind: str      # "운영" | "학습"
    section: str   # 조각이 속한 제목
    text: str      # 조각 본문


def load_chunks(sources, root: Path, chunk_size: int = 600, overlap: int = 80) -> list[Chunk]:
    # strip_headers=False: 제목을 본문에서 빼지 않는다. 빼면 제목에 있는 말로 검색이 안 된다 (04-RAG 실험 3).
    by_header = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2"), ("###", "h3")], strip_headers=False)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks: list[Chunk] = []
    for rel, kind in sources:
        path = Path(root) / rel
        if not path.exists():
            print(f"[경고] 경력 문서가 없어 건너뜀: {path}")
            continue
        docs = splitter.split_documents(by_header.split_text(path.read_text(encoding="utf-8")))
        for i, d in enumerate(docs, start=1):
            m = d.metadata
            section = m.get("h3") or m.get("h2") or m.get("h1") or ""
            chunks.append(Chunk(f"{Path(rel).stem}#{i}", rel, kind, section, d.page_content))
    return chunks


def ko_tokens(text: str) -> list[str]:
    """한국어 키워드 검색용: 공백을 없애고 두 글자씩 겹쳐 자른다. "사람승인" → 사람, 람승, 승인"""
    s = "".join(text.lower().split())
    return [s[i:i + 2] for i in range(len(s) - 1)]


class Retriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        # 긴 조각의 둘째 부분부터는 제목 줄이 없으므로, 색인할 때 제목을 앞에 붙인다.
        self.bm25 = BM25Okapi([ko_tokens(f"{c.section}\n{c.text}") for c in chunks])

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        scores = self.bm25.get_scores(ko_tokens(query))
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        return [(c, float(s)) for c, s in ranked[:k] if s > 0]
