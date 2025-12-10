# -*- coding: utf-8 -*-
"""
综合分析脚本 - 技术评分+多策略信号
"""

import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.disable(logging.WARNING)

from src.data.collectors import stock_collector
from src.data.processors import data_processor
from src.strategy.signals.comprehensive_strategy import (
    comprehensive_signal_generator, 
    technical_scorer,
    czsc_bar_signals
)
from src.strategy.signals.limit_chase import limit_chase_strategy
from src.strategy.signals.chan_strategy import chan_analyzer
from src.utils.helpers import format_number


def analyze_comprehensive(stock_code: str, days: int = 120):
    """综合分析"""
    print("="*55)
    print(f"综合分析: {stock_code}")
    print("="*55)
    
    # 获取数据
    df = stock_collector.get_daily_data(stock_code, days=days)
    
    if df.empty:
        print("获取数据失败")
        return
    
    # 数据处理
    df = data_processor.clean_data(df)
    
    # 设置索引
    if 'trade_date' in df.columns:
        df_indexed = df.set_index('trade_date')
    else:
        df_indexed = df
    
    latest = df_indexed.iloc[-1]
    
    # === 基本信息 ===
    print(f"\n[基本信息]")
    print(f"  最新收盘: {format_number(latest['close'])}")
    if 'pct_change' in df_indexed.columns:
        print(f"  今日涨幅: {format_number(latest['pct_change']*100 if latest['pct_change'] < 1 else latest['pct_change'])}%")
    
    # === 技术评分 ===
    print(f"\n[技术评分] (满分100)")
    scores = technical_scorer.calculate_total_score(df_indexed)
    print(f"  均线评分: {format_number(scores['ma_score'])}")
    print(f"  MACD评分: {format_number(scores['macd_score'])}")
    print(f"  RSI评分: {format_number(scores['rsi_score'])}")
    print(f"  量能评分: {format_number(scores['volume_score'])}")
    print(f"  趋势评分: {format_number(scores['trend_score'])}")
    print(f"  形态评分: {format_number(scores['pattern_score'])}")
    print(f"  -----------------------")
    print(f"  综合评分: {format_number(scores['total_score'])} 【{scores['rating']}】")
    
    # === CZSC经典策略信号 ===
    print(f"\n[CZSC经典策略]")
    
    # R-Breaker
    df_r = czsc_bar_signals.r_breaker(df_indexed.copy())
    r_signal = df_r.iloc[-1].get('r_signal', 0)
    r_type = df_r.iloc[-1].get('r_type', '')
    print(f"  R-Breaker: {'买入' if r_signal==1 else ('卖出' if r_signal==-1 else '无')} {r_type}")
    
    # Dual Thrust
    df_dt = czsc_bar_signals.dual_thrust(df_indexed.copy())
    dt_signal = df_dt.iloc[-1].get('dt_signal', 0)
    print(f"  Dual Thrust: {'突破做多' if dt_signal==1 else ('突破做空' if dt_signal==-1 else '无')}")
    
    # 双飞涨停
    df_sf = czsc_bar_signals.shuang_fei_zt(df_indexed.copy())
    shuangfei = df_sf.iloc[-1].get('shuangfei', False)
    print(f"  双飞涨停: {'是' if shuangfei else '否'}")
    
    # 跌停反转
    df_ld = czsc_bar_signals.limit_down_reverse(df_indexed.copy())
    ld_reverse = df_ld.iloc[-1].get('ld_reverse', False)
    print(f"  跌停反转: {'是' if ld_reverse else '否'}")
    
    # TNR趋势
    df_tnr = czsc_bar_signals.tnr_trend(df_indexed.copy())
    tnr = df_tnr.iloc[-1].get('tnr', 0)
    tnr_text = '强趋势' if tnr > 0.5 else ('弱趋势' if tnr > 0.3 else '震荡')
    print(f"  TNR趋势: {format_number(tnr)} ({tnr_text})")
    
    # === 打板分析 ===
    print(f"\n[打板分析]")
    df_limit = limit_chase_strategy.generate_signals(df_indexed.copy())
    limit_latest = df_limit.iloc[-1]
    print(f"  是否涨停: {'是' if limit_latest.get('is_limit_up', False) else '否'}")
    if limit_latest.get('is_first_limit', False):
        print(f"  首板信号: 是")
    if limit_latest.get('is_second_limit', False):
        print(f"  二板信号: 是")
    if limit_latest.get('signal', 0) == 1:
        print(f"  打板信号: {limit_latest.get('signal_type', '')}")
    
    # === 缠论分析 ===
    print(f"\n[缠论分析]")
    chan_result = chan_analyzer.analyze(df_indexed)
    print(f"  分型数: {chan_result['fx_count']}")
    print(f"  笔数: {chan_result['bi_count']}")
    if chan_result['latest_fx']:
        print(f"  最新分型: {chan_result['latest_fx'].mark.value}")
    if chan_result['latest_bi']:
        direction = '上涨' if chan_result['latest_bi'].direction.value == 'up' else '下跌'
        print(f"  最新笔: {direction}")
    
    bs = chan_analyzer.get_bs_point(df_indexed)
    if bs['signal'] == 1:
        print(f"  买卖点: 买入信号 ({bs['signal_type']})")
    elif bs['signal'] == -1:
        print(f"  买卖点: 卖出信号 ({bs['signal_type']})")
    else:
        print(f"  买卖点: 无")
    
    # === 综合建议 ===
    print(f"\n[综合建议]")
    
    # 计算综合得分
    total_signals = 0
    buy_weight = 0
    
    if scores['total_score'] >= 70:
        buy_weight += 0.3
        total_signals += 1
    elif scores['total_score'] >= 60:
        buy_weight += 0.15
    
    if r_signal == 1:
        buy_weight += 0.2
        total_signals += 1
    
    if dt_signal == 1:
        buy_weight += 0.15
        total_signals += 1
    
    if shuangfei:
        buy_weight += 0.3
        total_signals += 1
    
    if limit_latest.get('is_limit_up', False):
        buy_weight += 0.2
        total_signals += 1
    
    if bs['signal'] == 1:
        buy_weight += 0.2
        total_signals += 1
    
    if buy_weight >= 0.5:
        suggestion = "强烈看多"
    elif buy_weight >= 0.3:
        suggestion = "偏多"
    elif buy_weight >= 0.15:
        suggestion = "中性"
    else:
        suggestion = "观望"
    
    print(f"  多头信号数: {total_signals}")
    print(f"  综合权重: {format_number(buy_weight*100)}%")
    print(f"  操作建议: 【{suggestion}】")
    
    print("="*55)
    
    return {
        'scores': scores,
        'signals': total_signals,
        'weight': buy_weight,
        'suggestion': suggestion
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='综合分析')
    parser.add_argument('--stock', '-s', required=True, help='股票代码')
    parser.add_argument('--days', '-d', type=int, default=120, help='分析天数')
    
    args = parser.parse_args()
    analyze_comprehensive(args.stock, args.days)
