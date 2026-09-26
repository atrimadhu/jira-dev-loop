# Playground: try jira-loop in about 15 minutes

This guide runs the full pipeline three ways against a small practice app,
so you can see how it behaves before pointing it at real code.

| Mode | Needs Jira? | Input | Output lands in |
|---|---|---|---|
| **A. Inline text** | No | A one-line description | `.dev-loop/LOCAL-<timestamp>/` |
| **B. `.md` / `.txt` file** | No | A spec or bug-report file | `.dev-loop/LOCAL-<timestamp>/` |
| **C. Jira ticket** | Yes | A ticket key such as `PLAY-1` | `.jira-loop/PLAY-1/` + comments and attachments on the ticket |

Start with A or B. They need no credentials and nothing leaves your machine
except the Claude Code session itself.

---

## Step 0: Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (`claude --version`)
- `python3` 3.9 or newer
- `git`

## Step 1: Set up a sandbox copy of the playground app

Work on a copy so the original stays clean for the next experiment:

```bash
git clone https://github.com/<your-username>/jira-dev-loop.git
cd jira-dev-loop

cp -r examples/playground-app ~/jira-loop-sandbox
cp -r examples/specs ~/jira-loop-sandbox/specs

cd ~/jira-loop-sandbox
python3 -m unittest -v    # 5 tests pass
```

## Step 2: Install the pipeline into the sandbox

```bash
~/jira-dev-loop/install.sh ~/jira-loop-sandbox    # adjust to where you cloned it
```

This adds 8 agents, the `/jira-loop` command and the Jira client under
`~/jira-loop-sandbox/.claude/`. It never overwrites files that already exist.

Then take a git baseline, so you can diff each run and reset between them.
Run trails and QA sheets are ignored so they survive a reset:

```bash
printf '.jira-loop/\n.dev-loop/\n__pycache__/\nqa/\n' >> .gitignore
git init -q && git add -A && git commit -qm "baseline"
```

## Step 3: Open Claude Code in the sandbox

```bash
cd ~/jira-loop-sandbox
claude
```

Type `/jira` and `/jira-loop` should autocomplete. If it doesn't, you're not
in the sandbox folder.

---

## Mode A: Inline text

Paste into Claude Code:

```text
/jira-loop --text "An order of exactly $100.00 is charged full price, but the promo says $100 or more gets 10% off."
```

**What to watch:**
1. The planner infers the lane. The first line of `plan-final.md` should say `BUG` and give a reason.
2. `.dev-loop/LOCAL-*/` fills up as each agent finishes. Open it in a second terminal:
   ```bash
   watch -n 2 'ls -1 .dev-loop/*/ qa/ 2>/dev/null'
   ```
3. At the end you get a chat summary with status, coverage %, QA pass rate, and whether any loop hit its 3-round cap.

**Check the result yourself:**

```bash
git diff                     # expect a one-character fix: > becomes >=
python3 -m unittest -v       # original 5 tests plus the new ones
cat .dev-loop/LOCAL-*/final-comment.md
```

More prompts to try, including vague and contradictory ones, are in
[`examples/inline-text.md`](../examples/inline-text.md).

**Reset before the next experiment:**

```bash
git reset --hard && git clean -fd    # restores the code; ignored trails and credentials stay
```

---

## Mode B: A `.md` or `.txt` file

Use this when the requirement is longer than a sentence: a PRD, a pasted bug
report, meeting notes.

```text
/jira-loop --file specs/bug-bulk-discount-boundary.txt
/jira-loop --file specs/story-coupon-codes.md
/jira-loop --file specs/task-decimal-money.md --type task
```

Run them one at a time, resetting between runs. Each spec exercises a
different lane:

| Spec | Lane | The plan will contain | QA sheet is built from |
|---|---|---|---|
| `bug-bulk-discount-boundary.txt` | BUG | `## ROOT_CAUSE` + blast radius | The exact repro (P0) + regression cases |
| `story-coupon-codes.md` | STORY | `## ACCEPTANCE_CRITERIA` (7 items) | At least one case per AC, traced in the `Ref` column |
| `task-decimal-money.md` | TASK | `## DEFINITION_OF_DONE` | One Verification case per DoD item |

**Things worth checking:**
- **Story:** open `qa/LOCAL-*-test-cases.csv` and confirm every AC number 1–7 appears in the `Ref` column. The final report must say per AC whether it was met.
- **Task:** the DoD says "no new dependencies". See whether the reviewer flags it if the executor reaches for one.
- **Guardrail:** `/jira-loop --file specs/does-not-exist.md` and `/jira-loop --file cart.py` both stop immediately. The pipeline won't guess at a path or treat a code file as a spec.

**Write your own spec.** Any `.md` or `.txt` file works. Use this skeleton:

```markdown
# <Bug|Story|Task>: <one-line title>

## Context
<what exists today and why it's a problem>

## Acceptance Criteria        <- for a story
1. ...

## Definition of Done         <- for a task
- ...

## Steps to reproduce         <- for a bug
1. ...
Expected: ...
Actual: ...
```

---

## Mode C: A real Jira ticket

### C1. Credentials

```bash
cp .claude/jira-loop.env.example .claude/jira-loop.env
```

Fill in `.claude/jira-loop.env`:

```ini
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=<from https://id.atlassian.com/manage-profile/security/api-tokens>
JIRA_API_VERSION=3        # 3 = Jira Cloud, 2 = Server/Data Center
```

Confirm the token file is git-ignored:

```bash
git check-ignore -v .claude/jira-loop.env    # must print a match
```

### C2. Create the practice tickets

Create the three tickets in [`examples/jira-tickets.md`](../examples/jira-tickets.md)
in a Jira project you can write to. A throwaway project named `PLAY` is
ideal. Set the Issue type correctly, because it picks the lane.

### C3. Smoke-test the connection

```bash
python3 .claude/scripts/jira_client.py env-check
python3 .claude/scripts/jira_client.py get PLAY-1
```

The second command should print the ticket as JSON. Fix any error here
before going further; the pipeline stops in Phase 0 if this fails.

### C4. Run it

```text
/jira-loop PLAY-1
```

**What shows up on the ticket, in order:**
1. A comment with the **finalized plan**, after planner and planner-review agree (at most 3 rounds)
2. An **attachment**: `PLAY-1-test-cases.csv`, the QA sheet
3. A **final comment**: summary, coverage, QA results, deviations, and a `Ready for PR` / `Needs manual follow-up` status

### C5. Try the guardrails

- Create an **Epic** and run `/jira-loop` on it. It refuses and tells you to split it up.
- Create a **Sub-task** under `PLAY-2`. The pipeline fetches the parent Story too, so the plan respects the parent's acceptance criteria.

### C6. Promote a local run to a ticket

Already ran Mode A or B, and now a ticket exists? Post the existing write-ups
without rerunning anything:

```bash
python3 .claude/scripts/jira_client.py comment PLAY-4 --file .dev-loop/LOCAL-<timestamp>/plan-final.md
python3 .claude/scripts/jira_client.py comment PLAY-4 --file .dev-loop/LOCAL-<timestamp>/final-comment.md
python3 .claude/scripts/jira_client.py attach  PLAY-4 qa/LOCAL-<timestamp>-test-cases.csv
```

---

## Reading a run's trail

Every run writes each agent's output to disk as it goes:

```
.dev-loop/LOCAL-20260925-143012/        (or .jira-loop/PLAY-1/)
├── plan-round-1.md        planner, first draft
├── review-round-1.md      planner-review: APPROVE or REQUEST_CHANGES
├── plan-round-2.md        only if changes were requested
├── plan-final.md          the agreed plan
├── executor-1.md          what was changed, file by file
├── coverage-1.md          tests added, coverage % on changed code
├── reviewer-round-1.md    implementation vs requirement
└── final-comment.md       the closing report
qa/<KEY>-test-cases.csv    QA sheet, with pass/fail filled in
```

To see what a finished run looks like without spending tokens, open
[`examples/sample-output/`](../examples/sample-output/).

## Tips

- **Cost:** a run makes at least 8 agent calls, more when loops retry. Keep specs small while you learn how it behaves.
- **Interrupting is safe.** Whatever was already written to disk (and posted to Jira) stays. The trail folder shows how far it got.
- **Reruns start fresh.** Running the same input again doesn't resume. It produces a new plan and a new trail folder, which is handy for comparing runs.
- **The 3-round cap never fails silently.** If a loop gives up, the final report says so and the status is `Needs manual follow-up`.
