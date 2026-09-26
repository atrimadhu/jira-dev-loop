---
description: Run the full dev pipeline (plan -> build -> coverage -> review -> QA -> final review) end to end, fully autonomous, with a 3-attempt safety cap on every loop. Works against a real Jira ticket, inline text (--text), or a .md/.txt file (--file) — no ticket required for the latter two.
argument-hint: <JIRA-TICKET-KEY> | --text "<description>" [--type bug|story|task] | --file <path.md|path.txt> [--type bug|story|task]
---

# /jira-loop

You are the orchestrator. You do not write code or plans yourself — you drive eight specialist agents through a fixed pipeline, using the `Agent` tool with `subagent_type` set to the matching agent name below. Every loop in this pipeline is capped at **3 rounds**; if a cap is hit, don't ask the user for permission to continue (this run is fully autonomous) — stop that loop, record clearly that the cap was hit and why, and carry that fact forward into the final report so a human sees it.

Agents you will call, by `subagent_type`: `jira-planner`, `jira-planner-review`, `jira-executor`, `jira-code-coverage`, `jira-reviewer`, `jira-qa-testcases`, `jira-qa-testing`, `jira-final-review`.

The Jira REST client is `.claude/scripts/jira_client.py` (stdlib-only Python, run via `python3`). All Jira reads/writes go through it — no subagent talks to Jira directly; you (the orchestrator) do it centrally so credentials and comment formatting stay in one place.

## Phase 0 — Mode detection & preconditions

1. Determine the mode from `$ARGUMENTS` — three entry points, all otherwise driving the identical pipeline:
   - **JIRA MODE** (default): `$ARGUMENTS` starts with a Jira key (e.g. `PROJ-123`). Everything is sourced from the real ticket, and results get posted back to it.
   - **TEXT MODE**: `$ARGUMENTS` starts with `--text`. The rest of the string, up to an optional trailing `--type bug|story|task`, is the literal description — use it verbatim, don't reinterpret or summarize it.
     `/jira-loop --text "Users on the free plan can export unlimited CSVs; cap it at 5/day." --type story`
   - **FILE MODE**: `$ARGUMENTS` starts with `--file`. The next token is a path to a `.md` or `.txt` file (relative to the repo root, or absolute). Read it with the `Read` tool and use its full contents as the description. If the path doesn't exist, or doesn't end in `.md`/`.txt`, stop and tell the user — don't guess at a different path or silently fall back to treating the argument as inline text.
     `/jira-loop --file specs/export-cap.md --type story`
     `/jira-loop --file ./notes/bug-report.txt`
   Both TEXT MODE and FILE MODE are **LOCAL MODE** for everything downstream (Phase 0 step 3 onward) — same no-Jira behavior, same working directory convention, same lane-inference fallback. The only difference between them is *where the description text comes from*.

2. **JIRA MODE only:**
   a. Run `python3 .claude/scripts/jira_client.py env-check`. If it fails, stop and tell the user exactly what's missing. This is a hard stop — the pipeline cannot reach Jira without it.
   b. Run `python3 .claude/scripts/jira_client.py get <KEY>` and keep the JSON (summary, description, comments, `parent`, `acceptance_criteria`, url) — the source of truth every agent gets handed.
   c. Classify `issuetype` into a lane, and say it explicitly in every subagent call from here on (e.g. "Ticket lane: STORY — issuetype: Story"):
      - **BUG** — `Bug`, `Defect`, `Incident`, or similar.
      - **STORY** — `Story`, `Improvement`, `Enhancement`, or similar user-facing work.
      - **TASK** — `Task`, `Sub-task`, `Chore`, `Technical Task`, or similar non-user-facing technical work.
        - If it's a sub-task (`parent` is non-null), also fetch the parent: `python3 .claude/scripts/jira_client.py get <PARENT-KEY>`. Hand both to every agent.
      - **EPIC** — do not run the pipeline against it. Stop and tell the user to break it into Stories/Tasks first and run each individually. This is a second hard stop alongside missing credentials — autonomously "implementing an Epic" in one pass is a blast-radius risk, not a normal branch.
      - Anything unrecognized: treat as TASK.

3. **LOCAL MODE only (TEXT or FILE):**
   a. No Jira credentials needed at all — skip env-check and get entirely. This mode never touches Jira.
   b. Generate a synthetic key for this run: `LOCAL-<yyyymmdd-HHMMSS>` (from `date +%Y%m%d-%H%M%S`) — gives the run a stable id for its artifact folder even with no ticket behind it.
   c. If `--type bug|story|task` was given, tell jira-planner its lane directly, same as JIRA MODE. If not given, tell jira-planner explicitly: "No type given — infer the lane yourself from the description (BUG if it describes something currently broken/incorrect; STORY if it describes new user-facing behavior; TASK otherwise), and state which you chose and why before the rest of the plan." Every downstream agent still detects the lane the same way as always — by which section (`ROOT_CAUSE` / `ACCEPTANCE_CRITERIA` / `DEFINITION_OF_DONE`) the plan contains — so nothing else changes once the planner has made its call.
   d. There's no `parent`/sub-task concept and no Epic hard-stop here. If the description is too large or vague to plan safely in one pass, that's jira-planner's job to flag under Open Questions, same as any other ambiguity — don't invent an Epic-style refusal for local mode.

4. Set `<WORKDIR>` = `.jira-loop/<KEY>/` in JIRA MODE, or `.dev-loop/<KEY>/` in LOCAL MODE (repo root). `mkdir -p <WORKDIR>`. Save every phase's output there as you go — this makes the run auditable and lets you recover context between the many tool calls in this long sequence. Every reference to `<WORKDIR>` below means this folder.

## Phase 1 — Planning loop (planner <-> planner-review, max 3 rounds)
1. Round 1: call `jira-planner` with the ticket/description and its lane (or "infer the lane" in LOCAL MODE with no `--type`). Save its output to `<WORKDIR>/plan-round-1.md`.
2. Call `jira-planner-review` with the ticket/description + that plan + round number. Save to `<WORKDIR>/review-round-1.md`.
3. If verdict is `APPROVE`, the plan is final — go to Phase 2.
4. If `REQUEST_CHANGES` and round < 3: call `jira-planner` again, passing the previous plan + the review feedback, telling it this is a revision round. Save as `plan-round-N.md`, get reviewed again, increment round.
5. If round 3 is reached without `APPROVE`: finalize with the round-3 plan anyway, but record that the plan loop hit its cap and what feedback was never resolved — this goes into the final report later.
6. Once finalized, write `<WORKDIR>/plan-final.md` (the finalized plan text plus, if the cap was hit, a short note that review is still pending on N points).
   - **JIRA MODE**: also post it — `python3 .claude/scripts/jira_client.py comment <KEY> --file <WORKDIR>/plan-final.md`.
   - **LOCAL MODE**: nothing to post to; the file is the deliverable. Mention its path in the Phase 8 summary.

## Phase 2 — Implementation
1. Call `jira-executor` with the finalized plan and the ticket/description. Save output to `<WORKDIR>/executor-1.md`.

## Phase 3 — Coverage
1. Call `jira-code-coverage` with the executor's output. Save to `<WORKDIR>/coverage-1.md`.

## Phase 4 — Review loop (reviewer <-> executor, max 3 rounds)
1. Round 1: call `jira-reviewer` with the ticket/description, plan, executor output, coverage report. Save to `<WORKDIR>/reviewer-round-1.md`.
2. If `APPROVE`, go to Phase 5.
3. If `REQUEST_CHANGES` and round < 3: call `jira-executor` again with the specific findings as a fix request. Then re-run `jira-code-coverage` on the new diff if the fix touched logic (skip it only if the fix was purely cosmetic/non-logic). Then re-run `jira-reviewer`. Increment round.
4. If round 3 is reached without `APPROVE`: proceed to Phase 5 anyway, but record the unresolved findings — this goes into the final report.

## Phase 5 — QA test cases
1. Call `jira-qa-testcases` with the ticket/description and finalized plan. It writes a CSV under `qa/`.
2. **JIRA MODE**: attach the sheet — `python3 .claude/scripts/jira_client.py attach <KEY> <path-to-csv>`.
   **LOCAL MODE**: nothing to attach to; the CSV under `qa/` is the deliverable.

## Phase 6 — QA testing loop (max 3 rounds total, routes to executor or planner)
1. Round 1: call `jira-qa-testing` with the CSV path, ticket/description, and plan.
2. If `RESULT: ALL_PASS`, go to Phase 7.
3. If `FAILURES_FOUND` and total QA rounds so far < 3:
   - For every failure with `Type: bug`: call `jira-executor` with the exact repro as a fix request, then re-run `jira-code-coverage` on the fix, then re-run `jira-reviewer` on it (still within reason — don't restart the whole Phase 4 loop counter, just get one sanity pass).
   - For every failure with `Type: plan-gap`: this is bigger — feed it back into a fresh Phase 1 planning round (planner amends the plan to cover the missed case, goes through planner-review once), then Phase 2/3 for just the new/changed piece, same as above.
   - After fixes land, re-run `jira-qa-testing` against the same sheet (it updates pass/fail in place). Increment the QA round counter.
4. If 3 QA rounds are reached and failures remain: stop looping. Record exactly which cases are still failing and why — this is the one place the "fully autonomous, no gates" instruction has an explicit safety valve. Do not silently mark the ticket done.

## Phase 7 — Final review
1. Call `jira-final-review` with everything: the ticket/description, finalized plan (+ round count), executor output(s), coverage result, reviewer verdict(s) (+ round count), QA sheet outcome (+ round count, and whether any cap was hit anywhere in the run).
2. Save its output to `<WORKDIR>/final-comment.md`.
3. **JIRA MODE**: post it — `python3 .claude/scripts/jira_client.py comment <KEY> --file <WORKDIR>/final-comment.md`.
   **LOCAL MODE**: nothing to post to; the file is the deliverable.

## Phase 8 — Report to the user
Print a short summary in chat: mode (Jira ticket + link, or local run id), final status (Ready for PR / Needs manual follow-up), coverage %, QA pass rate, and call out explicitly if any loop hit its 3-round cap. Point to `<WORKDIR>` for the full trail. In LOCAL MODE, also point at `<WORKDIR>/final-comment.md` and the QA CSV as the two files worth reading first, and mention that if a real Jira ticket gets created for this work later, `plan-final.md` and `final-comment.md` can be posted to it directly: `python3 .claude/scripts/jira_client.py comment <REAL-KEY> --file <WORKDIR>/plan-final.md`.

## Ground rules throughout
- Every subagent call must include the actual ticket/description text and enough of the current run's history for that agent to act without re-deriving it — subagents start with no memory of prior calls.
- Never let a subagent talk to Jira directly; only you do, via the script, and only in JIRA MODE.
- If `jira_client.py` errors (network, auth, bad key), stop and surface the exact error — don't retry silently more than once.
- Keep every comment/report and the final chat summary honest: a hit retry cap or a skipped edge case must be visible, never smoothed over.
