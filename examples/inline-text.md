# Inline text prompts

No ticket and no file: just describe the work in one line. Each of these
runs against the [playground app](playground-app/). Paste one into Claude
Code, opened inside your copy of the app.

## Let the planner pick the lane

With no `--type`, the planner decides BUG / STORY / TASK itself and puts its
choice and reasoning on the first line of `plan-final.md`. It's a good way to
see how it reads intent.

```text
/jira-loop --text "An order of exactly $100.00 is charged full price, but the promo says $100 or more gets 10% off."
```
→ should infer **BUG** ("describes current behavior that is wrong").

```text
/jira-loop --text "Let shoppers apply a coupon code: SAVE10 for 10% off, FLAT5 for $5 off. Total can never go negative."
```
→ should infer **STORY** ("new user-facing behavior").

```text
/jira-loop --text "Replace float money math in cart.py with decimal.Decimal rounded to cents. Keep all existing tests green."
```
→ should infer **TASK** ("internal change, no new user-facing behavior").

## Force the lane with `--type`

```text
/jira-loop --text "Cart.remove() raises a raw KeyError for an unknown SKU; it should raise ValueError with the SKU in the message." --type bug
/jira-loop --text "Add Cart.clear() that empties the cart and resets any discount state." --type story
/jira-loop --text "Add type hints to every public method in cart.py and make mypy --strict pass." --type task
```

## Experiments worth trying

| Try this | What to look for |
|---|---|
| A deliberately vague prompt: `--text "make the cart better"` | The planner should list real questions under `OPEN_QUESTIONS` and report low `CONFIDENCE` instead of inventing scope |
| A conflicting prompt: `--text "Add a coupon that can make totals negative"` | Whether planner-review pushes back over its rounds |
| The same prompt twice | Each run gets its own `.dev-loop/LOCAL-<timestamp>/` folder, so you can diff the two plans |
| A bug report with no repro steps | The BUG lane should flag the missing repro rather than guess one |

## Where the output goes

```
.dev-loop/LOCAL-20260925-143012/
├── plan-round-1.md
├── review-round-1.md
├── plan-final.md        ← read this first
├── executor-1.md
├── coverage-1.md
├── reviewer-round-1.md
└── final-comment.md     ← and this
qa/LOCAL-20260925-143012-test-cases.csv
```

Nothing is posted anywhere. If you create a real ticket later, you can send
the write-ups to it without rerunning anything:

```bash
python3 .claude/scripts/jira_client.py comment PROJ-42 --file .dev-loop/LOCAL-20260925-143012/final-comment.md
```
