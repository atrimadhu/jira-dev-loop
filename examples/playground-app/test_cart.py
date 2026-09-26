import unittest

from cart import Cart


class CartTest(unittest.TestCase):
    def test_empty_cart_totals_zero(self):
        self.assertEqual(Cart().total(), 0.0)

    def test_add_merges_same_sku(self):
        cart = Cart()
        cart.add("A1", "Mug", 8.0)
        cart.add("A1", "Mug", 8.0, qty=2)
        self.assertEqual(cart.item_count(), 3)
        self.assertEqual(cart.subtotal(), 24.0)

    def test_rejects_non_positive_qty(self):
        with self.assertRaises(ValueError):
            Cart().add("A1", "Mug", 8.0, qty=0)

    def test_small_order_has_no_discount(self):
        cart = Cart()
        cart.add("A1", "Mug", 20.0, qty=2)
        self.assertEqual(cart.total(), 40.0)

    def test_large_order_gets_bulk_discount(self):
        cart = Cart()
        cart.add("B2", "Kettle", 150.0)
        self.assertEqual(cart.total(), 135.0)


if __name__ == "__main__":
    unittest.main()
