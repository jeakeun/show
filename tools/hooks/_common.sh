#!/bin/sh
# Shared settings for tools/hooks/* (sourced, not run directly).

REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")

# gitleaks: PATH first, then the winget install folder (scheduled tasks may have a short PATH).
GL=$(command -v gitleaks 2>/dev/null)
if [ -z "$GL" ]; then
  for c in /c/Users/User/AppData/Local/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_*/gitleaks.exe; do
    [ -x "$c" ] && GL="$c"
  done
fi

# semgrep: dedicated venv + locally cached rule pack (no network, no metrics at hook time).
SG=/d/tools-venv/semgrep/Scripts/semgrep.exe
SG_RULES=/d/tools-venv/semgrep-rules/default.yml
SG_LOGDIR=/d/tools-venv/semgrep-logs

PY=/c/Users/User/AppData/Local/Programs/Python/Python312/python.exe

run_local_hook() {
  # Because core.hooksPath points here, git no longer runs the repo's own .git/hooks/<name>
  # (e.g. D:\code-reviewer's AI review hook). Run it ourselves, after our checks pass.
  # $1 hook name, rest = its arguments. stdin is passed through by the caller.
  name=$1; shift
  lh="$(git rev-parse --git-common-dir 2>/dev/null)/hooks/$name"
  if [ -f "$lh" ] && [ -x "$lh" ]; then
    "$lh" "$@"
    return $?
  fi
  return 0
}

notify_phone() {
  # $1 title, $2 message (ASCII only). Never fails the hook. HOOK_NO_NOTIFY=1 silences it (tests).
  [ "$HOOK_NO_NOTIFY" = "1" ] && return 0
  if [ -x "$PY" ] && [ -f /d/notify/push.py ]; then
    timeout 20 "$PY" /d/notify/push.py "$1" "$2" </dev/null >/dev/null 2>&1 || true
  fi
}
