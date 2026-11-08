from decimal import Decimal

from django.test import SimpleTestCase

from .settlement import position_profit_loss


class PositionProfitLossTest(SimpleTestCase):
    def test_direction_and_rounding(self):
        outcome = Decimal('90.01')
        self.assertEqual(position_profit_loss('LONG', 90, outcome, '1.01'), Decimal('0.02'))
        self.assertEqual(position_profit_loss('SHORT', 90, outcome, '1.01'), Decimal('-0.02'))
