"""
라오어 무한매수법 V3.0 핵심 로직
"""
from dataclasses import dataclass, field
from typing import List, Optional
import math


@dataclass
class Position:
    """현재 포지션 상태"""
    round_num: int = 0          # 현재 회차 (0 = 미시작)
    total_shares: float = 0.0   # 총 보유 수량
    total_cost: float = 0.0     # 총 매수 금액
    remaining_budget: float = 0.0  # 잔여 투자금
    cumulative_buy_amount: float = 0.0  # 매수 누적액 (T 계산용)

    @property
    def avg_price(self) -> float:
        """평단가"""
        if self.total_shares == 0:
            return 0.0
        return self.total_cost / self.total_shares

    @property
    def target_sell_price(self) -> float:
        """목표 매도가 (평단가 + target_profit_pct%)"""
        return 0.0  # strategy에서 계산

    def reset(self, total_investment: float):
        """새 사이클 시작"""
        self.round_num = 0
        self.total_shares = 0.0
        self.total_cost = 0.0
        self.remaining_budget = total_investment
        self.cumulative_buy_amount = 0.0


@dataclass
class TradeRecord:
    """매매 기록"""
    date: str
    round_num: int
    action: str              # "buy" or "sell" or "quarter_sell"
    price: float             # 체결가
    shares: float            # 수량
    amount: float            # 금액
    total_shares: float      # 매매 후 총 보유수량
    avg_price: float         # 매매 후 평단가
    target_sell_price: float # 목표 매도가
    remaining_budget: float  # 잔여 투자금
    cycle: int = 1           # 사이클 번호
    t_value: float = 0.0     # T 값
    star_pct: float = 0.0    # 별% 값


class InfiniteBuyStrategy:
    """라오어 무한매수법 V3.0"""

    def __init__(
        self,
        total_investment: float,
        divisions: int = 40,
        target_profit_pct: float = 5.0,
        use_loc: bool = True,
        loc_discount_pct: float = 1.0,
        ticker: str = "TQQQ"
    ):
        if divisions not in (20, 30, 40):
            raise ValueError("divisions must be 20, 30 or 40")

        self.total_investment = total_investment
        self.divisions = divisions
        self.target_profit_pct = target_profit_pct
        self.use_loc = use_loc
        self.loc_discount_pct = loc_discount_pct
        self.ticker = ticker.upper()
        self.unit_amount = total_investment / divisions  # 초기 1회 매수금액
        self.max_profit_pool = 0.0  # 수익 풀 (절반은 반복리, 절반은 손절 대비)

        self.position = Position()
        self.position.remaining_budget = total_investment
        self.cycle = 1
        self.trades: List[TradeRecord] = []

    def get_t_value(self) -> float:
        """T 값 계산: 매수누적액 / 1회매수액 (소수점 둘째 자리 올림)"""
        if self.unit_amount == 0:
            return 0.0
        return math.ceil(self.position.cumulative_buy_amount / self.unit_amount * 100) / 100

    def get_star_pct(self) -> float:
        """별% 계산: 종목별 공식"""
        t = self.get_t_value()
        if self.ticker == "TQQQ":
            return max(0, 15 - 1.5 * t)  # T=10에서 0%
        elif self.ticker == "SOXL":
            return max(0, 20 - 2.0 * t)  # T=10에서 0%
        else:
            return max(0, 15 - 1.5 * t)  # 기본은 TQQQ 기준

    def get_buy_price(self, current_price: float, prev_close: float) -> float:
        """매수 가격 결정 (LOC 또는 시장가)"""
        if self.use_loc:
            return prev_close * (1 - self.loc_discount_pct / 100)
        return current_price

    def get_buy_multiplier(self, current_price: float) -> int:
        """매수 배수 결정: 평단가 이하면 2배, 초과면 1배"""
        if self.position.round_num == 0:
            return 1  # 1회차는 무조건 1배
        if current_price <= self.position.avg_price:
            return 2
        return 1

    def should_sell(self, current_price: float) -> bool:
        """매도 조건 확인: 평단가 대비 target_profit_pct% 이상"""
        if self.position.total_shares == 0:
            return False
        target = self.position.avg_price * (1 + self.target_profit_pct / 100)
        return current_price >= target

    def get_target_sell_price(self) -> float:
        """목표 매도가"""
        if self.position.avg_price == 0:
            return 0.0
        return self.position.avg_price * (1 + self.target_profit_pct / 100)

    def get_buy_portions(self) -> tuple[float, float]:
        """전반전/후반전 매수 비율 결정: (별%LOC 비율, 0%LOC 비율)"""
        t = self.get_t_value()
        if t < 10:
            return (0.5, 0.5)  # 전반전: 절반씩
        else:
            return (1.0, 0.0)  # 후반전: 전부 별%LOC

    def execute_buy(self, date: str, price: float, prev_close: float) -> Optional[TradeRecord]:
        """매수 실행"""
        buy_price = self.get_buy_price(price, prev_close)
        multiplier = self.get_buy_multiplier(buy_price)
        buy_amount = self.unit_amount * multiplier

        # 잔여 투자금 확인
        if buy_amount > self.position.remaining_budget:
            buy_amount = self.position.remaining_budget
        if buy_amount <= 0:
            return None

        # 매수 수량 계산
        shares = buy_amount / buy_price

        # 포지션 업데이트
        self.position.round_num += 1
        self.position.total_shares += shares
        self.position.total_cost += buy_amount
        self.position.remaining_budget -= buy_amount
        self.position.cumulative_buy_amount += buy_amount

        # T와 별% 계산
        t_val = self.get_t_value()
        star_pct = self.get_star_pct()

        record = TradeRecord(
            date=date,
            round_num=self.position.round_num,
            action="buy",
            price=buy_price,
            shares=round(shares, 6),
            amount=round(buy_amount, 2),
            total_shares=round(self.position.total_shares, 6),
            avg_price=round(self.position.avg_price, 4),
            target_sell_price=round(self.get_target_sell_price(), 4),
            remaining_budget=round(self.position.remaining_budget, 2),
            cycle=self.cycle,
            t_value=round(t_val, 2),
            star_pct=round(star_pct, 2)
        )
        self.trades.append(record)
        return record

    def execute_sell(self, date: str, price: float) -> Optional[TradeRecord]:
        """전량 매도"""
        if self.position.total_shares == 0:
            return None

        sell_amount = self.position.total_shares * price
        shares_sold = self.position.total_shares
        # 새 투자금 = 매도 수익금 + 미사용 잔여 투자금
        new_investment = sell_amount + self.position.remaining_budget
        # 수익 계산 (매도금 - 총 매수비용)
        profit = sell_amount - self.position.total_cost
        if profit > 0:
            # 수익의 절반은 반복리, 절반은 풀에
            half_profit = profit / 2
            self.max_profit_pool += half_profit
            # 반복리: 40분할로 1회매수금 증가
            unit_increase = half_profit / 40
            self.unit_amount += unit_increase

        t_val = self.get_t_value()
        star_pct = self.get_star_pct()

        record = TradeRecord(
            date=date,
            round_num=self.position.round_num,
            action="sell",
            price=price,
            shares=round(shares_sold, 6),
            amount=round(sell_amount, 2),
            total_shares=0.0,
            avg_price=0.0,
            target_sell_price=0.0,
            remaining_budget=round(new_investment, 2),
            cycle=self.cycle,
            t_value=round(t_val, 2),
            star_pct=round(star_pct, 2)
        )
        self.trades.append(record)

        # 새 사이클 시작
        self.cycle += 1
        self.total_investment = new_investment
        self.position.reset(new_investment)

        return record

    def process_day(self, date: str, open_price: float, high: float,
                    low: float, close: float, prev_close: float) -> List[TradeRecord]:
        """하루 처리: 매도 체크 → 매수"""
        records = []

        # 1) 매도 조건 체크 (고가 기준)
        if self.should_sell(high):
            sell_price = self.get_target_sell_price()
            # 실제 고가가 목표가 이상이면 목표가에 매도
            if high >= sell_price:
                rec = self.execute_sell(date, sell_price)
                if rec:
                    records.append(rec)
                return records  # 매도 후 그날은 매수 안 함

        # 2) 매수 (분할 횟수 초과 체크)
        if self.position.round_num < self.divisions:
            rec = self.execute_buy(date, close, prev_close)
            if rec:
                records.append(rec)

        return records
