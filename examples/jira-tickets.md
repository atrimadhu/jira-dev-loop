# Jira tickets to create for the playground

Create these three tickets in any Jira project you can write to (a throwaway
project named `PLAY` works well), then run `/jira-loop PLAY-<n>` against the
[playground app](playground-app/).

The **Issue type** is what matters most: it picks the pipeline lane
automatically (Bug → root-cause analysis, Story → acceptance criteria, Task →
definition of done).

---

## Ticket 1 (Bug)

| Field | Value |
|---|---|
| Issue type | **Bug** |
| Summary | Order of exactly $100.00 does not get the 10% bulk discount |
| Priority | High |

**Description** (paste as-is):

```
Our promo says "Spend $100 or more and get 10% off". An order of exactly
$100.00 is charged full price.

Steps to reproduce:
1. Create an empty Cart.
2. Add sku "A1", "Desk Lamp", unit_price 50.00, qty 2.
3. Call cart.total().

Expected: 90.00
Actual: 100.00

Orders above $100 and below $100 behave correctly. Only the exact
threshold is wrong.
```

Run: `/jira-loop PLAY-1`

---

## Ticket 2 (Story)

| Field | Value |
|---|---|
| Issue type | **Story** |
| Summary | Shopper can apply a coupon code to the cart |
| Priority | Medium |

**Description** (paste as-is):

```
As a shopper I want to enter a coupon code so I get the discount a promo
email promised me.

Launch codes (hard-coded is fine):
- SAVE10: 10% off subtotal
- FLAT5: $5.00 off subtotal

Acceptance Criteria
- [ ] Cart.apply_coupon(code) accepts a known code and total() reflects it
- [ ] Codes are case-insensitive and whitespace-trimmed
- [ ] Unknown code raises ValueError naming the code; cart unchanged
- [ ] One coupon at a time; a second one replaces the first
- [ ] Cart.remove_coupon() removes it; no-op when none active
- [ ] Total never goes below $0.00
- [ ] Coupon and bulk discount don't stack; the larger one wins

Out of scope: expiry, usage limits, persistence.
```

If your Jira has a dedicated Acceptance Criteria field, put the checklist
there instead and set `JIRA_ACCEPTANCE_CRITERIA_FIELD` in
`.claude/jira-loop.env`.

Run: `/jira-loop PLAY-2`

---

## Ticket 3 (Task)

| Field | Value |
|---|---|
| Issue type | **Task** |
| Summary | Replace float money math in cart.py with Decimal |
| Priority | Low |

**Description** (paste as-is):

```
cart.py uses float for prices, so 0.10 x 3 = 0.30000000000000004.
Switch to decimal.Decimal quantized to cents (ROUND_HALF_UP).

Definition of Done
- unit_price, line_total, subtotal(), discount(), total() return Decimal with 2 dp
- add() still accepts int/float/str and converts once via Decimal(str(value))
- 0.10 x 3 gives exactly Decimal("0.30")
- all existing tests pass (assertions updated to Decimal)
- no new third-party dependencies
```

Run: `/jira-loop PLAY-3`

---

## Bonus: try the two guardrails

- **Create an Epic** and run `/jira-loop` on it. The pipeline refuses in Phase
  0 and tells you to split it into Stories/Tasks. That refusal is intended.
- **Create a Sub-task under Ticket 2** (e.g. "Add remove_coupon()"). The
  pipeline fetches the parent Story too, so the sub-task is planned in the
  context of the parent's acceptance criteria.
