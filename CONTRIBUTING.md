# Contributing to jira-loop

Thanks for helping. This project is mostly prompts, so a good contribution
shows *evidence* that a change improves behavior, not just that it reads
better.

## Ways to help

- **Report a bad run.** Open an issue with the input (ticket text, `--text`
  string or spec file), the lane, and the relevant files from the trail folder
  (`.jira-loop/<KEY>/` or `.dev-loop/LOCAL-<ts>/`). Remove anything
  confidential first.
- **Improve an agent prompt** in `.claude/agents/`. Include a before/after
  run on the same input in the PR, ideally one of the playground specs.
- **Add a playground spec** in `examples/specs/`. It should be small, target
  `examples/playground-app/`, and state its expected outcome clearly.
- **Tracker support.** Linear, GitHub Issues and GitLab adapters should
  follow the same pattern as `jira_client.py`: stdlib only, called by the
  orchestrator only.

## Ground rules

- **Zero dependencies.** `jira_client.py` and `install.sh` use only the
  Python stdlib and POSIX tools.
- **`install.sh` must stay non-destructive.** It never overwrites a file with
  different content and never touches `jira-loop.env`.
- **Honesty over polish.** Don't change an agent in a way that lets a hit retry
  cap, a failing case or an unmet acceptance criterion be left out of the
  final report.
- **Never commit credentials.** Check `git status` before pushing; the
  `.claude/jira-loop.env` file must stay ignored.

## Local checks

```bash
bash -n install.sh
python3 -m py_compile .claude/scripts/jira_client.py
(cd examples/playground-app && python3 -m unittest -v)
```
