"""공고 파일 읽기. 맨 위의 메모(--- 로 감싼 부분)는 빼고 공고 본문만 돌려준다."""
from pathlib import Path


def read_posting(path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()
