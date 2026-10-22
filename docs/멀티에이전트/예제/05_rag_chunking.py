# RAG 실험: 같은 문서를 자르는 방법에 따라 조각이 어떻게 달라지는지, 검색 방법에 따라 결과가 어떻게 달라지는지
import sys
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_community.retrievers import BM25Retriever

import os
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02-내-설계결정-기록.md")
text = open(path, encoding="utf-8").read()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

blind = splitter.create_documents([text])                                   # 글자 수로만 자르기
by_header = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2")]).split_text(text)
structured = splitter.split_documents(by_header)                            # 제목 기준 + 500자
print(f"글자 수로만: {len(blind)}조각 / 제목 기준: {len(by_header)}조각 / 제목 기준+500자: {len(structured)}조각")
print("제목 기준 조각에 붙은 정보:", structured[5].metadata)
print("글자 수로만 자른 조각에 붙은 정보:", blind[5].metadata or "(없음)")
print("글자 수로만 자른 조각 중 본문에 ## ADR 제목 줄이 있는 것:", sum("## ADR" in d.page_content for d in blind), "/", len(blind))

q = "사람 승인은 어디에 두나"
fake = InMemoryVectorStore.from_documents(structured, DeterministicFakeEmbedding(size=64))
print("\n질문:", q)
print("가짜 임베딩 1등:", fake.similarity_search(q, k=1)[0].metadata.get("h2"))
def ko_tokens(s):                       # 한국어 키워드 검색용: 2글자씩 겹쳐 자른 조각
    s = s.replace(" ", "")
    return [s[i:i+2] for i in range(len(s) - 1)]
bm25 = BM25Retriever.from_documents(structured, preprocess_func=ko_tokens, k=3)
print("키워드(BM25) 상위 3:", [d.metadata.get("h2") for d in bm25.invoke(q)])

# 개선: 제목을 본문 앞에 붙여서 색인 (제목이 메타데이터에만 있으면 검색에 안 쓰임)
from langchain_core.documents import Document
with_title = [Document(page_content=f"[{d.metadata.get('h2', '')}]\n{d.page_content}", metadata=d.metadata)
              for d in structured]
bm25_t = BM25Retriever.from_documents(with_title, preprocess_func=ko_tokens, k=3)
print("제목 붙인 뒤 BM25 상위 3:", [d.metadata.get("h2") for d in bm25_t.invoke(q)])

# 비교: 글자 수로만 자른 조각(제목 줄이 본문에 남음), 제목 기준이지만 제목을 본문에 남기는 설정(strip_headers=False)
first_line = lambda d: d.metadata.get("h2") or d.page_content.strip().split("\n")[0][:30]
bm25_blind = BM25Retriever.from_documents(blind, preprocess_func=ko_tokens, k=3)
print("글자 수로만 BM25 상위 3:", [first_line(d) for d in bm25_blind.invoke(q)])
kept = splitter.split_documents(MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2")], strip_headers=False).split_text(text))
print("strip_headers=False BM25 상위 3:", [d.metadata.get("h2") for d in BM25Retriever.from_documents(kept, preprocess_func=ko_tokens, k=3).invoke(q)])
