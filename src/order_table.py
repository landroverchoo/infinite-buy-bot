"""
주문 표 생성
"""
import pandas as pd
from typing import List, Optional

from .strategy import InfiniteBuyStrategy, Position


class OrderTableGenerator:
    """무한매수법 주문 표 생성기"""

    def __init__(self, strategy: InfiniteBuyStrategy):
        self.strategy = strategy

    def generate_table(
        self,
        start_price: float,
        price_step_pct: float = -1.0,  # 가격 하락률 %
        steps: Optional[int] = None,
        max_rounds: Optional[int] = None
    ) -> pd.DataFrame:
        """시뮬레이션 주문 표 생성
        - start_price: 시작 가격
        - price_step_pct: 각 회차 가격 변화율 (음수 = 하락)
        - steps: 시뮬레이션 단계 수 (기본값 None = divisions까지)
        - max_rounds: 최대 회차 제한 (기본값 None = divisions)
        """
        if steps is None:
            steps = self.strategy.divisions
        if max_rounds is None:
            max_rounds = self.strategy.divisions

        # 초기화
        pos = Position()
        pos.remaining_budget = self.strategy.total_investment
        rows = []
        prev_close = start_price

        for step in range(steps):
            round_num = pos.round_num + 1
            if round_num > max_rounds:
                break

            # 현재 가격 = 전일 종가 * (1 + 변화율)
            current_price = prev_close * (1 + price_step_pct / 100)
            buy_price = self.strategy.get_buy_price(current_price, prev_close)
            multiplier = self.strategy.get_buy_multiplier(buy_price)
            buy_amount = self.strategy.unit_amount * multiplier

            if buy_amount > pos.remaining_budget:
                buy_amount = pos.remaining_budget
            if buy_amount <= 0:
                break

            shares = buy_amount / buy_price
            pos.round_num = round_num
            pos.total_shares += shares
            pos.total_cost += buy_amount
            pos.remaining_budget -= buy_amount

            target_sell = pos.avg_price * (1 + self.strategy.target_profit_pct / 100) if pos.avg_price > 0 else 0.0

            rows.append({
                'Round': round_num,
                'Buy Price': round(buy_price, 2),
                'Multiplier': multiplier,
                'Shares': round(shares, 6),
                'Amount': round(buy_amount, 2),
                'Total Shares': round(pos.total_shares, 6),
                'Avg Price': round(pos.avg_price, 2),
                'Target Sell Price': round(target_sell, 2),
                'Remaining Budget': round(pos.remaining_budget, 2),
            })

            # 다음 루프를 위해
            prev_close = current_price

            # 매도 조건 체크
            if current_price >= target_sell and pos.total_shares > 0:
                sell_amount = pos.total_shares * target_sell
                rows.append({
                    'Round': round_num,
                    'Buy Price': round(target_sell, 2),
                    'Multiplier': 0,
                    'Shares': -pos.total_shares,
                    'Amount': round(sell_amount, 2),
                    'Total Shares': 0.0,
                    'Avg Price': 0.0,
                    'Target Sell Price': 0.0,
                    'Remaining Budget': round(pos.remaining_budget + sell_amount, 2),
                })
                pos.reset(pos.remaining_budget + sell_amount)
                self.strategy.unit_amount = pos.remaining_budget / self.strategy.divisions

        return pd.DataFrame(rows)


if __name__ == "__main__":
    strategy = InfiniteBuyStrategy(total_investment=10000000, divisions=40)
    gen = OrderTableGenerator(strategy)
    df = gen.generate_table(start_price=100.0, price_step_pct=-1.0)
    print(df)
