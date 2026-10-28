import io, sys, os
SRC, OUT = sys.argv[1], sys.argv[2]
s = io.open(SRC, encoding="utf-8").read()
PRINT = """
<style>
@media print {
  @page { size: A4; margin: 12mm 11mm 13mm; }
  /* 인쇄는 항상 밝은 테마로 — 잉크와 가독성 */
  :root, :root[data-theme="dark"] {
    --bg:#FFFFFF; --surface:#FFFFFF; --fg:#15201F; --muted:#56635F;
    --line:#D2DAD8; --accent:#0B6E62; --alert:#9C4221; color-scheme: light;
  }
  body { background:#fff !important; font-size: 9.6pt; line-height: 1.6; }
  .wrap { max-width: none; padding-block: 0 0; padding-left: 0; padding-right: 0; }
  header { padding-block: 0 4px; }
  h1 { font-size: 21pt; line-height: 1.22; }
  .lede { font-size: 10pt; max-width: none; }
  section { padding-block: 15px 0; }
  h2 { break-after: avoid; page-break-after: avoid; }
  .rail-note { break-after: avoid; page-break-after: avoid; }
  /* 통째로 쪼개지면 안 되는 덩어리들 */
  .shots, .shot, .nums, .tt, .pj, .fix, .sk, footer {
    break-inside: avoid; page-break-inside: avoid;
  }
  .shots { grid-template-columns: repeat(4, 1fr) !important; gap: 10px; }
  .shots.vids { grid-template-columns: repeat(3, 1fr) !important; gap: 12px; }
  .shot img { border-color: #CBD4D1; }
  .shot .cap { font-size: 8.6pt; line-height: 1.5; }
  .num .v { font-size: 20px; }
  .num .k { font-size: 10px; }
  .tt > .t, .tt > .d { padding-block: 8px; }
  .tt > .d small { font-size: 8.6pt; }
  .pj-s, .did li, .meta dd, .fix .fl { font-size: 9pt; }
  /* 프로젝트 카드 압축 — 한 쪽에 두 개가 들어가도록 */
  .pj { padding-block: 9px 2px; }
  .pj-s { margin-top: 5px; }
  .meta { margin-top: 9px; gap: 2px 14px; }
  .did { gap: 4px; margin-top: 10px; }
  .fix { margin-top: 10px; gap: 3px; }
  .pj-h img { height: 22px; }
  .pj-h h3 { font-size: 15px; }
  a { border-bottom: none; color: var(--accent); }
  footer { margin-top: 26px; }
  /* 큰 덩어리는 새 쪽에서 시작 — 이미지 줄이 두 쪽에 걸치지 않게 */
  section.newpage { break-before: page; page-break-before: always; }
  section.newpage { padding-block: 0 0; }
}
</style>
"""
# 머리글 바로 밑 첫 섹션만 같은 쪽에 두고, 나머지 큰 섹션은 새 쪽에서 시작한다.
cands = ['<section>\n  <h2>작업물 — nudy<span>',
         '<section>\n  <h2>작업물 — nudy 마케팅 영상',
         '<section>\n  <h2>영상이 만들어져 나가는 경로',
         '<section>\n  <h2>이미지가 만들어져 나가는 경로',
         '<section>\n  <h2>프로젝트']
found = sorted([(s.index(m), m) for m in cands if m in s])
for _, m in found[1:]:
    s = s.replace(m, m.replace('<section>', '<section class="newpage">'), 1)
i = s.index("</style>") + len("</style>")
io.open(OUT, "w", encoding="utf-8").write(s[:i] + PRINT + s[i:])
print("작성:", os.path.basename(OUT))
