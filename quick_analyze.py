# -*- coding: utf-8 -*-
"""快速分析脚本 - 完整版 (信号聚合版)"""
import sys
import os
sys.path.insert(0, '.')
os.system('chcp 65001 > nul')

from src.data.collectors.realtime_service import get_realtime_quote, get_intraday_data
from src.strategy.signals.intraday_pattern import analyze_intraday_patterns, intraday_analyzer
from src.strategy.signals.trading_advisor import trading_advisor
from src.strategy.ai_analyzer import analyze_stock
from src.strategy.signals.sector_analyzer import sector_analyzer
from src.strategy.signals.sentiment_monitor import sentiment_monitor
from src.strategy.signals.signal_aggregator import SignalAggregator, SignalType

code = '000592'
print(f"\n{'='*50}")
print(f"分析股票: {code}")
print(f"{'='*50}")

# 1. 市场情绪分析
print(f"\n[市场情绪]")
sentiment = sentiment_monitor.get_market_overview()
print(f"   情绪评分: {sentiment.sentiment_score:.0f}分 ({sentiment.sentiment_level})")
print(f"   涨跌家数: 涨{sentiment.up_count} / 跌{sentiment.down_count}")
print(f"   涨停/跌停: {sentiment.limit_up_count} / {sentiment.limit_down_count}")
if sentiment.hot_sectors:
    print(f"   热门板块: {', '.join(sentiment.hot_sectors[:3])}")

# 2. 获取实时行情
q = get_realtime_quote(code)
if q:
    print(f"\n[实时行情]")
    print(f"   名称: {q.name}")
    print(f"   现价: {q.price:.2f} ({q.change_pct:+.2f}%)")
    print(f"   最高/最低: {q.high}/{q.low}")
    print(f"   成交量: {q.volume/10000:.0f}万手")

    # 3. 板块联动分析
    print(f"\n[板块联动]")
    sector_result = sector_analyzer.analyze(code, q.name)
    print(f"   板块强度: {sector_result.sector_strength}")
    print(f"   连板加成: +{sector_result.limit_continuation_boost*100:.0f}%")
    if sector_result.sectors:
        print(f"   所属板块: {', '.join([s.sector_name for s in sector_result.sectors])}")

    # 4. 分时形态分析
    df = get_intraday_data(code)
    if not df.empty:
        signals = analyze_intraday_patterns(df, q.pre_close)
        print(f"\n[分时信号] {len(signals)}个")
        for s in signals:
            quality_tag = "[高质量]" if s.is_high_quality() else ""
            print(f"   [{s.direction}] {s.pattern.value} {quality_tag}")
            print(f"      {s.message} (质量{s.match_quality:.0%})")
        
        advice = intraday_analyzer.get_trading_advice(signals)
        print(f"\n[分时建议] {advice['action'].upper()} (置信度{advice['confidence']}%)")
        print(f"   高质量信号数: {advice.get('high_quality_count', 0)}")
    else:
        signals = []
    
    # 5. 获取历史K线计算技术指标
    print(f"\n[历史数据分析]")
    from src.data.collectors.stock_collector import StockCollector
    collector = StockCollector()
    
    historical_summary = ""
    support_level = 0.0
    resistance_level = 0.0
    volume_ratio = 1.0
    macd_signal = ""
    rsi_value = 50.0
    
    try:
        hist_df = collector.get_daily_data(code, days=30)
        if hist_df is not None and len(hist_df) >= 10:
            # 计算5日/20日均线
            ma5 = hist_df['close'].rolling(5).mean().iloc[-1]
            ma20 = hist_df['close'].rolling(20).mean().iloc[-1] if len(hist_df) >= 20 else ma5
            
            if q.price > ma5 > ma20:
                historical_summary = "多头排列，上升趋势"
            elif q.price < ma5 < ma20:
                historical_summary = "空头排列，下跌趋势"
            else:
                historical_summary = "均线纠缠，震荡整理"
            
            # 计算支撑/压力位
            support_level = hist_df['low'].tail(5).min()
            resistance_level = hist_df['high'].tail(5).max()
            
            # 量比
            avg_vol = hist_df['volume'].tail(5).mean()
            if avg_vol > 0:
                volume_ratio = q.volume / avg_vol
            
            # MACD判断
            ema12 = hist_df['close'].ewm(span=12).mean()
            ema26 = hist_df['close'].ewm(span=26).mean()
            diff = ema12 - ema26
            if len(diff) >= 2:
                if diff.iloc[-1] > diff.iloc[-2]:
                    macd_signal = "MACD上升"
                else:
                    macd_signal = "MACD下降"
            
            # RSI计算
            delta = hist_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1] if not rsi.empty else 50.0
            
            print(f"   历史趋势: {historical_summary}")
            print(f"   支撑/压力: {support_level:.2f} / {resistance_level:.2f}")
            print(f"   量比: {volume_ratio:.2f}")
            print(f"   MACD: {macd_signal}")
            print(f"   RSI: {rsi_value:.1f}")
    except Exception as e:
        print(f"   获取历史数据失败: {e}")
    
    # 6. 信号聚合 (多策略投票)
    print(f"\n[信号聚合]")
    aggregator = SignalAggregator()
    
    # 添加分时信号
    for s in signals:
        signal_type = 'BUY' if s.direction == 'buy' else 'SELL' if s.direction == 'sell' else 'HOLD'
        aggregator.add_signal(
            strategy_name='intraday_pattern',
            signal=signal_type,
            confidence=s.confidence * s.match_quality,
            reasons=[s.message]
        )
    
    # 添加技术指标信号
    if macd_signal == "MACD上升" and rsi_value < 70:
        aggregator.add_signal('technical', 'BUY', 65, ['MACD上升趋势', f'RSI={rsi_value:.0f}'])
    elif macd_signal == "MACD下降" and rsi_value > 30:
        aggregator.add_signal('technical', 'SELL', 60, ['MACD下降趋势', f'RSI={rsi_value:.0f}'])
    else:
        aggregator.add_signal('technical', 'HOLD', 50, ['技术指标中性'])
    
    # 添加趋势信号
    if "多头排列" in historical_summary:
        aggregator.add_signal('trend', 'BUY', 70, ['MA多头排列'])
    elif "空头排列" in historical_summary:
        aggregator.add_signal('trend', 'SELL', 70, ['MA空头排列'])
    else:
        aggregator.add_signal('trend', 'HOLD', 50, ['均线纠缠'])
    
    # 添加板块联动信号
    if sector_result.limit_continuation_boost > 0.1:
        aggregator.add_signal('sector', 'BUY', 60, [f'板块强势，加成{sector_result.limit_continuation_boost*100:.0f}%'])
    
    # 聚合结果
    agg_result = aggregator.aggregate()
    print(f"   综合决策: {agg_result.final_signal.value} ({agg_result.confidence:.0f}%)")
    print(f"   信号分布: 买{agg_result.buy_score:.0f} / 卖{agg_result.sell_score:.0f} / 持{agg_result.hold_score:.0f}")
    print(f"   摘要: {agg_result.summary}")
    
    # 7. 准备技术指标
    indicators = {
        "市场情绪": f"{sentiment.sentiment_score:.0f}分({sentiment.sentiment_level})",
        "涨停家数": f"{sentiment.limit_up_count}",
        "板块强度": sector_result.sector_strength,
        "连板加成": f"+{sector_result.limit_continuation_boost*100:.0f}%",
        "信号聚合": f"{agg_result.final_signal.value}({agg_result.confidence:.0f}%)"
    }
    
    # 8. AI分析 (传入完整数据)
    print(f"\n[AI分析] 正在调用Groq (传入完整数据)...")
    print(f"   - 分时信号: {len(signals)}个")
    print(f"   - 技术指标: {len(indicators)}项")
    print(f"   - 历史数据: 已计算")
    print(f"   - 聚合决策: {agg_result.final_signal.value}")
    
    result = analyze_stock(
        code=code,
        name=q.name,
        price=q.price,
        change_pct=q.change_pct,
        volume=q.volume,
        amount=q.amount,
        high=q.high,
        low=q.low,
        open_price=q.open,
        pre_close=q.pre_close,
        signals=[s.pattern.value for s in signals if s.direction == 'buy'],
        patterns=[s.pattern.value for s in signals],
        pressure="买盘较强" if q.change_pct > 0 else "卖盘较强",
        fund_flow=f"涨{sentiment.up_count}/跌{sentiment.down_count}",
        ma_position="上涨趋势" if q.price > q.pre_close else "下跌趋势",
        indicators=indicators,
        recent_trend=f"今日涨{q.change_pct:+.2f}%",
        # 新增历史数据
        historical_summary=historical_summary,
        support_level=support_level,
        resistance_level=resistance_level,
        volume_ratio=volume_ratio,
        macd_signal=macd_signal,
        rsi_value=rsi_value
    )
    print(f"\n{result}")
    
    # 9. 保存分析结果到数据库
    print(f"\n[数据库存储]")
    try:
        from src.data.services.db_service import db_service
        
        saved = db_service.save_analysis(
            stock_code=code,
            stock_name=q.name,
            price=q.price,
            change_pct=q.change_pct,
            aggregated_signal=agg_result.final_signal.value,
            signal_confidence=agg_result.confidence,
            buy_score=agg_result.buy_score,
            sell_score=agg_result.sell_score,
            hold_score=agg_result.hold_score,
            ai_response=result,
            ma_trend=historical_summary,
            macd_signal=macd_signal,
            rsi_value=rsi_value,
            support_level=support_level,
            resistance_level=resistance_level
        )
        
        if saved:
            print(f"   分析记录已保存到数据库")
        else:
            print(f"   数据库保存失败（可能未配置）")
            
        # 缓存日K线数据
        if hist_df is not None and not hist_df.empty:
            cached = db_service.cache_daily_data(code, hist_df)
            if cached:
                print(f"   日K线数据已缓存")
                
    except Exception as e:
        print(f"   数据库操作失败: {e}")
        
else:
    print("获取行情失败")
