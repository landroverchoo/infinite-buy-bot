"""
주문 표 생성 (V3.0)
"""
import pandas as pd
from typing import Optional

from .strategy import InfiniteBuyStrategyV3, Position


class OrderTableGenerator:
    """무한매수법 V3.0 주문 표 생성기"""

    def __init__(self, strategy: InfiniteBuyStrategyV3):
        self.strategy = strategy

    def generate_table(
        self,
        start_price: float,
        price_step_pct: float = -1.0,  # 가격 하락률 %
        steps: Optional[int] = None,
    ) -> pd.DataFrame:
        """시뮬레이션 주문 표 생성 (V3.0 별%/T 기반)

        - start_price: 시작 가격
        - price_step_pct: 각 회차 가격 변화율 (음수 = 하락)
        - steps: 시뮬레이션 단계 수 (기본값 None = divisions까지)
        """
        if steps is None:
            steps = self.strategy.divisions

        rows = []
        prev_close = start_price

        for step in range(steps):
            if self.strategy.position.round_num >= self.strategy.divisions:
                break

            # 현재 가격 시뮬레이션 (전일 종가 기준 변화)
            if step == 0:
                current_price = start_price
            else:
                current_price = prev_close * (1 + price_step_pct / 100)

            # V3 별%/T 계산
            t_val = self.strategy.calc_t()
            star_pct = self.strategy.calc_star_pct()
            half_label = "전반전" if star_pct > 0 else "후반전"

            # 시뮬레이션용 OHLC: 저가를 충분히 낮게 설정하여 LOC 체결 보장
            sim_low = current_price * 0.8
            sim_high = current_price * 1.02

            # 매도 조건 먼저 체크
            if self.strategy.should_sell(sim_high):
                rec = self.strategy.execute_sell(f"step-{step+1}")
                if rec:
                    rows.append({
                        'Step': step + 1,
                        'Half': '매도',
                        'Action': 'sell',
                        'Prev Close': round(prev_close, 4),
                        'LOC Price': round(rec.price, 4),
                        'Shares': round(rec.shares, 6),
                        'Amount': round(rec.amount, 2),
                        'Total Shares': 0.0,
                        'Avg Price': 0.0,
                        'Target Sell': 0.0,
                        'T': round(rec.t_value, 2),
                        'Star %': round(rec.star_pct, 2),
                        'Unit Amount': round(rec.unit_amount, 2),
                        'Remaining Budget': round(rec.remaining_budget, 2),
                    })
                prev_close = current_price
                continue

            # 매수 실행
            buy_records = self.strategy.execute_daily_buy(
                date=f"step-{step+1}",
                prev_close=prev_close,
                open_price=current_price,
                high=sim_high,
                low=sim_low,
                close=current_price,
            )

            for rec in buy_records:
                rows.append({
                    'Step': step + 1,
                    'Half': rec.half,
                    'Action': rec.action,
                    'Prev Close': round(prev_close, 4),
                    'LOC Price': round(rec.price, 4),
                    'Shares': round(rec.shares, 6),
                    'Amount': round(rec.amount, 2),
                    'Total Shares': round(rec.total_shares, 6),
                    'Avg Price': round(rec.avg_price, 4),
                    'Target Sell': round(rec.target_sell_price, 4),
                    'T': round(rec.t_value, 2),
                    'Star %': round(rec.star_pct, 2),
                    'Unit Amount': round(rec.unit_amount, 2),
                    'Remaining Budget': round(rec.remaining_budget, 2),
                })

            if not buy_records and self.strategy.position.remaining_budget <= 0:
                break

            prev_close = current_price

        return pd.DataFrame(rows)


if __name__ == "__main__":
    strategy = InfiniteBuyStrategyV3(total_investment=10000000, divisions=40)
    gen = OrderTableGenerator(strategy)
    df = gen.generate_table(start_price=100.0, price_step_pct=-1.0)
    print(df.to_string())
