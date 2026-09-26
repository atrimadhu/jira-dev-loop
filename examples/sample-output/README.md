# Sample output

These are **illustrative, abridged** artifacts showing what a run of

```text
/jira-loop --file ../specs/bug-bulk-discount-boundary.txt
```

against the playground app produces. They follow the exact formats the
agents are instructed to emit. Your own run's wording will differ, but the
structure won't.

| File | Produced by | What it is |
|---|---|---|
| [`plan-final.md`](plan-final.md) | `jira-planner` + `jira-planner-review` | The agreed plan, with root cause and blast radius |
| [`qa-test-cases.csv`](qa-test-cases.csv) | `jira-qa-testcases` → `jira-qa-testing` | The QA sheet, with pass/fail filled in |
| [`final-comment.md`](final-comment.md) | `jira-final-review` | The closing report (posted to Jira in ticket mode) |
