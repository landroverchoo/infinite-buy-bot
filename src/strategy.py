"""
라오어 무한매수법 V3.0 핵심 로직

핵심 개념:
- T = 매수누적액 / 1회매수액 (소수점 둘째자리 올림)
- 별% (Star%):
    TQQQ: 15 - 1.5*T
    SOXL: 20 - 2*T
    T=10에서 별%=0 → 전후반전 기준
- 전반전(별%>0): 1회매수액 절반 별%LOC + 절반 0%LOC
- 후반전(별%≤0): 1회매수액 전부 별%LOC (절대값)
- 수익 시: 수익금 40분할 → 1회매수금에 반복리 반영
- 손실 시: 1회매수금 불변 (과거 수익Max 기준)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math


# 종목별 별% 설정
STAR_CONFIG = {
    "TQQQ": {"base": 15, "coeff": 1.5},   # 별% = 15 - 1.5*T
    "SOXL": {"base": 20, "coeff": 2.0},   # 별% = 20 - 2*T
}


@dataclass
class Position:
    """현재 포지션"""
    round_num: int = 0
    total_shares: float = 0.0
    total_cost: float = 0.0           # 총 매수금액
    remaining_budget: float = 0.0
    cumulative_buy_amount: float = 0.0  # 매수 누적액 (T 계산용)

    @property
    def avg_price(self) -> float:
        if self.total_shares == 0:
            return 0.0
        return self.total_cost / self.total_shares

    def reset(self, budget: float):
        self.round_num = 0
        self.total_shares = 0.0
        self.total_cost = 0.0
        self.remaining_budget = budget
        self.cumulative_buy_amount = 0.0


@dataclass
class TradeRecord:
    """매매 기록"""
    date: str
    cycle: int
    round_num: int
    action: str             # "buy_star", "buy_zero", "sell", "quarter_sell"
    price: float
    shares: float
    amount: float
    total_shares: float
    avg_price: float
    target_sell_price: float
    remaining_budget: float
    t_value: float = 0.0
    star_pct: float = 0.0
    half: str = ""          # "전반전" or "후반전"
    unit_amount: float = 0.0  # 당시 1회매수금


class InfiniteBuyStrategyV3:
    """라오어 무한매수법 V3.0"""

    def __init__(
        self,
        total_investment: float,
        divisions: int = 40,
        target_profit_pct: float = 5.0,
        ticker: str = "TQQQ",
    ):
        if divisions not in (20, 30, 40):
            raise ValueError("divisions는 20, 30, 40 중 선택")

        self.initial_investment = total_investment
        self.total_investment = total_investment
        self.divisions = divisions
        self.target_profit_pct = target_profit_pct
        self.ticker = ticker.upper()

        # 1회 매수금 = 원금 / 분할수
        self.base_unit_amount = total_investment / divisions
        self.unit_amount = self.base_unit_amount

        # 수익 추적 (반복리)
        self.cumulative_profit = 0.0       # 누적 수익 (반복리 적용분)
        self.max_cumulative_profit = 0.0   # 과거 최대 수익 (손실 시 매수금 유지용)
        self.reserve_pool = 0.0            # 나머지 절반 수익 (손절 대비)

        # 별% 설정
        star_cfg = STAR_CONFIG.get(self.ticker, STAR_CONFIG["TQQQ"])
        self.star_base = star_cfg["base"]
        self.star_coeff = star_cfg["coeff"]

        self.position = Position()
        self.position.remaining_budget = total_investment
        self.cycle = 1
        self.trades: List[TradeRecord] = []

    # ─── T 값 / 별% ───────────────────────────────────

    def calc_t(self) -> float:
        """T = 매수누적액 / 1회매수액 (소수점 둘째자리 올림)"""
        if self.unit_amount <= 0:
            return 0.0
        raw = self.position.cumulative_buy_amount / self.unit_amount
        return math.ceil(raw * 100) / 100

    def calc_star_pct(self) -> float:
        """별% = base - coeff * T"""
        t = self.calc_t()
        return self.star_base - self.star_coeff * t

    def is_first_half(self) -> bool:
        """전반전: 별% > 0 (T < 10)"""
        return self.calc_star_pct() > 0

    # ─── LOC 가격 계산 ─────────────────────────────────

    def loc_price(self, prev_close: float, pct: float) -> float:
        """LOC 가격 = 전일종가 * (1 - pct/100)
        pct=0 이면 0%LOC (전일 종가 그대로)
        pct=5 이면 5%LOC (전일 종가 -5%)
        """
        return prev_close * (1 - pct / 100)

    # ─── 매수 실행 ─────────────────────────────────────

    def execute_daily_buy(self, date: str, prev_close: float, open_price: float,
                          high: float, low: float, close: float) -> List[TradeRecord]:
        """하루 매수 로직 (V3.0)"""
        records = []
        if self.position.round_num >= self.divisions:
            return records

        star_pct = self.calc_star_pct()
        t_val = self.calc_t()
        half_label = "전반전" if star_pct > 0 else "후반전"

        if star_pct > 0:
            # ── 전반전: 절반 별%LOC + 절반 0%LOC ──
            half_amount = self.unit_amount / 2

            # 1) 별%LOC 매수 시도
            star_loc = self.loc_price(prev_close, star_pct)
            if low <= star_loc:  # 장중 저가가 LOC 가격 이하면 체결
                buy_price = star_loc
                actual_amount = min(half_amount, self.position.remaining_budget)
                if actual_amount > 0:
                    rec = self._do_buy(date, buy_price, actual_amount, "buy_star", t_val, star_pct, half_label)
                    records.append(rec)

            # 2) 0%LOC 매수 시도 (전일 종가)
            zero_loc = self.loc_price(prev_close, 0)
            if low <= zero_loc:  # 거의 항상 체결
                buy_price = zero_loc
                actual_amount = min(half_amount, self.position.remaining_budget)
                if actual_amount > 0:
                    rec = self._do_buy(date, buy_price, actual_amount, "buy_zero", t_val, star_pct, half_label)
                    records.append(rec)

        else:
            # ── 후반전: 전액 |별%|LOC ──
            abs_star = abs(star_pct)
            star_loc = self.loc_price(prev_close, abs_star)
            if low <= star_loc:
                buy_price = star_loc
                actual_amount = min(self.unit_amount, self.position.remaining_budget)
                if actual_amount > 0:
                    rec = self._do_buy(date, buy_price, actual_amount, "buy_star", t_val, star_pct, half_label)
                    records.append(rec)

        return records

    def _do_buy(self, date: str, price: float, amount: float,
                action: str, t_val: float, star_pct: float, half: str) -> TradeRecord:
        """실제 매수 처리"""
        shares = amount / price

        self.position.round_num += 1
        self.position.total_shares += shares
        self.position.total_cost += amount
        self.position.remaining_budget -= amount
        self.position.cumulative_buy_amount += amount

        # 매수 후 T/별% 재계산
        new_t = self.calc_t()
        new_star = self.calc_star_pct()

        record = TradeRecord(
            date=date,
            cycle=self.cycle,
            round_num=self.position.round_num,
            action=action,
            price=round(price, 4),
            shares=round(shares, 6),
            amount=round(amount, 2),
            total_shares=round(self.position.total_shares, 6),
            avg_price=round(self.position.avg_price, 4),
            target_sell_price=round(self._target_sell_price(), 4),
            remaining_budget=round(self.position.remaining_budget, 2),
            t_value=round(new_t, 2),
            star_pct=round(new_star, 2),
            half=half,
            unit_amount=round(self.unit_amount, 2),
        )
        self.trades.append(record)
        return record

    # ─── 매도 실행 ─────────────────────────────────────

    def _target_sell_price(self) -> float:
        if self.position.avg_price == 0:
            return 0.0
        return self.position.avg_price * (1 + self.target_profit_pct / 100)

    def should_sell(self, high: float) -> bool:
        """매도 조건: 고가가 목표매도가 이상"""
        if self.position.total_shares == 0:
            return False
        return high >= self._target_sell_price()

    def execute_sell(self, date: str) -> Optional[TradeRecord]:
        """전량 매도 (목표가에 체결)"""
        if self.position.total_shares == 0:
            return None

        sell_price = self._target_sell_price()
        sell_amount = self.position.total_shares * sell_price
        shares_sold = self.position.total_shares
        profit = sell_amount - self.position.total_cost

        t_val = self.calc_t()
        star_pct = self.calc_star_pct()

        # 잔여 투자금 + 매도금 = 새 사이클 투자금
        new_budget = sell_amount + self.position.remaining_budget

        record = TradeRecord(
            date=date,
            cycle=self.cycle,
            round_num=self.position.round_num,
            action="sell",
            price=round(sell_price, 4),
            shares=round(shares_sold, 6),
            amount=round(sell_amount, 2),
            total_shares=0.0,
            avg_price=0.0,
            target_sell_price=0.0,
            remaining_budget=round(new_budget, 2),
            t_value=round(t_val, 2),
            star_pct=round(star_pct, 2),
            half="매도",
            unit_amount=round(self.unit_amount, 2),
        )
        self.trades.append(record)

        # ── V3.0 수익 반복리 처리 ──
        if profit > 0:
            half_profit = profit / 2
            self.cumulative_profit += half_profit
            self.reserve_pool += half_profit
            # 과거 최대 수익 갱신
            if self.cumulative_profit > self.max_cumulative_profit:
                self.max_cumulative_profit = self.cumulative_profit
            # 1회매수금 = 기본 + 누적수익/40
            self.unit_amount = self.base_unit_amount + self.cumulative_profit / 40
        else:
            # 손실 시 1회매수금 불변 (과거 Max 기준)
            self.unit_amount = self.base_unit_amount + self.max_cumulative_profit / 40

        # 새 사이클
        self.cycle += 1
        self.total_investment = new_budget
        self.position.reset(new_budget)

        return record

    # ─── 하루 전체 처리 ────────────────────────────────

    def process_day(self, date: str, open_price: float, high: float,
                    low: float, close: float, prev_close: float) -> List[TradeRecord]:
        """하루 처리: 매도 체크 → 매수"""
        records = []

        # 1) 매도 조건 체크
        if self.should_sell(high):
            rec = self.execute_sell(date)
            if rec:
                records.append(rec)
            return records  # 매도일은 매수 안 함

        # 2) 매수
        buy_records = self.execute_daily_buy(date, prev_close, open_price, high, low, close)
        records.extend(buy_records)

        return records

    # ─── 상태 요약 ─────────────────────────────────────

    def summary(self) -> dict:
        return {
            "cycle": self.cycle,
            "t_value": self.calc_t(),
            "star_pct": self.calc_star_pct(),
            "half": "전반전" if self.is_first_half() else "후반전",
            "unit_amount": round(self.unit_amount, 2),
            "avg_price": round(self.position.avg_price, 4),
            "total_shares": round(self.position.total_shares, 6),
            "remaining_budget": round(self.position.remaining_budget, 2),
            "cumulative_profit": round(self.cumulative_profit, 2),
            "reserve_pool": round(self.reserve_pool, 2),
        }
