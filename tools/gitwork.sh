#!/usr/bin/env bash
# Branch workflow for the automation repos (user rule 2026-10-01):
#   work on a branch -> verify/test there -> merge into main only after tests pass.
# The live folders (D:\yt-auto, D:\coin-bot, D:\ai-daily, ...) stay on main because the
# Task Scheduler runs them directly. Branch work happens in a separate worktree folder D:\wt\<repo>-<name>.
#
#   bash gitwork.sh start  <repo> <name>   # new branch work/<name> + worktree, links secrets/.venv
#   bash gitwork.sh finish <repo> <name>   # merge --no-ff into main (live folder), push, clean up
#   bash gitwork.sh drop   <repo> <name>   # abandon: remove worktree and branch without merging
#   bash gitwork.sh list                   # open work branches
set -euo pipefail

WT_ROOT=/d/wt
LINKS=(secrets .venv)   # git-ignored things a test run needs; linked (junction), never copied

win() { cygpath -w "$1"; }

unlink_all() {  # remove junctions only (non-recursive Directory.Delete never touches the target)
  local wt=$1
  for l in "${LINKS[@]}"; do
    [ -e "$wt/$l" ] && powershell -NoProfile -Command "[System.IO.Directory]::Delete('$(win "$wt/$l")')"
  done
  return 0
}

repo_running() {  # is a python/claude job of this repo running right now?
  # excluded: always-on src.server, and interactive Claude desktop sessions (stream-json; they only list the repo as --add-dir)
  powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*$1*' -and \$_.CommandLine -notlike '*src.server*' -and \$_.CommandLine -notlike '*--input-format stream-json*' -and \$_.Name -match 'python|claude|cmd' } | Measure-Object).Count"
}

cmd_start() {
  local repo=$1 name=$2 live=/d/$1 wt=$WT_ROOT/$1-$2 br=work/$2
  [ -d "$live/.git" ] || { echo "no repo $live"; exit 1; }
  mkdir -p "$WT_ROOT"
  git -C "$live" worktree add -b "$br" "$wt" main
  for l in "${LINKS[@]}"; do
    [ -e "$live/$l" ] && powershell -NoProfile -Command "New-Item -ItemType Junction -Path '$(win "$wt/$l")' -Target '$(win "$live/$l")' | Out-Null"
  done
  echo "branch $br ready at $wt"
  [ -e "$live/.venv" ] && echo "python: $wt/.venv/Scripts/python (linked to live .venv)" || true
}

cmd_finish() {
  local repo=$1 name=$2 live=/d/$1 wt=$WT_ROOT/$1-$2 br=work/$2
  if [ -n "$(git -C "$wt" status --porcelain --untracked-files=no)" ]; then
    echo "uncommitted changes in $wt - commit or drop first"; exit 1
  fi
  # 2026-10-16: a heredoc turned a \n into a real newline inside a string and a syntax error reached main.
  # Compile every changed .py and parse every changed .json before merging; refuse on failure.
  local py="$live/.venv/Scripts/python.exe"; [ -x "$py" ] || py=python
  local changed; changed=$(git -C "$wt" diff --name-only main...HEAD | tr -d '\r')
  local pys jsons; pys=$(echo "$changed" | grep '\.py$' || true); jsons=$(echo "$changed" | grep '\.json$' || true)
  if [ -n "$pys" ]; then
    (cd "$wt" && "$py" -m py_compile $pys) || { echo "syntax error in changed .py files - not merged"; exit 1; }
  fi
  if [ -n "$jsons" ]; then
    (cd "$wt" && "$py" -c "import json,sys; [json.load(open(f, encoding='utf-8')) for f in sys.argv[1:]]" $jsons) \
      || { echo "invalid json in changed files - not merged"; exit 1; }
  fi
  local n; n=$(repo_running "$repo" | tr -d '\r' || true)
  if [ "$n" != "0" ]; then echo "a $repo job is running now or the check failed ('$n') - try again later"; exit 1; fi
  git -C "$live" checkout -q main
  git -C "$live" merge --no-ff "$br" -m "Merge $br (tested)"
  git -C "$live" push -q origin main
  unlink_all "$wt"
  git -C "$live" worktree remove "$wt"
  git -C "$live" branch -d "$br"
  git -C "$live" push -q origin --delete "$br" 2>/dev/null || true
  echo "merged $br into main and cleaned up"
}

cmd_drop() {
  local repo=$1 name=$2 live=/d/$1 wt=$WT_ROOT/$1-$2 br=work/$2
  unlink_all "$wt"
  git -C "$live" worktree remove --force "$wt"
  git -C "$live" branch -D "$br"
  git -C "$live" push -q origin --delete "$br" 2>/dev/null || true
  echo "dropped $br"
}

cmd_list() {
  for live in /d/yt-auto /d/coin-bot /d/ai-daily /d/market-compass /d/hub; do
    [ -d "$live/.git" ] || continue
    git -C "$live" branch --list 'work/*' --format="$(basename "$live"): %(refname:short)"
  done
}

case "${1:-}" in
  start)  cmd_start "$2" "$3" ;;
  finish) cmd_finish "$2" "$3" ;;
  drop)   cmd_drop "$2" "$3" ;;
  list)   cmd_list ;;
  *) sed -n 2,12p "$0"; exit 1 ;;
esac
