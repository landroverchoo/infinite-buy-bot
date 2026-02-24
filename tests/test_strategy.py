"""
무한매수법 전략 테스트
"""
import unittest
from src.strategy import InfiniteBuyStrategy


class TestInfiniteBuyStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = InfiniteBuyStrategy(
            total_investment=1000000,
            divisions=20,
            target_profit_pct=5.0,
            use_loc=False
        )

    def test_initial_buy(self):
        """1회차 매수는 무조건 1배"""
        rec = self.strategy.execute_buy("2024-01-01", 100.0, 100.0)
        self.assertEqual(rec.round_num, 1)
        self.assertEqual(rec.shares, 500.0)  # 1,000,000 / 20 / 100
        self.assertEqual(rec.amount, 50000.0)  # unit_amount = 50,000

    def test_buy_multiplier_below_avg(self):
        """평단 이하 → 2배 매수"""
        self.strategy.execute_buy("2024-01-01", 100.0, 100.0)  # 평단 100
        rec = self.strategy.execute_buy("2024-01-02", 90.0, 100.0)
        self.assertEqual(rec.round_num, 2)
        self.assertEqual(rec.amount, 100000.0)  # 2배 = 100,000

    def test_buy_multiplier_above_avg(self):
        """평단 초과 → 1배 매수"""
        self.strategy.execute_buy("2024-01-01", 100.0, 100.0)  # 평단 100
        rec = self.strategy.execute_buy("2024-01-02", 110.0, 100.0)
        self.assertEqual(rec.round_num, 2)
        self.assertEqual(rec.amount, 50000.0)  # 1배 = 50,000

    def test_sell_condition(self):
        """평단 +5% 이상 → 매도"""
        self.strategy.execute_buy("2024-01-01", 100.0, 100.0)
        self.assertFalse(self.strategy.should_sell(104.0))  # 105 미만
        self.assertTrue(self.strategy.should_sell(105.0))   # 100 * 1.05
        self.assertTrue(self.strategy.should_sell(110.0))

    def test_sell_resets_cycle(self):
        """매도 후 새 사이클"""
        self.strategy.execute_buy("2024-01-01", 100.0, 100.0)
        rec = self.strategy.execute_sell("2024-01-02", 105.0)
        self.assertEqual(rec.cycle, 1)
        self.assertEqual(self.strategy.cycle, 2)  # 새 사이클
        self.assertEqual(self.strategy.position.round_num, 0)  # 회차 리셋
        self.assertEqual(self.strategy.position.total_shares, 0.0)

    def test_loc_price(self):
        """LOC 지정가 = 전일종가 * (1 - 할인율)"""
        self.strategy.use_loc = True
        self.strategy.loc_discount_pct = 1.0
        price = self.strategy.get_buy_price(100.0, 100.0)
        self.assertEqual(price, 99.0)  # 100 * 0.99

if __name__ == '__main__':
    unittest.main()
