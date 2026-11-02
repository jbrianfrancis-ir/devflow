#!/usr/bin/env bash
# DevFlow size budget count. Read-only; counts git-tracked files at HEAD of the working tree.
# Usage: scripts/budget-count.sh            -> prints counts
#        scripts/budget-count.sh --check    -> also compares to docs/budget.md, exit 1 if any count is over
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
P=plugins/devflow
skills=$(git ls-files "$P/skills/*/SKILL.md" | wc -l)
agents=$(git ls-files "$P/agents/*.md" | wc -l)
commands=$(git ls-files "$P/commands/*" | wc -l)
hooks=$(git ls-files "$P/templates/hooks/*-guard.py" "$P/hooks/*" | wc -l)
# Prompt text = every tracked *.md outside .planning/, plus any non-.md file under agents/, commands/, skills/.
prompt_files() {
  { git ls-files '*.md' ':!:.planning/**'
    git ls-files "$P/agents" "$P/commands" "$P/skills" | grep -v '\.md$' || true; } | sort -u
}
prompt_lines=$(prompt_files | tr '\n' '\0' | xargs -0 cat | wc -l)
prompt_bytes=$(prompt_files | tr '\n' '\0' | xargs -0 cat | wc -c)
planning=$(git ls-files '.planning/*.md' '.planning/**/*.md' | sort -u | tr '\n' '\0' | xargs -0 -r cat | wc -l)
printf 'skills\t%s\nagents\t%s\ncommands\t%s\nhooks\t%s\nprompt_lines\t%s\nprompt_bytes_info\t%s\nplanning_lines_info\t%s\n' \
  "$skills" "$agents" "$commands" "$hooks" "$prompt_lines" "$prompt_bytes" "$planning"
if [[ "${1:-}" == "--check" ]]; then
  fail=0
  for k in skills agents commands hooks prompt_lines; do
    cap=$(awk -F'|' -v k="$k" '$2 ~ "^ *"k" *$" {gsub(/ /,"",$3); print $3}' docs/budget.md)
    [[ -z "$cap" ]] && { echo "budget: no cap for $k in docs/budget.md"; fail=1; continue; }
    v=${!k}
    (( v > cap )) && { echo "OVER BUDGET: $k=$v cap=$cap"; fail=1; }
  done
  exit $fail
fi
