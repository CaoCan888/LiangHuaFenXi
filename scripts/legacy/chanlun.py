# -*- coding: utf-8 -*-
"""
缠论分析脚本
"""

import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 禁用过多日志
import logging
logging.disable(logging.WARNING)

from src.data.collectors import stock_collector
from src.data.processors import data_processor
from src.strategy.signals.chan_strategy import chan_analyzer, chan_signal_generator
from src.utils.helpers import format_number


def analyze_chan(stock_code: str, days: int = 120):
    """缠论分析"""
    print("="*50)
    print(f"缠论分析: {stock_code}")
    print("="*50)
    
    # 获取数据
    df = stock_collector.get_daily_data(stock_code, days=days)
    
    if df.empty:
        print("获取数据失败")
        return
    
    # 数据处理
    df = data_processor.clean_data(df)
    
    # 设置索引
    if 'trade_date' in df.columns:
        df.set_index('trade_date', inplace=True)
    
    # 缠论分析
    result = chan_analyzer.analyze(df)
    
    print(f"\n[K线信息]")
    print(f"  原始K线数: {len(df)}")
    print(f"  处理后K线数: {result['processed_bars']}")
    
    print(f"\n[分型识别]")
    print(f"  分型总数: {result['fx_count']}")
    
    if result['fx_list']:
        # 统计顶底分型
        top_count = sum(1 for fx in result['fx_list'] if fx.mark.value == '顶分型')
        bottom_count = sum(1 for fx in result['fx_list'] if fx.mark.value == '底分型')
        print(f"  顶分型: {top_count}个")
        print(f"  底分型: {bottom_count}个")
        
        # 最近3个分型
        print(f"\n  最近分型:")
        for fx in result['fx_list'][-3:]:
            dt = fx.dt.strftime('%Y-%m-%d') if hasattr(fx.dt, 'strftime') else str(fx.dt)
            print(f"    {dt}: {fx.mark.value} @ {format_number(fx.fx)}")
    
    print(f"\n[笔划分]")
    print(f"  笔总数: {result['bi_count']}")
    
    if result['bi_list']:
        # 最近3笔
        print(f"\n  最近3笔:")
        for bi in result['bi_list'][-3:]:
            start = bi.start_dt.strftime('%Y-%m-%d') if hasattr(bi.start_dt, 'strftime') else str(bi.start_dt)
            end = bi.end_dt.strftime('%Y-%m-%d') if hasattr(bi.end_dt, 'strftime') else str(bi.end_dt)
            direction = '↑' if bi.direction.value == 'up' else '↓'
            print(f"    {start} -> {end}: {direction} 力度:{format_number(bi.power*100)}%")
    
    # 买卖点信号
    bs_result = chan_analyzer.get_bs_point(df)
    
    print(f"\n[买卖点判断]")
    if bs_result['latest_bi']:
        print(f"  最新笔方向: {'上涨' if bs_result['latest_bi']['direction']=='up' else '下跌'}")
    if bs_result['latest_fx']:
        print(f"  最新分型: {bs_result['latest_fx']['mark']}")
    
    if bs_result['signal'] == 1:
        print(f"  信号: 【买入信号】 - {bs_result['signal_type']}")
    elif bs_result['signal'] == -1:
        print(f"  信号: 【卖出信号】 - {bs_result['signal_type']}")
    else:
        print(f"  信号: 暂无明确信号")
    
    print(f"  建议: {bs_result['suggestion']}")
    
    # 生成完整信号序列并统计
    df_signals = chan_signal_generator.generate_signals(df.copy())
    buy_signals = len(df_signals[df_signals['signal'] == 1])
    sell_signals = len(df_signals[df_signals['signal'] == -1])
    
    print(f"\n[历史信号统计]")
    print(f"  买入信号: {buy_signals}次")
    print(f"  卖出信号: {sell_signals}次")
    
    # 最近信号
    recent_signals = df_signals[df_signals['signal'] != 0].tail(5)
    if not recent_signals.empty:
        print(f"\n  最近信号:")
        for idx in recent_signals.index:
            row = df_signals.loc[idx]
            dt = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            signal_text = '买入' if row['signal'] == 1 else '卖出'
            print(f"    {dt}: {signal_text} - {row.get('signal_type', '')}")
    
    print("="*50)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='缠论分析')
    parser.add_argument('--stock', '-s', required=True, help='股票代码')
    parser.add_argument('--days', '-d', type=int, default=120, help='分析天数')
    
    args = parser.parse_args()
    analyze_chan(args.stock, args.days)
