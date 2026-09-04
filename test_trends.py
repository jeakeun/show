"""YouTube 트렌드 수집 테스트."""
from src.trends import collect_trends

items = collect_trends()
print(f"수집 성공: {len(items)}건")
for t in items[:5]:
    print(f"- [{t['views']:,}회] {t['title'][:50]}")
