# Playground app

A 50-line shopping cart with a few problems planted in it, so you can watch
`/jira-loop` work on something real without pointing it at your own code
first.

```bash
python3 -m unittest -v    # 5 tests, all green — the bugs are in what they don't test
```

| What's planted | Kind | Spec to hand to `/jira-loop` |
|---|---|---|
| An order of exactly $100.00 gets no bulk discount | Bug | [`../specs/bug-bulk-discount-boundary.txt`](../specs/bug-bulk-discount-boundary.txt) |
| No way to apply a coupon code | Story | [`../specs/story-coupon-codes.md`](../specs/story-coupon-codes.md) |
| Money math uses `float` (`0.1 * 3 == 0.30000000000000004`) | Task | [`../specs/task-decimal-money.md`](../specs/task-decimal-money.md) |

Copy this folder somewhere else before running the pipeline on it, so the
original stays clean for the next try. [`../../docs/PLAYGROUND.md`](../../docs/PLAYGROUND.md)
walks through each step.
