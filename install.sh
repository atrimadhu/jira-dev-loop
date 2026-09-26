#!/usr/bin/env bash
# Installs jira-loop into an existing project's .claude/ folder without
# touching anything already there. Safe to run against a project that
# already has its own agents/commands/skills.
#
# Usage: ./install.sh /path/to/target-project
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.claude"

if [ $# -ne 1 ]; then
  echo "Usage: $0 /path/to/target-project" >&2
  exit 2
fi

TARGET="$1"
if [ ! -d "$TARGET" ]; then
  echo "Error: '$TARGET' is not a directory" >&2
  exit 2
fi

DST="$TARGET/.claude"
mkdir -p "$DST/agents" "$DST/commands" "$DST/scripts"

conflicts=()
copied=()
skipped_identical=()

copy_one() {
  local src="$1" dst="$2"
  if [ -e "$dst" ]; then
    if cmp -s "$src" "$dst"; then
      skipped_identical+=("$dst")
    else
      conflicts+=("$dst")
    fi
  else
    cp "$src" "$dst"
    copied+=("$dst")
  fi
}

for f in "$SRC"/agents/jira-*.md; do
  copy_one "$f" "$DST/agents/$(basename "$f")"
done

copy_one "$SRC/commands/jira-loop.md" "$DST/commands/jira-loop.md"
copy_one "$SRC/scripts/jira_client.py" "$DST/scripts/jira_client.py"

# Never overwrite an existing env file — it may already hold real secrets.
if [ ! -e "$DST/jira-loop.env.example" ]; then
  cp "$SRC/jira-loop.env.example" "$DST/jira-loop.env.example"
  copied+=("$DST/jira-loop.env.example")
else
  skipped_identical+=("$DST/jira-loop.env.example (left as-is)")
fi

# Merge the gitignore entry rather than overwrite the project's own file.
touch "$DST/.gitignore"
grep -qxF "jira-loop.env" "$DST/.gitignore" || echo "jira-loop.env" >> "$DST/.gitignore"

echo "== jira-loop install: $TARGET =="
if [ ${#copied[@]} -gt 0 ]; then
  echo "Copied:"
  printf '  %s\n' "${copied[@]}"
fi
if [ ${#skipped_identical[@]} -gt 0 ]; then
  echo "Already present (unchanged, left as-is):"
  printf '  %s\n' "${skipped_identical[@]}"
fi
if [ ${#conflicts[@]} -gt 0 ]; then
  echo
  echo "CONFLICTS — these files already exist with DIFFERENT content and were NOT touched:"
  printf '  %s\n' "${conflicts[@]}"
  echo "Resolve manually (diff against $SRC and merge by hand) before running /jira-loop."
fi

echo
if [ ! -e "$DST/jira-loop.env" ]; then
  echo "Next: cp $DST/jira-loop.env.example $DST/jira-loop.env  (then fill in your Jira credentials)"
else
  echo "Found existing $DST/jira-loop.env — left untouched."
fi
echo "Then: cd $TARGET && python3 .claude/scripts/jira_client.py env-check"
echo "Then: open Claude Code in $TARGET and run /jira-loop <TICKET-KEY>"

if [ ${#conflicts[@]} -gt 0 ]; then
  exit 1
fi
