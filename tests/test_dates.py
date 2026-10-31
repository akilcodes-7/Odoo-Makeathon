from datetime import date

from django.test import SimpleTestCase

from core.models import Subscription
from core.services.dates import add_period, period_for_index, period_index_for_date


class BillingDateTests(SimpleTestCase):
    def test_month_end_is_anchored_to_original_date(self):
        anchor = date(2024, 1, 31)
        self.assertEqual(add_period(anchor, Subscription.Period.MONTHLY, 1), date(2024, 2, 29))
        self.assertEqual(add_period(anchor, Subscription.Period.MONTHLY, 2), date(2024, 3, 31))

    def test_leap_day_yearly_anchor_returns_in_leap_year(self):
        anchor = date(2024, 2, 29)
        self.assertEqual(add_period(anchor, Subscription.Period.YEARLY, 1), date(2025, 2, 28))
        self.assertEqual(add_period(anchor, Subscription.Period.YEARLY, 4), date(2028, 2, 29))

    def test_terminal_period_is_clipped_with_inclusive_expiry(self):
        period = period_for_index(
            date(2024, 1, 31), Subscription.Period.MONTHLY, 1, date(2024, 3, 5)
        )
        self.assertEqual(period.start, date(2024, 2, 29))
        self.assertEqual(period.end, date(2024, 3, 6))
        self.assertEqual(period.nominal_days, 31)
        self.assertEqual(period.actual_days, 6)

    def test_index_uses_anchor_not_clamped_boundary(self):
        self.assertEqual(
            period_index_for_date(date(2024, 1, 31), Subscription.Period.MONTHLY, date(2024, 3, 30)),
            1,
        )
