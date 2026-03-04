"""
무한매수법 V3.0 전략 테스트
"""
import unittest
import math
from src.strategy import InfiniteBuyStrategyV3, Position, STAR_CONFIG


class TestPosition(unittest.TestCase):
    """Position 데이터 클래스 테스트"""

    def test_avg_price_zero_shares(self):
        pos = Position()
        self.assertEqual(pos.avg_price, 0.0)

    def test_avg_price(self):
        pos = Position(total_shares=100.0, total_cost=10000.0)
        self.assertEqual(pos.avg_price, 100.0)

    def test_reset(self):
        pos = Position(round_num=5, total_shares=100.0, total_cost=5000.0,
                       remaining_budget=5000.0, cumulative_buy_amount=5000.0)
        pos.reset(10000.0)
        self.assertEqual(pos.round_num, 0)
        self.assertEqual(pos.total_shares, 0.0)
        self.assertEqual(pos.total_cost, 0.0)
        self.assertEqual(pos.remaining_budget, 10000.0)
        self.assertEqual(pos.cumulative_buy_amount, 0.0)


class TestStrategyInit(unittest.TestCase):
    """전략 초기화 테스트"""

    def test_default_tqqq(self):
        s = InfiniteBuyStrategyV3(total_investment=1000000, divisions=40, ticker="TQQQ")
        self.assertEqual(s.divisions, 40)
        self.assertEqual(s.unit_amount, 25000.0)  # 1,000,000 / 40
        self.assertEqual(s.star_base, 15)
        self.assertEqual(s.star_coeff, 1.5)
        self.assertEqual(s.cycle, 1)

    def test_soxl_config(self):
        s = InfiniteBuyStrategyV3(total_investment=1000000, divisions=40, ticker="SOXL")
        self.assertEqual(s.star_base, 20)
        self.assertEqual(s.star_coeff, 2.0)

    def test_invalid_divisions(self):
        with self.assertRaises(ValueError):
            InfiniteBuyStrategyV3(total_investment=1000000, divisions=25)


class TestTValueAndStarPct(unittest.TestCase):
    """T 값 및 별% 계산 테스트"""

    def setUp(self):
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

    def test_initial_t_value(self):
        """초기 T=0"""
        self.assertEqual(self.strategy.calc_t(), 0.0)

    def test_initial_star_pct(self):
        """초기 별% = 15 (TQQQ)"""
        self.assertEqual(self.strategy.calc_star_pct(), 15.0)

    def test_t_after_one_buy(self):
        """1회 매수 후 T 계산 (소수점 둘째자리 올림)"""
        # 1회 매수금 = 25,000
        self.strategy.position.cumulative_buy_amount = 25000.0
        t = self.strategy.calc_t()
        # T = 25000 / 25000 = 1.0
        self.assertEqual(t, 1.0)

    def test_star_pct_after_buys(self):
        """T=5 일때 별% = 15 - 1.5*5 = 7.5"""
        self.strategy.position.cumulative_buy_amount = 125000.0  # 5 * 25000
        self.assertEqual(self.strategy.calc_star_pct(), 7.5)

    def test_star_pct_at_t10(self):
        """T=10 에서 별% = 0 → 전후반전 전환"""
        self.strategy.position.cumulative_buy_amount = 250000.0  # 10 * 25000
        self.assertEqual(self.strategy.calc_star_pct(), 0.0)

    def test_is_first_half(self):
        """별% > 0 이면 전반전"""
        self.assertTrue(self.strategy.is_first_half())

    def test_is_second_half(self):
        """별% <= 0 이면 후반전"""
        self.strategy.position.cumulative_buy_amount = 250000.0  # T=10
        self.assertFalse(self.strategy.is_first_half())

    def test_t_ceiling(self):
        """T 소수점 둘째자리 올림 테스트"""
        # 12345 / 25000 = 0.4938 → ceil(49.38)/100 = 0.50
        self.strategy.position.cumulative_buy_amount = 12345.0
        t = self.strategy.calc_t()
        expected = math.ceil(12345.0 / 25000.0 * 100) / 100
        self.assertEqual(t, expected)


class TestLOCPrice(unittest.TestCase):
    """LOC 가격 계산 테스트"""

    def setUp(self):
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

    def test_zero_pct_loc(self):
        """0%LOC = 전일 종가"""
        self.assertEqual(self.strategy.loc_price(100.0, 0), 100.0)

    def test_positive_pct_loc(self):
        """5%LOC = 전일종가 * 0.95"""
        self.assertAlmostEqual(self.strategy.loc_price(100.0, 5), 95.0)

    def test_star_pct_loc(self):
        """별%LOC 가격"""
        # 초기 별% = 15 → LOC = 100 * (1 - 15/100) = 85
        star_pct = self.strategy.calc_star_pct()
        loc = self.strategy.loc_price(100.0, star_pct)
        self.assertAlmostEqual(loc, 85.0)


class TestDailyBuy(unittest.TestCase):
    """일일 매수 로직 테스트"""

    def setUp(self):
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

    def test_first_buy_first_half(self):
        """전반전 첫 매수: 별%LOC + 0%LOC 2건"""
        records = self.strategy.execute_daily_buy(
            date="2024-01-01",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=80.0,  # 저가가 별%LOC 이하
            close=100.0,
        )
        # 전반전: 절반 별%LOC + 절반 0%LOC = 2건
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].action, "buy_star")
        self.assertEqual(records[1].action, "buy_zero")
        # 각 절반 금액 = 25000 / 2 = 12500
        self.assertAlmostEqual(records[0].amount, 12500.0)
        self.assertAlmostEqual(records[1].amount, 12500.0)

    def test_first_half_star_loc_not_filled(self):
        """전반전: 저가가 별%LOC보다 높으면 별%LOC 미체결"""
        records = self.strategy.execute_daily_buy(
            date="2024-01-01",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=90.0,  # 별%LOC=85 보다 높음 → 미체결
            close=100.0,
        )
        # 0%LOC만 체결
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].action, "buy_zero")

    def test_second_half_buy(self):
        """후반전: 전액 |별%|LOC 1건"""
        # T=10 이상으로 후반전 진입
        self.strategy.position.cumulative_buy_amount = 250000.0  # T=10
        self.strategy.position.round_num = 10
        self.strategy.position.total_shares = 100.0
        self.strategy.position.total_cost = 250000.0
        self.strategy.position.remaining_budget = 750000.0

        records = self.strategy.execute_daily_buy(
            date="2024-01-15",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=95.0,  # |별%|=0 → LOC=100, 저가 95<=100 체결
            close=100.0,
        )
        # 후반전: 전액 1건
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].action, "buy_star")
        self.assertAlmostEqual(records[0].amount, 25000.0)

    def test_no_buy_when_budget_zero(self):
        """예산 소진 시 매수 없음"""
        self.strategy.position.remaining_budget = 0.0
        records = self.strategy.execute_daily_buy(
            date="2024-01-01",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=80.0,
            close=100.0,
        )
        self.assertEqual(len(records), 0)

    def test_no_buy_when_max_divisions_reached(self):
        """최대 분할수 도달 시 매수 없음"""
        self.strategy.position.round_num = 40
        records = self.strategy.execute_daily_buy(
            date="2024-01-01",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=80.0,
            close=100.0,
        )
        self.assertEqual(len(records), 0)


class TestSell(unittest.TestCase):
    """매도 로직 테스트"""

    def setUp(self):
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

    def _buy_once(self):
        """테스트용 1회 매수"""
        return self.strategy.execute_daily_buy(
            date="2024-01-01",
            prev_close=100.0,
            open_price=100.0,
            high=105.0,
            low=80.0,
            close=100.0,
        )

    def test_should_sell_no_position(self):
        """보유 없으면 매도 불가"""
        self.assertFalse(self.strategy.should_sell(200.0))

    def test_should_sell_below_target(self):
        """목표가 미달 → 매도 안 함"""
        self._buy_once()
        avg = self.strategy.position.avg_price
        target = avg * 1.05
        self.assertFalse(self.strategy.should_sell(target - 0.01))

    def test_should_sell_at_target(self):
        """목표가 도달 → 매도"""
        self._buy_once()
        avg = self.strategy.position.avg_price
        target = avg * 1.05
        self.assertTrue(self.strategy.should_sell(target))

    def test_should_sell_above_target(self):
        """목표가 초과 → 매도"""
        self._buy_once()
        avg = self.strategy.position.avg_price
        self.assertTrue(self.strategy.should_sell(avg * 1.10))

    def test_sell_resets_cycle(self):
        """매도 후 새 사이클 시작"""
        self._buy_once()
        rec = self.strategy.execute_sell("2024-01-05")
        self.assertEqual(rec.cycle, 1)
        self.assertEqual(rec.action, "sell")
        # 새 사이클
        self.assertEqual(self.strategy.cycle, 2)
        self.assertEqual(self.strategy.position.round_num, 0)
        self.assertEqual(self.strategy.position.total_shares, 0.0)

    def test_sell_profit_reinvestment(self):
        """매도 수익 반복리: 수익의 절반 / 40 → 1회매수금 증가"""
        self._buy_once()
        old_unit = self.strategy.unit_amount
        rec = self.strategy.execute_sell("2024-01-05")
        # 수익이 있으면 unit_amount가 증가해야 함
        if rec.amount > self.strategy.position.total_cost:
            self.assertGreater(self.strategy.unit_amount, old_unit)


class TestProcessDay(unittest.TestCase):
    """하루 전체 처리 테스트"""

    def setUp(self):
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

    def test_buy_day(self):
        """일반 매수일"""
        records = self.strategy.process_day(
            date="2024-01-01",
            open_price=100.0,
            high=105.0,
            low=80.0,
            close=100.0,
            prev_close=100.0,
        )
        self.assertTrue(len(records) > 0)
        self.assertTrue(all("buy" in r.action for r in records))

    def test_sell_day_no_buy(self):
        """매도일에는 매수 안 함"""
        # 먼저 매수
        self.strategy.process_day(
            date="2024-01-01",
            open_price=100.0,
            high=105.0,
            low=80.0,
            close=100.0,
            prev_close=100.0,
        )

        # 목표가 이상으로 매도 트리거
        avg = self.strategy.position.avg_price
        target = avg * 1.05

        records = self.strategy.process_day(
            date="2024-01-02",
            open_price=target + 5,
            high=target + 10,
            low=target - 1,
            close=target + 5,
            prev_close=100.0,
        )
        # 매도만 발생
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].action, "sell")


class TestMultipleCycles(unittest.TestCase):
    """여러 사이클 테스트"""

    def test_two_cycles(self):
        """2사이클 완전 순환"""
        strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )

        # 사이클 1: 매수
        strategy.process_day("2024-01-01", 100.0, 105.0, 80.0, 100.0, 100.0)
        self.assertEqual(strategy.cycle, 1)

        # 사이클 1: 매도
        avg = strategy.position.avg_price
        target = avg * 1.05
        strategy.process_day("2024-01-02", target+5, target+10, target-1, target+5, 100.0)
        self.assertEqual(strategy.cycle, 2)

        # 사이클 2: 매수
        strategy.process_day("2024-01-03", 100.0, 105.0, 80.0, 100.0, 100.0)
        self.assertEqual(strategy.cycle, 2)
        self.assertTrue(strategy.position.total_shares > 0)


class TestOrderTableGenerator(unittest.TestCase):
    """주문 표 생성기 테스트"""

    def test_generate_basic_table(self):
        """기본 주문 표 생성"""
        from src.order_table import OrderTableGenerator
        strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )
        gen = OrderTableGenerator(strategy)
        df = gen.generate_table(start_price=100.0, price_step_pct=-1.0, steps=5)
        self.assertFalse(df.empty)
        self.assertIn('Step', df.columns)
        self.assertIn('Action', df.columns)
        self.assertIn('T', df.columns)
        self.assertIn('Star %', df.columns)

    def test_table_has_correct_steps(self):
        """지정 step 수만큼 생성"""
        from src.order_table import OrderTableGenerator
        strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )
        gen = OrderTableGenerator(strategy)
        df = gen.generate_table(start_price=100.0, price_step_pct=-1.0, steps=3)
        # 전반전이면 각 step에서 2건(별%LOC + 0%LOC)
        unique_steps = df['Step'].nunique()
        self.assertGreaterEqual(unique_steps, 1)
        self.assertLessEqual(unique_steps, 3)


class TestSummary(unittest.TestCase):
    """전략 요약 테스트"""

    def test_initial_summary(self):
        strategy = InfiniteBuyStrategyV3(
            total_investment=1000000, divisions=40, ticker="TQQQ"
        )
        s = strategy.summary()
        self.assertEqual(s['cycle'], 1)
        self.assertEqual(s['t_value'], 0.0)
        self.assertEqual(s['star_pct'], 15.0)
        self.assertEqual(s['half'], '전반전')
        self.assertEqual(s['unit_amount'], 25000.0)
        self.assertEqual(s['total_shares'], 0.0)
        self.assertEqual(s['remaining_budget'], 1000000.0)


if __name__ == '__main__':
    unittest.main()
