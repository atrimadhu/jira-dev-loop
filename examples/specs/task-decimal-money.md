# Task: Stop using float for money in cart.py

`cart.py` stores prices as `float`, so arithmetic drifts:

```python
cart.add("A1", "Sticker", 0.10, qty=3)
cart.subtotal()   # 0.30000000000000004
```

`total()` papers over it with `round(..., 2)`, but `subtotal()` and
`discount()` leak the raw float, and rounding happens at the wrong step.

## What to do

Switch money handling in `cart.py` to `decimal.Decimal`, quantized to cents
with `ROUND_HALF_UP`.

## Definition of Done

- `Item.unit_price`, `Item.line_total`, `Cart.subtotal()`, `Cart.discount()`
  and `Cart.total()` all return `Decimal` values with exactly 2 decimal places.
- `Cart.add()` still accepts `int`, `float` or `str` prices and converts them
  once, at the boundary (`Decimal(str(value))`, not `Decimal(float)`).
- `0.10 x 3` gives a subtotal of exactly `Decimal("0.30")`.
- Every existing test in `test_cart.py` still passes, with assertions updated
  to compare against `Decimal`.
- No new third-party dependencies — stdlib only.
