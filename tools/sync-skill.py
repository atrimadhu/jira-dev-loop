#!/usr/bin/env python3
"""Regenerate the portable skill's bundled files from the Claude Code sources.

The Claude Code setup in .claude/ is the source of truth for the role
instructions and the Jira client. The portable skill in skills/jira-loop/
bundles copies of them so it works in any Agent Skills-compatible tool.
Run this after editing any .claude/agents/jira-*.md, the Jira client or the
env example, then commit the result:

    python3 tools/sync-skill.py          # rewrite the bundled copies
    python3 tools/sync-skill.py --check  # exit 1 if they are out of date (CI)

SKILL.md itself is hand-written and is not touched by this script.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / ".claude"
SKILL = ROOT / "skills" / "jira-loop"

HEADER = (
    "<!-- Generated from .claude/agents/{name}.md by tools/sync-skill.py. "
    "Edit the source, not this file. -->\n\n"
)


def strip_frontmatter(text: str) -> str:
    """Drop the Claude Code agent frontmatter (model, effort, tools): other
    agents don't understand it, and the skill picks models itself."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + len("\n---\n"):].lstrip("\n")
    return text


def expected_files() -> dict:
    files = {}
    for agent in sorted((SRC / "agents").glob("jira-*.md")):
        body = strip_frontmatter(agent.read_text())
        files[SKILL / "references" / "roles" / agent.name] = HEADER.format(name=agent.stem) + body
    files[SKILL / "scripts" / "jira_client.py"] = (SRC / "scripts" / "jira_client.py").read_text()
    files[SKILL / "assets" / "jira-loop.env.example"] = (SRC / "jira-loop.env.example").read_text()
    return files


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for path, content in expected_files().items():
        if not path.exists() or path.read_text() != content:
            stale.append(path.relative_to(ROOT))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
    roles_dir = SKILL / "references" / "roles"
    wanted = {p.name for p in expected_files() if p.parent == roles_dir}
    for orphan in sorted(roles_dir.glob("*.md")):
        if orphan.name not in wanted:
            stale.append(orphan.relative_to(ROOT))
            if not check:
                orphan.unlink()
    if check:
        if stale:
            print("Out of date (run python3 tools/sync-skill.py):")
            for p in stale:
                print("  " + str(p))
            return 1
        print("Skill bundle is up to date.")
        return 0
    print("Updated %d file(s)." % len(stale) if stale else "Already up to date.")
    for p in stale:
        print("  " + str(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
