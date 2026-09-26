## Summary
An order with a subtotal of exactly $100.00 was not receiving the advertised
"$100 or more" 10% bulk discount.

## What was implemented
- `cart.py`: `Cart.discount()` now uses an inclusive comparison
  (`subtotal >= BULK_DISCOUNT_THRESHOLD`). One line changed.
- `test_cart.py`: 4 new tests covering the exact threshold, just under,
  just over, and reaching the threshold across multiple line items.

## Plan
Minimal root-cause fix, approved by planner-review in round 1 of 3.
**Root cause:** `>` instead of `>=` in `Cart.discount()`.
**Blast radius:** `Cart.total()` is the only caller; below-, above-threshold
and empty-cart paths were regression-tested.

## Coverage
100% of changed lines (1/1); `cart.py` overall 94%.

## QA Results
7 / 7 passed (4 × P0, 3 × P1). No failures in any round.
- **Original reproduction case (TC-01): PASS.** $100.00 now totals $90.00.
- **All regression cases around the fix (TC-02, TC-03, TC-04, TC-07): PASS.**

## Deviations & Follow-ups
- Reviewer approved in round 1 of 3; QA passed in round 1 of 3. **No retry cap was hit.**
- **Follow-up needed (out of scope here):** float arithmetic can still miss
  the threshold. 5 × $19.99 + $0.05 sums to `99.99999999999999`, so that cart
  gets no discount. Fix it with the separate Decimal money task.

## Status
**Ready for PR**
