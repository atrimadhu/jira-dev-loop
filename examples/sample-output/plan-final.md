## LANE_CHOSEN
BUG: the description states current behavior ("Actual: 100.00") that contradicts a stated promise ("Expected: 90.00").

## ROOT_CAUSE
**Repro:** `Cart()` → `add("A1", "Desk Lamp", 50.00, qty=2)` → `total()` returns `100.0`, expected `90.0`.

**Mechanism:** `cart.py`, `Cart.discount()`:

```python
if subtotal > BULK_DISCOUNT_THRESHOLD:
```

The promo is "$100 **or more**", so the comparison must be inclusive. With a
subtotal of exactly `100.0`, `>` is `False` and the method returns `0.0`.

**Blast radius:** `Cart.discount()` is called only by `Cart.total()`. Nothing
else reads `BULK_DISCOUNT_THRESHOLD`. Code paths to regression-check:
- subtotal below threshold (99.99) → no discount (unchanged)
- subtotal above threshold (150.00) → 10% discount (unchanged)
- empty cart → 0.00 (unchanged)

## PLAN
**Approach:** Change `>` to `>=` in `Cart.discount()`. One-character fix, no
other changes. It is a root-cause fix, not a workaround in `total()`.

**Reliability:** Pure function over in-memory state, no I/O and no new
failure modes.

**Performance & high traffic:** No change. O(n) over cart items, same as before.

**Edge cases:**
1. Subtotal exactly 100.00 → discount 10.00, total 90.00 *(the repro)*
2. Subtotal 99.99 → no discount *(regression)*
3. Subtotal 100.01 → discount applied *(regression)*
4. Empty cart → 0.00 *(regression)*
5. Threshold reached through several line items (40 + 60) → discount applied

**File-level changes:** `cart.py` (1 line), `test_cart.py` (new tests).

**Testing strategy:** Unit tests in `test_cart.py` for edge cases 1–5. Case 1
is the regression test for this ticket and must fail before the fix and pass
after it.

## OPEN_QUESTIONS
None. The expected behavior is stated explicitly in the report.

## CONFIDENCE
97%. Would be 100% with confirmation that float drift is out of scope: 5 ×
$19.99 + $0.05 evaluates to `99.99999999999999` and still misses the
discount. That belongs to the separate Decimal money task.
