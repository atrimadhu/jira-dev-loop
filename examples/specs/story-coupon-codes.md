# Story: Apply a coupon code to the cart

**As a** shopper
**I want to** enter a coupon code at checkout
**So that** I get the discount a promotion email promised me

## Context

`cart.py` only knows one discount today: the automatic 10% bulk discount for
orders of $100 or more. Marketing wants to run coupon campaigns.

Coupons for launch (hard-coded is fine, no database):

| Code | Effect |
|---|---|
| `SAVE10` | 10% off the subtotal |
| `FLAT5` | $5.00 off the subtotal |

## Acceptance Criteria

1. `Cart.apply_coupon(code)` accepts a known code and it is reflected in `total()`.
2. Codes are case-insensitive and ignore surrounding whitespace (`" save10 "` works).
3. An unknown code raises `ValueError` with a message that names the code, and leaves the cart unchanged.
4. Only one coupon at a time — applying a second one replaces the first.
5. `Cart.remove_coupon()` removes the active coupon; calling it with none active is a no-op.
6. A coupon never makes the total negative — `FLAT5` on a $3.00 cart totals $0.00.
7. Coupon and bulk discount do not stack: the customer gets whichever is larger.

## Out of scope

- Coupon expiry dates, usage limits, per-customer codes.
- Persisting coupons anywhere.
