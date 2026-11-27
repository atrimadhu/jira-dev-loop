---
name: jira-loop
description: Autonomous dev pipeline that takes one ticket from requirement to reviewed, tested code — plan, adversarial plan review, implementation, unit-test coverage (90%+ on changed code), code review against the requirement, a QA test sheet that gets executed, and a final report — with every loop capped at 2 rounds. Works from a Jira ticket key (reads the ticket and posts the plan, QA sheet and report back to it), from inline text, or from a .md/.txt spec file, with no Jira needed for the latter two. Use this whenever the user asks to implement, build, fix or "work" a Jira ticket or issue key (e.g. PROJ-123), to take a spec, PRD or bug report end to end, or to run "jira-loop" / "dev loop", even if they don't name the skill. Add --lite for small, low-risk changes. Don't use it for a quick one-line edit the user wants done directly, or for only reading or commenting on a ticket.
license: MIT
compatibility: Needs an agent that can read and write files and run shell commands. python3 3.9+ for Jira mode. Subagents are optional — the skill uses them when available.
metadata:
  version: "1.1.0"
  homepage: https://github.com/atrimadhu/jira-dev-loop
---

# jira-loop

You are the orchestrator. You don't write the plan or the code yourself — you drive eight specialist roles through a fixed pipeline, and each role's full instructions live in `references/roles/`. The run is fully autonomous: don't stop to ask the user for permission between phases. Every loop is capped at **2 rounds**; when a cap is hit, stop that loop, record what is unresolved, and carry it into the final report so a human sees it.

`<SKILL_DIR>` below means the folder this SKILL.md is in. Resolve it to an absolute path once at the start, because roles and scripts are referenced from it while you work in the user's repo.

| Role | Role file (`<SKILL_DIR>/references/roles/`) | Does |
|---|---|---|
| planner | `jira-planner.md` | Writes the plan and `context.md` |
| planner-review | `jira-planner-review.md` | Adversarially reviews the plan |
| executor | `jira-executor.md` | Implements the plan; applies fix requests |
| code-coverage | `jira-code-coverage.md` | Unit tests to 90%+ on changed code |
| reviewer | `jira-reviewer.md` | Reviews code against the requirement |
| qa-testcases | `jira-qa-testcases.md` | Writes the QA test-case CSV |
| qa-testing | `jira-qa-testing.md` | Executes the sheet, classifies failures |
| final-review | `jira-final-review.md` | Writes the closing report |

## How to run a role

Use the first option your agent supports:

1. **Claude Code with the jira-loop agents installed** (`.claude/agents/jira-*.md` exist in the project or `~/.claude/agents/`): call the `Agent` tool with `subagent_type` set to the agent name (e.g. `jira-planner`). Those agents carry tuned model and effort settings.
2. **Any agent that can spawn subagents** (a Task/Agent/subagent tool): spawn a general-purpose subagent with this prompt, filled in:
   > You are the `<role>` in a jira-loop run. Read `<SKILL_DIR>/references/roles/<role file>` and follow it exactly. Inputs: `TICKET: …`, `PLAN: …`, `OUTPUT_FILE: …` (and any others the step lists), lane: `…`, round: `…`.

   If you can choose a model per subagent, use your strongest model for planner and executor and a cheaper, faster one for the other roles.
3. **No subagents** (single-agent mode): play each role yourself, one at a time. Before each role, read its role file fresh. Work only from the files named in that step — not from what you remember doing in an earlier role — so the reviewers judge the code against the ticket rather than against your own intentions. Write `OUTPUT_FILE`, then route on the verdict in that file (no separate reply lines needed) and move on. Steps marked parallel run one after the other. Note in the final report that one agent played every role, since the review is less independent.

## Token budget: paths in, short verdicts out

A full run makes 8–20 role calls (about 5 with `--lite`), so what you pass around dominates the cost:
- **Pass file paths, never pasted content.** Each role call names its inputs as paths plus an `OUTPUT_FILE`, the lane and the round. Roles read what they need.
- **Roles write their full output to `OUTPUT_FILE` and reply with a few lines** (`VERDICT:`/`RESULT:`, `WROTE:`, counts). Route on those lines; open a role's output file only when a routing decision can't be made from the reply. If a role replies with its whole report or didn't write the file, save the reply to the expected path once and carry on.
- **Run independent calls in parallel** when your agent can (several subagent calls in one message).
- **The roles that read code get `CONTEXT_FILE: <WORKDIR>/context.md`** — the planner's map of the relevant files — so they don't search the codebase from scratch. Leave it out for qa-testcases (it works from the requirement, not the code) and final-review.

## Phase 0 — Mode, flags and run folder

1. **Read the request.** Strip trailing flags first, in any order: `--type bug|story|task` (local modes only) and `--lite` (switches on LITE MODE, below). Then:
   - **JIRA MODE**: the request is (or names) a Jira key like `PROJ-123`.
   - **TEXT MODE**: `--text "<description>"`, or the user simply described the work inline. Use the description verbatim — don't reinterpret or summarize it.
   - **FILE MODE**: `--file <path>` to a `.md` or `.txt` file. If it doesn't exist or has another extension, stop and say so; don't guess another path.
   TEXT and FILE MODE are both **LOCAL MODE** from here on: no Jira, same behavior.

2. **JIRA MODE:**
   a. Run `python3 <SKILL_DIR>/scripts/jira_client.py env-check` from the repo root. If it fails, stop and tell the user what's missing: credentials come from `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` in the environment, or from `.claude/jira-loop.env` or `jira-loop.env` in the repo root (template: `<SKILL_DIR>/assets/jira-loop.env.example`; make sure the file is git-ignored).
   b. `mkdir -p .jira-loop/<KEY>` and run `python3 <SKILL_DIR>/scripts/jira_client.py get <KEY> > .jira-loop/<KEY>/ticket.json`. Don't print it; extract only what routing needs: `python3 -c "import json;d=json.load(open('.jira-loop/<KEY>/ticket.json'));print(d['issuetype'], d.get('parent') or '')"`. If `get` fails, show its error and stop.
   c. Map `issuetype` to a lane. Give the lane in every role call in every mode as `lane: BUG|STORY|TASK` (Jira mode may add the issuetype, e.g. `lane: STORY (issuetype: Story)`):
      - **BUG**: Bug, Defect, Incident and similar.
      - **STORY**: Story, Improvement, Enhancement and similar user-facing work.
      - **TASK**: Task, Sub-task, Chore, Technical Task and similar. For a sub-task (`parent` set), also fetch the parent into `.jira-loop/<KEY>/parent.json` and pass both files as `TICKET`.
      - **EPIC**: don't run. Tell the user to split it into stories/tasks and run each one; implementing an epic in one autonomous pass is too much blast radius.
      - Anything else: TASK.

3. **LOCAL MODE:**
   a. Skip Jira entirely. Make a run key `LOCAL-<yyyymmdd-HHMMSS>` (`date +%Y%m%d-%H%M%S`).
   b. `mkdir -p .dev-loop/<KEY>` and put the description in `.dev-loop/<KEY>/ticket.md`: write the literal text (TEXT MODE) or `cp` the file (FILE MODE).
   c. With `--type`, give the planner that lane. Without it, tell the planner: "No type given — infer the lane (BUG if something is broken, STORY if it adds user-facing behavior, TASK otherwise) and state your choice and why first." Later roles detect the lane from which section the plan has (`ROOT_CAUSE` / `ACCEPTANCE_CRITERIA` / `DEFINITION_OF_DONE`).
   d. No parent or epic handling. If the description is too big or vague, that's for the planner's Open Questions.

4. `<WORKDIR>` is `.jira-loop/<KEY>/` or `.dev-loop/<KEY>/` in the repo root. `<TICKET>` means `ticket.json` (+ `parent.json`) or `ticket.md` in it. Every role writes there; it is the audit trail and what later roles read.

## LITE MODE (`--lite`)

For small, low-risk tickets. Same phases and files, with the expensive loops cut:
- **Phase 1:** planner once, told "LITE MODE", no planner-review. `plan-round-1.md` is the final plan.
- **Round numbers:** tell every role `round 1 of max 1 (LITE MODE)`.
- **Coverage:** pass the reviewer `COVERAGE_REPORT: none (LITE MODE) — the executor's tests are in the ## TESTS section of its report`. If the executor's reply says `COVERAGE: not measured`, report it that way; never an estimate.

- **Phase 2:** tell the executor "LITE MODE: also write the unit tests for your change". Still run qa-testcases alongside it.
- **Phase 3:** skipped; take coverage from the executor's reply.
- **Phase 4:** one reviewer round. On `REQUEST_CHANGES`, one executor fix pass with no re-review; record that.
- **Phase 6:** one qa-testing round, no retries. Failures go into the report with status `Needs manual follow-up`.
- **Phase 7/8:** tell final-review it was a LITE run and what was skipped; say so in the chat summary too.

## Phase 1 — Plan (planner ⇄ planner-review, max 2 rounds)
1. **planner**: `TICKET`, lane (or "infer the lane"), round, `OUTPUT_FILE: <WORKDIR>/plan-round-1.md`, `CONTEXT_FILE: <WORKDIR>/context.md` (it writes the file map there).
2. **planner-review**: `TICKET`, `PLAN: <WORKDIR>/plan-round-1.md`, `CONTEXT_FILE`, round, `OUTPUT_FILE: <WORKDIR>/review-round-1.md`.
3. `APPROVE` → the plan is final.
4. `REQUEST_CHANGES` and round < 2 → planner again with the previous plan and review paths, as a revision round, `OUTPUT_FILE: plan-round-2.md`; review it again (`review-round-2.md`).
5. No `APPROVE` after round 2 → use the round-2 plan anyway and record the unresolved feedback.
6. `cp` the final plan to `<WORKDIR>/plan-final.md`. If the cap was hit, append a note that review is still pending on N points. **JIRA MODE**: post it — `python3 <SKILL_DIR>/scripts/jira_client.py comment <KEY> --file <WORKDIR>/plan-final.md`.

## Phase 2 — Build + QA test cases (parallel)
The test cases come from the ticket and plan, not the code, so write them while the code is built:
1. **executor**: `TICKET`, `PLAN: <WORKDIR>/plan-final.md`, `CONTEXT_FILE`, `OUTPUT_FILE: <WORKDIR>/executor-1.md`.
2. **qa-testcases**: `TICKET`, `PLAN`, `KEY`, `OUTPUT_FILE: <WORKDIR>/qa-testcases.md`. It writes a CSV under `qa/` and replies with its path.

Wait for both. **JIRA MODE**: attach the sheet — `python3 <SKILL_DIR>/scripts/jira_client.py attach <KEY> <csv>`.

## Phase 3 — Coverage
**code-coverage**: `PLAN`, `CONTEXT_FILE`, `EXECUTOR_REPORT: <WORKDIR>/executor-1.md`, `OUTPUT_FILE: <WORKDIR>/coverage-1.md`.

## Phase 4 — Review (reviewer ⇄ executor, max 2 rounds)
1. **reviewer**: `TICKET`, `PLAN`, `CONTEXT_FILE`, the latest `EXECUTOR_REPORT` and `COVERAGE_REPORT`, `OUTPUT_FILE: <WORKDIR>/reviewer-round-1.md`.
2. `APPROVE` → Phase 6.
3. `REQUEST_CHANGES` and round < 2 → executor fix request pointing at the review file (fix every finding), `OUTPUT_FILE: executor-<next>.md`; re-run code-coverage only if the executor replied `LOGIC_CHANGED: yes`; then reviewer again with its previous review path and the new reports.
4. No `APPROVE` after round 2 → go on to Phase 6 and record the unresolved findings.

## Phase 6 — QA testing (max 2 rounds; routes to executor or planner)
1. **qa-testing**: `CSV`, `TICKET`, `PLAN`, `CONTEXT_FILE`, round, `OUTPUT_FILE: <WORKDIR>/qa-round-1.md`.
2. `RESULT: ALL_PASS` → Phase 7.
3. `FAILURES_FOUND` and rounds < 2 → route from the reply's `FAILURES:` line (run both kinds of fix in parallel when there are both):
   - `bug` failures: one executor fix request naming the case IDs and pointing at `qa-round-N.md`; then code-coverage (if `LOGIC_CHANGED: yes`) and one reviewer sanity pass — don't restart Phase 4's counter.
   - `plan-gap` failures: planner amends the plan from `plan-final.md` and `qa-round-N.md` and gets one planner-review pass; `cp` the new plan over `plan-final.md`; then executor (and coverage) for just the changed piece. The sheet already holds the failing cases, so don't rerun qa-testcases.
   - Re-run qa-testing on the same sheet (it updates pass/fail in place), `OUTPUT_FILE: qa-round-<next>.md`.
4. Failures left after round 2 → stop. Record exactly which cases still fail and why. Never mark the ticket done anyway.

(There is no Phase 5: QA test cases are written in Phase 2. Numbering matches the Claude Code version.)

## Phase 7 — Final report
**final-review**: `WORKDIR`, the CSV path, `OUTPUT_FILE: <WORKDIR>/final-comment.md`, and a short run summary from the replies you collected: rounds per loop, any cap hit and what's unresolved, LITE MODE and what it skipped, and single-agent mode if that's how you ran. Don't paste reports — it reads `<WORKDIR>`. **JIRA MODE**: post it — `python3 <SKILL_DIR>/scripts/jira_client.py comment <KEY> --file <WORKDIR>/final-comment.md`.

## Phase 8 — Tell the user
A short chat summary from final-review's reply (`STATUS`, `COVERAGE`, `QA`, `CAPS_HIT`): the ticket and link or the local run id, status (Ready for PR / Needs manual follow-up), coverage, QA pass rate, any cap hit, and lite or single-agent mode if used. If the repo's `.gitignore` doesn't already ignore `.jira-loop/`, `.dev-loop/` and `qa/`, mention that they're new untracked folders the user can ignore or keep. Point to `<WORKDIR>`, and in LOCAL MODE to `final-comment.md` and the QA CSV as the files to read first. If a Jira ticket is created later, the results can be posted to it: `python3 <SKILL_DIR>/scripts/jira_client.py comment <REAL-KEY> --file <WORKDIR>/final-comment.md`.

## Ground rules
- Roles start with no memory, so every call names every file the role needs (ticket, plan, relevant reports, previous-round files on re-runs) plus lane and round.
- Output files keep counting across phases (`executor-3.md` after `executor-2.md`, and so on). Never overwrite an earlier round — the trail is the audit record.
- Only you talk to Jira, through the script, and only in JIRA MODE. If the script errors, surface the exact error; retry at most once.
- The pipeline never commits, pushes or opens PRs. It edits the working tree; the user reviews `git diff` and commits. Suggest running on a clean branch.
- Be honest everywhere: a hit cap, a skipped edge case, or a failing QA case must be visible in the report and the summary, never smoothed over.
