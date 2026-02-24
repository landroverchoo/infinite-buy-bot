"""
무한매수법 CLI
"""
import argparse
import os
import sys
from src.simulator import InfiniteBuySimulator
from src.order_table import OrderTableGenerator
from src.strategy import InfiniteBuyStrategy


def parse_args():
    parser = argparse.ArgumentParser(description="라오어 무한매수법 자동매매")
    subparsers = parser.add_subparsers(dest="command")

    # 백테스트
    backtest_parser = subparsers.add_parser("backtest", help="백테스트 실행")
    backtest_parser.add_argument("--config", default="config.yaml", help="설정 파일")
    backtest_parser.add_argument("--plot", action="store_true", help="차트 표시")
    backtest_parser.add_argument("--save-plot", help="차트 저장 경로")

    # 시뮬레이션 표
    table_parser = subparsers.add_parser("table", help="주문 표 생성")
    table_parser.add_argument("--start-price", type=float, default=100.0, help="시작 가격")
    table_parser.add_argument("--price-step", type=float, default=-1.0, help="가격 변화율 (퍼센트)")
    table_parser.add_argument("--steps", type=int, help="시뮬레이션 단계 수")
    table_parser.add_argument("--config", default="config.yaml", help="설정 파일")

    # 실시간 매매 (TODO)
    run_parser = subparsers.add_parser("run", help="실시간 자동매매")
    run_parser.add_argument("--config", default="config.yaml", help="설정 파일")
    run_parser.add_argument("--dry-run", action="store_true", help="모의 주문")

    return parser.parse_args()


def run_backtest(args):
    sim = InfiniteBuySimulator(args.config)
    print("Fetching data...")
    sim.fetch_data()
    print("Running backtest...")
    sim.run_backtest()
    df = sim.get_trade_df()
    print("\nLast 10 trades:")
    print(df.tail(10))
    perf = sim.calculate_performance()
    print("\nPerformance Summary:")
    for k, v in perf.items():
        print(f"  {k.replace('_', ' ').title()}: {v}")
    if args.plot or args.save_plot:
        print("Generating plot...")
        sim.plot_performance(save_path=args.save_plot)


def generate_order_table(args):
    # config에서 strategy 설정 읽기
    import yaml
    with open(args.config, 'r') as f:
        cfg = yaml.safe_load(f)
    strategy = InfiniteBuyStrategy(
        total_investment=cfg['strategy']['total_investment'],
        divisions=cfg['strategy']['divisions'],
        target_profit_pct=cfg['strategy']['target_profit_pct'],
        use_loc=cfg['strategy']['use_loc'],
        loc_discount_pct=cfg['strategy']['loc_discount_pct'],
    )
    gen = OrderTableGenerator(strategy)
    df = gen.generate_table(
        start_price=args.start_price,
        price_step_pct=args.price_step,
        steps=args.steps
    )
    print(df)


def run_trading(args):
    print("실시간 자동매매는 아직 구현되지 않았습니다. 한투/키움 API 연동 필요.")
    sys.exit(1)


def main():
    args = parse_args()
    if args.command == "backtest":
        run_backtest(args)
    elif args.command == "table":
        generate_order_table(args)
    elif args.command == "run":
        run_trading(args)
    else:
        print("사용법: python main.py [backtest|table|run]")
        sys.exit(1)


if __name__ == "__main__":
    main()
