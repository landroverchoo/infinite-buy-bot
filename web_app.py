"""
무한매수법 V3.0 웹 UI (Flask)
"""
from flask import Flask, render_template, request, jsonify, send_file
import yaml
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.strategy import InfiniteBuyStrategyV3
from src.simulator import InfiniteBuySimulator

from src.order_table import OrderTableGenerator

app = Flask(__name__)

DEFAULT_CONFIG = {
    'strategy': {
        'divisions': 40,
        'total_investment': 10000000,
        'target_profit_pct': 5.0,
        'use_loc': True,
        'loc_discount_pct': 1.0,
    },
    'ticker': 'TQQQ',
    'broker': 'kis',
    'backtest': {
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
    }
}


@app.route('/')
def index():
    return render_template('index.html', config=DEFAULT_CONFIG)


@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """백테스트 API"""
    data = request.json
    
    # 임시 config 파일 생성
    config = {
        'strategy': {
            'divisions': int(data.get('divisions', 40)),
            'total_investment': float(data.get('total_investment', 10000000)),
            'target_profit_pct': float(data.get('target_profit_pct', 5.0)),
            'use_loc': data.get('use_loc', True),
            'loc_discount_pct': float(data.get('loc_discount_pct', 1.0)),
        },
        'ticker': data.get('ticker', 'TQQQ'),
        'broker': 'kis',
        'backtest': {
            'start_date': data.get('start_date', '2024-01-01'),
            'end_date': data.get('end_date', '2024-12-31'),
        }
    }
    
    tmp_config = '/tmp/infinite_buy_config.yaml'
    with open(tmp_config, 'w') as f:
        yaml.dump(config, f)
    
    try:
        sim = InfiniteBuySimulator(tmp_config)
        sim.fetch_data()
        sim.run_backtest()
        
        # 매매 기록
        df = sim.get_trade_df()
        trades_html = df.to_html(classes='table table-striped table-sm', index=False)
        
        # 성과
        perf = sim.calculate_performance()
        
        # 차트 생성 (base64)
        chart_b64 = generate_chart_b64(sim)
        
        return jsonify({
            'success': True,
            'trades_html': trades_html,
            'performance': perf,
            'chart': chart_b64,
            'total_trades': len(df),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/order_table', methods=['POST'])
def generate_order_table():
    """주문 표 API"""
    data = request.json
    
    strategy = InfiniteBuyStrategyV3(
        total_investment=float(data.get('total_investment', 10000000)),
        divisions=int(data.get('divisions', 40)),
        target_profit_pct=float(data.get('target_profit_pct', 5.0)),
        ticker=data.get('ticker', 'TQQQ'),
    )
    gen = OrderTableGenerator(strategy)
    df = gen.generate_table(
        start_price=float(data.get('start_price', 100.0)),
        price_step_pct=float(data.get('price_step', -1.0)),
    )
    
    table_html = df.to_html(classes='table table-striped table-sm', index=False)
    return jsonify({'success': True, 'table_html': table_html})


def generate_chart_b64(sim):
    """차트를 base64 문자열로"""
    df = sim.get_trade_df()
    if df.empty:
        return None
    
    price_df = sim.data[['Date', 'Close']].copy()
    price_df['Date'] = price_df['Date'].astype(str)
    df['Date'] = df['Date'].astype(str)
    merged = price_df.merge(df, on='Date', how='left')
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    ax1.plot(range(len(merged)), merged['Close'], label=f"{sim.ticker} Close", alpha=0.6, color='#2196F3')
    buy_idx = merged[merged['Action'].str.contains('buy')].index
    sell_idx = merged[merged['Action'] == 'sell'].index
    ax1.scatter(buy_idx, merged.loc[buy_idx, 'Price'], color='#4CAF50', marker='^', s=60, label='Buy', zorder=5)
    ax1.scatter(sell_idx, merged.loc[sell_idx, 'Price'], color='#F44336', marker='v', s=60, label='Sell', zorder=5)
    ax1.set_title(f"Infinite Buy Strategy V3.0 - {sim.ticker}", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Price ($)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    merged['Total Shares'] = merged['Total Shares'].ffill().fillna(0)
    ax2.fill_between(range(len(merged)), merged['Total Shares'], color='#9C27B0', alpha=0.3)
    ax2.plot(range(len(merged)), merged['Total Shares'], color='#9C27B0', alpha=0.6)
    ax2.set_xlabel("Trading Days")
    ax2.set_ylabel("Shares")
    ax2.set_title("Position Size", fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
