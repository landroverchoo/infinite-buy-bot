"""
백테스트 및 시뮬레이션 (V3.0)
"""
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Tuple
import yaml

from .strategy import InfiniteBuyStrategyV3, TradeRecord


class InfiniteBuySimulator:
    """무한매수법 V3.0 시뮬레이터 & 백테스트"""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.strategy = InfiniteBuyStrategyV3(
            total_investment=self.config['strategy']['total_investment'],
            divisions=self.config['strategy']['divisions'],
            target_profit_pct=self.config['strategy']['target_profit_pct'],
            ticker=self.config['ticker'],
        )
        self.ticker = self.config['ticker']
        self.backtest_start = self.config['backtest']['start_date']
        self.backtest_end = self.config['backtest']['end_date']
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """yfinance로 데이터 가져오기"""
        ticker = yf.Ticker(self.ticker)
        df = ticker.history(start=self.backtest_start, end=self.backtest_end)
        if df.empty:
            raise ValueError(f"No data for {self.ticker}")
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df['Prev_Close'] = df['Close'].shift(1)
        df.dropna(subset=['Prev_Close'], inplace=True)
        self.data = df
        return df

    def run_backtest(self) -> List[TradeRecord]:
        """백테스트 실행"""
        if self.data is None:
            self.fetch_data()

        trades = []
        for _, row in self.data.iterrows():
            day_trades = self.strategy.process_day(
                date=row['Date'],
                open_price=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                prev_close=row['Prev_Close'],
            )
            trades.extend(day_trades)

        return trades

    def get_trade_df(self) -> pd.DataFrame:
        """매매 기록을 DataFrame으로"""
        records = []
        for t in self.strategy.trades:
            records.append({
                'Date': t.date,
                'Cycle': t.cycle,
                'Round': t.round_num,
                'Action': t.action,
                'Half': t.half,
                'Price': t.price,
                'Shares': t.shares,
                'Amount': t.amount,
                'Total Shares': t.total_shares,
                'Avg Price': t.avg_price,
                'Target Sell Price': t.target_sell_price,
                'Remaining Budget': t.remaining_budget,
                'T': t.t_value,
                'Star %': t.star_pct,
                'Unit Amount': t.unit_amount,
            })
        return pd.DataFrame(records)

    def calculate_performance(self) -> Dict:
        """성과 계산"""
        trades = self.strategy.trades
        if not trades:
            return {'total_return': 0.0, 'cycles_completed': 0, 'max_drawdown': 0.0}

        cycles = max(t.cycle for t in trades)
        completed_cycles = sum(1 for t in trades if t.action == 'sell')
        total_return = 0.0
        initial_investment = self.strategy.initial_investment
        last_trade = trades[-1]
        last_close = self.data['Close'].iloc[-1] if not self.data.empty else 0.0
        if last_trade.action == 'sell':
            current_value = last_trade.remaining_budget
        else:
            current_value = last_trade.remaining_budget + last_trade.total_shares * last_close
        total_return = (current_value / initial_investment - 1) * 100

        # 최대 낙폭 (MDD)
        max_drawdown = 0.0
        df = self.get_trade_df()
        if not df.empty and 'Total Shares' in df.columns and not df[df['Total Shares'] > 0].empty and not self.data.empty:
            merged = self.data[['Date', 'Close']].merge(df, on='Date', how='left')
            merged['Total Shares'] = merged['Total Shares'].ffill().fillna(0)
            merged['Portfolio Value'] = merged['Total Shares'] * merged['Close']
            merged['Peak'] = merged['Portfolio Value'].cummax()
            merged['Drawdown'] = (merged['Portfolio Value'] - merged['Peak']) / merged['Peak'] * 100
            max_drawdown = merged['Drawdown'].min() if not merged['Drawdown'].isna().all() else 0.0

        return {
            'total_return_pct': round(total_return, 2),
            'cycles_completed': completed_cycles,
            'total_cycles': cycles,
            'max_drawdown_pct': round(max_drawdown, 2) if max_drawdown != float('nan') else 0.0,
        }

    def plot_performance(self, save_path: str = None):
        """성과 시각화"""
        if self.data is None or not self.strategy.trades:
            print("No data to plot")
            return

        df = self.get_trade_df()
        if df.empty:
            print("No trades to plot")
            return

        # 가격 데이터와 매매 기록 병합
        price_df = self.data[['Date', 'Close']].copy()
        price_df['Date'] = price_df['Date'].astype(str)
        df['Date'] = df['Date'].astype(str)
        merged = price_df.merge(df, on='Date', how='left')

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

        # 1) 가격 차트 + 매수/매도 포인트
        ax1.plot(merged['Date'], merged['Close'], label=f"{self.ticker} Close", alpha=0.5)
        buy_points = merged[merged['Action'].str.contains('buy')]
        sell_points = merged[merged['Action'] == 'sell']
        ax1.scatter(buy_points['Date'], buy_points['Price'], color='green', marker='^', s=100, label='Buy')
        ax1.scatter(sell_points['Date'], sell_points['Price'], color='red', marker='v', s=100, label='Sell')
        ax1.set_title(f"Infinite Buy Strategy V3.0 - {self.ticker}")
        ax1.set_ylabel("Price")
        ax1.legend()
        ax1.grid(True)
        plt.setp(ax1.get_xticklabels(), rotation=45)

        # 2) 포지션 수량
        merged['Total Shares'] = merged['Total Shares'].ffill().fillna(0)
        ax2.bar(merged['Date'], merged['Total Shares'], color='purple', alpha=0.3, label='Position')
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Shares")
        ax2.legend()
        ax2.grid(True)
        plt.setp(ax2.get_xticklabels(), rotation=45)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
        plt.close()

if __name__ == "__main__":
    sim = InfiniteBuySimulator("config.yaml")
    sim.run_backtest()
    df = sim.get_trade_df()
    print(df.tail(10))
    perf = sim.calculate_performance()
    print("\nPerformance Summary:")
    for k, v in perf.items():
        print(f"  {k}: {v}")
    sim.plot_performance()
