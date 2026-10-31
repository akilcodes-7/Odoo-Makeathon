from decimal import Decimal

from django.test import SimpleTestCase

from core.services.money import decimal_to_paise, format_paise, prorate_paise, tax_paise


class MoneyTests(SimpleTestCase):
    def test_decimal_rupees_convert_without_float(self):
        self.assertEqual(decimal_to_paise("560.00"), 56_000)
        self.assertEqual(decimal_to_paise(Decimal("0.01")), 1)

    def test_rejects_excess_precision_negative_and_float(self):
        for value in ("1.001", "-1", "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decimal_to_paise(value)
        with self.assertRaises(TypeError):
            decimal_to_paise(1.0)

    def test_proration_and_tax_use_half_up(self):
        self.assertEqual(prorate_paise(10, 1, 4), 3)
        self.assertEqual(tax_paise(18_000, 1_800), 3_240)

    def test_display_uses_rupees_not_raw_paise(self):
        self.assertEqual(format_paise(123_456), "₹1,234.56")
