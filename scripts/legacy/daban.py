# -*- coding: utf-8 -*-
"""
打板分析命令
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.collectors import stock_collector
from src.data.processors import data_processor
from src.strategy.signals.limit_chase import limit_chase_strategy
from src.utils.logger import get_logger
from src.utils.helpers import format_number

logger = get_logger(__name__)


def analyze_limit_chase(stock_code: str, days: int = 60):
    """打板分析"""
    print(f"打板分析: {stock_code}")
    print("="*50)
    
    # 获取数据
    df = stock_collector.get_daily_data(stock_code, days=days)
    
    if df.empty:
        print("获取数据失败")
        return
    
    # 数据处理
    df = data_processor.clean_data(df)
    
    # 打板分析
    df = limit_chase_strategy.generate_signals(df)
    
    # 设置索引
    if 'trade_date' in df.columns:
        df.set_index('trade_date', inplace=True)
    
    # 输出分析结果
    latest = df.iloc[-1]
    
    print(f"\n[最新数据]")
    print(f"  收盘价: {format_number(latest.get('close', 0))}")
    print(f"  涨跌幅: {format_number(latest.get('pct_change', 0) * 100)}%")
    print(f"  量比: {format_number(latest.get('volume_ratio', 0))}")
    
    print(f"\n[涨停分析]")
    print(f"  是否涨停: {'是' if latest.get('is_limit_up', False) else '否'}")
    print(f"  距离涨停: {format_number(latest.get('dist_to_limit', 0) * 100)}%")
    print(f"  首板: {'是' if latest.get('is_first_limit', False) else '否'}")
    print(f"  二板: {'是' if latest.get('is_second_limit', False) else '否'}")
    
    print(f"\n[交易信号]")
    if latest.get('signal', 0) == 1:
        print(f"  信号: 买入")
        print(f"  类型: {latest.get('signal_type', 'N/A')}")
        print(f"  强度: {format_number(latest.get('signal_score', 0) * 100)}%")
        
        buy_price = latest.get('close', 0)
        signal_type = latest.get('signal_type', '').split('+')[0]
        stop_loss = limit_chase_strategy.get_stop_loss_price(buy_price, signal_type)
        take_profit = limit_chase_strategy.get_take_profit_price(buy_price, signal_type)
        
        print(f"  止损价: {format_number(stop_loss)}")
        print(f"  止盈价: {format_number(take_profit)}")
    else:
        print(f"  信号: 暂无信号")
    
    # 历史涨停统计
    limit_up_count = len(df[df['is_limit_up'] == True])
    first_limit_count = len(df[df['is_first_limit'] == True])
    
    print(f"\n[近{days}日统计]")
    print(f"  涨停天数: {limit_up_count}天")
    print(f"  首板次数: {first_limit_count}次")
    
    # 显示最近有信号的日期
    signals = df[df['signal'] == 1]
    if not signals.empty:
        print(f"\n[最近信号]")
        for idx in signals.tail(5).index:
            row = df.loc[idx]
            dt = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            print(f"  {dt}: {row.get('signal_type', '')} ({format_number(row.get('signal_score', 0)*100)}%)")
    
    print("="*50)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='打板分析')
    parser.add_argument('--stock', '-s', required=True, help='股票代码')
    parser.add_argument('--days', '-d', type=int, default=60, help='分析天数')
    
    args = parser.parse_args()
    analyze_limit_chase(args.stock, args.days)
