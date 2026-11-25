#!/bin/sh
# Connect the shared hooks (gitleaks + semgrep) to every repo on the main PC.
#   bash tools/hooks/install.sh                 -> connect hooks (safe to run again)
#   bash tools/hooks/install.sh --update-rules  -> also re-download the semgrep rule pack
#   bash tools/hooks/install.sh --uninstall     -> disconnect hooks (only where they point here)
# Tools themselves: gitleaks = winget (Gitleaks.Gitleaks), semgrep = D:\tools-venv\semgrep (pip).
# Hooks are read from the MAIN checkout of show, so merge to main before running this.

HOOKS="C:/Users/User/OneDrive/Desktop/show/tools/hooks"
RULES=/d/tools-venv/semgrep-rules/default.yml
fail=0

if [ "$1" != "--uninstall" ]; then
  for h in pre-commit pre-push _common.sh; do
    [ -r "$HOOKS/$h" ] || { echo "ERROR: $HOOKS/$h missing - merge to main first"; exit 1; }
  done
fi

while IFS= read -r r; do
  [ -z "$r" ] && continue
  if ! git -C "$r" rev-parse --git-dir >/dev/null 2>&1; then
    echo "skip (no repo): $r"; continue
  fi
  if [ "$1" = "--uninstall" ]; then
    cur=$(git -C "$r" config --get core.hooksPath)
    if [ "$cur" = "$HOOKS" ]; then git -C "$r" config --unset core.hooksPath && echo "removed: $r"
    else echo "left as is: $r (hooksPath=[$cur])"; fi
  else
    git -C "$r" config core.hooksPath "$HOOKS"
    if [ "$(git -C "$r" config --get core.hooksPath)" = "$HOOKS" ]; then echo "connected: $r"
    else echo "FAILED: $r"; fail=1; fi
  fi
done <<EOF
/c/Users/User/OneDrive/Desktop/show
/d/yt-auto
/d/ai-daily
/d/coin-bot
/d/market-compass
/d/hub
/d/kids-toon
/d/YummyPlanet
EOF

if [ "$1" != "--uninstall" ] && { [ ! -f "$RULES" ] || [ "$1" = "--update-rules" ]; }; then
  mkdir -p "$(dirname "$RULES")"
  tmp="$RULES.$$.tmp"
  if curl -sfL --max-time 120 -o "$tmp" "https://semgrep.dev/c/p/default" && head -1 "$tmp" | grep -q '^rules:'; then
    mv "$tmp" "$RULES" && echo "semgrep rules updated: $RULES"
  else
    rm -f "$tmp"; echo "WARNING: semgrep rule download failed (kept old file if any)"
  fi
fi
exit $fail
