# -*- coding: utf-8 -*-
"""
股票分析系统 - 命令行入口
"""

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.engine import analysis_engine
from src.visualization.reports import report_generator
from src.utils.logger import get_logger
from src.utils.helpers import format_number

logger = get_logger(__name__)


def cmd_fetch(args):
    """获取数据命令"""
    stock_code = args.stock
    days = args.days
    save = args.save
    
    print(f"获取数据: {stock_code}, {days}天")
    
    df = analysis_engine.fetch_data(stock_code, days, save_to_db=save)
    
    if df.empty:
        print("获取数据失败")
        return
    
    print(f"成功获取 {len(df)} 条数据")
    print(df.tail(10))


def cmd_analyze(args):
    """分析命令"""
    stock_code = args.stock
    days = args.days
    
    print(f"分析: {stock_code}")
    
    result = analysis_engine.full_analysis(stock_code, days)
    
    if 'error' in result:
        print(f"分析失败: {result['error']}")
        return
    
    summary = result['summary']
    
    print("\n=== 技术分析结果 ===")
    print(f"最新价格: {format_number(summary.get('latest_price', 0))}")
    print(f"趋势判断: {summary.get('trend', 'N/A')}")
    
    rsi = summary.get('rsi_status', {})
    print(f"RSI(14): {format_number(rsi.get('rsi_14', 0))} ({rsi.get('condition', 'N/A')})")
    
    signal = summary.get('latest_signal', {})
    print(f"信号: {signal.get('direction', 'hold')}, 强度: {format_number(signal.get('strength', 0) * 100)}%")
    
    if signal.get('reason'):
        print(f"原因: {signal.get('reason')}")


def cmd_backtest(args):
    """回测命令"""
    stock_code = args.stock
    strategy = args.strategy
    days = args.days
    capital = args.capital
    
    print(f"回测: {stock_code}, 策略: {strategy}")
    
    df = analysis_engine.fetch_data(stock_code, days)
    df = analysis_engine.analyze(df)
    
    if 'trade_date' in df.columns:
        df.set_index('trade_date', inplace=True)
    
    result = analysis_engine.run_backtest(df, strategy, capital)
    
    print("\n=== 回测结果 ===")
    print(f"初始资金: {format_number(result['initial_capital'])}")
    print(f"最终资金: {format_number(result['final_capital'])}")
    print(f"总收益率: {format_number(result['total_return'] * 100)}%")
    print(f"年化收益: {format_number(result['annualized_return'] * 100)}%")
    print(f"最大回撤: {format_number(result['max_drawdown'] * 100)}%")
    print(f"夏普比率: {format_number(result['sharpe_ratio'])}")
    print(f"胜率: {format_number(result['win_rate'] * 100)}%")
    print(f"交易次数: {result['total_trades']}")


def cmd_dashboard(args):
    """启动仪表盘"""
    port = args.port
    print(f"启动Streamlit仪表盘...")
    import sys
    os.system(f'"{sys.executable}" -m streamlit run src/visualization/dashboard/app.py --server.port {port}')


def cmd_api(args):
    """启动API服务"""
    port = args.port
    print(f"启动API服务在端口 {port}...")
    from src.core.api import run_api
    run_api(port=port, debug=True)


def cmd_init_db(args):
    """初始化数据库"""
    print("初始化数据库表...")
    from src.data.storage import get_db_manager
    db = get_db_manager()
    db.init_tables()
    print("数据库表初始化完成")


def main():
    parser = argparse.ArgumentParser(description='股票分析系统')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # fetch 命令
    fetch_parser = subparsers.add_parser('fetch', help='获取股票数据')
    fetch_parser.add_argument('--stock', '-s', required=True, help='股票代码 (如: HK.00700)')
    fetch_parser.add_argument('--days', '-d', type=int, default=120, help='获取天数')
    fetch_parser.add_argument('--save', action='store_true', help='保存到数据库')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='技术分析')
    analyze_parser.add_argument('--stock', '-s', required=True, help='股票代码')
    analyze_parser.add_argument('--days', '-d', type=int, default=120, help='分析天数')
    
    # backtest 命令
    backtest_parser = subparsers.add_parser('backtest', help='策略回测')
    backtest_parser.add_argument('--stock', '-s', required=True, help='股票代码')
    backtest_parser.add_argument('--strategy', type=str, default='combined', 
                                 choices=['combined', 'ma_cross', 'macd', 'rsi', 'limit_chase', 'momentum', 'czsc', 'comprehensive'], 
                                 help='策略: limit_chase(打板), czsc(缠论), comprehensive(综合)')
    backtest_parser.add_argument('--days', '-d', type=int, default=365, help='回测天数')
    backtest_parser.add_argument('--capital', '-c', type=float, default=1000000, help='初始资金')
    
    # dashboard 命令
    dash_parser = subparsers.add_parser('dashboard', help='启动仪表盘')
    dash_parser.add_argument('--port', '-p', type=int, default=8501, help='端口')
    
    # api 命令
    api_parser = subparsers.add_parser('api', help='启动API服务')
    api_parser.add_argument('--port', '-p', type=int, default=5000, help='端口')
    
    # initdb 命令
    initdb_parser = subparsers.add_parser('initdb', help='初始化数据库')
    
    args = parser.parse_args()
    
    if args.command == 'fetch':
        cmd_fetch(args)
    elif args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'dashboard':
        cmd_dashboard(args)
    elif args.command == 'api':
        cmd_api(args)
    elif args.command == 'initdb':
        cmd_init_db(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
