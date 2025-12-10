# -*- coding: utf-8 -*-
"""
分时策略模块
识别分时图形态并生成交易信号
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum


class IntradayPattern(Enum):
    """分时形态类型"""
    EARLY_SURGE = "早盘急拉"
    LATE_SURGE = "尾盘拉升"
    HIGH_OPEN_LOW = "高开低走"
    LOW_OPEN_HIGH = "低开高走"
    MA_BREAK_UP = "均价上穿"
    MA_BREAK_DOWN = "均价下穿"
    W_BOTTOM = "W底形态"
    M_TOP = "M顶形态"
    VOLUME_PRICE_UP = "量价齐升"
    VOLUME_DIVERGE = "量价背离"
    CONSOLIDATION = "横盘整理"


@dataclass
class IntradaySignal:
    """分时信号"""
    pattern: IntradayPattern
    direction: str  # 'buy', 'sell', 'hold'
    confidence: int  # 0-100
    message: str
    timestamp: str
    match_quality: float = 1.0  # 形态匹配度 0-1.0，用于过滤低质量信号
    
    def to_dict(self) -> dict:
        return {
            'pattern': self.pattern.value,
            'direction': self.direction,
            'confidence': self.confidence,
            'message': self.message,
            'timestamp': self.timestamp,
            'match_quality': self.match_quality
        }
    
    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """判断信号是否高质量"""
        return self.match_quality >= threshold


class IntradayPatternAnalyzer:
    """分时形态分析器"""
    
    def __init__(self):
        pass
    
    def analyze(self, df: pd.DataFrame, pre_close: float = None) -> List[IntradaySignal]:
        """
        分析分时数据，识别形态
        
        Args:
            df: 分时数据 (columns: time, open, high, low, close, volume)
            pre_close: 昨收价
            
        Returns:
            信号列表
        """
        if df is None or df.empty or len(df) < 5:
            return []
        
        signals = []
        
        # 计算基础指标
        df = df.copy()
        df['avg_price'] = df['close'].expanding().mean()
        df['pct_change'] = df['close'].pct_change() * 100
        df['vol_ma'] = df['volume'].rolling(5, min_periods=1).mean()
        
        current_price = df['close'].iloc[-1]
        open_price = df['open'].iloc[0]
        avg_price = df['avg_price'].iloc[-1]
        high_price = df['high'].max()
        low_price = df['low'].min()
        
        if pre_close is None:
            pre_close = open_price
        
        total_change = (current_price / pre_close - 1) * 100
        
        # 1. 高开低走 / 低开高走
        signal = self._check_open_pattern(df, open_price, current_price, pre_close)
        if signal:
            signals.append(signal)
        
        # 2. 早盘急拉 / 尾盘拉升
        signal = self._check_surge_pattern(df, pre_close)
        if signal:
            signals.append(signal)
        
        # 3. 均价突破
        signal = self._check_ma_cross(df)
        if signal:
            signals.append(signal)
        
        # 4. W底 / M顶
        signal = self._check_wm_pattern(df)
        if signal:
            signals.append(signal)
        
        # 5. 量价关系
        signal = self._check_volume_price(df)
        if signal:
            signals.append(signal)
        
        return signals
    
    def _check_open_pattern(self, df, open_price, current, pre_close) -> Optional[IntradaySignal]:
        """检测开盘形态"""
        open_change = (open_price / pre_close - 1) * 100
        current_change = (current / pre_close - 1) * 100
        
        # 高开低走
        if open_change > 2 and current_change < open_change - 2:
            return IntradaySignal(
                pattern=IntradayPattern.HIGH_OPEN_LOW,
                direction='sell',
                confidence=70,
                message=f"高开{open_change:.1f}%后回落，现涨{current_change:.1f}%",
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
        
        # 低开高走
        if open_change < -1 and current_change > open_change + 2:
            return IntradaySignal(
                pattern=IntradayPattern.LOW_OPEN_HIGH,
                direction='buy',
                confidence=75,
                message=f"低开{open_change:.1f}%后拉升，现涨{current_change:.1f}%",
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
        
        return None
    
    def _check_surge_pattern(self, df, pre_close) -> Optional[IntradaySignal]:
        """检测急拉形态"""
        if len(df) < 6:
            return None
        
        # 判断当前时段
        now = datetime.now()
        
        # 早盘急拉（前6根5分钟线，即前30分钟）
        if len(df) >= 6:
            early_df = df.head(6)
            early_high = early_df['high'].max()
            early_change = (early_high / pre_close - 1) * 100
            
            if early_change > 5:
                # 动态计算匹配度: 涨幅越大，信号越强
                match_quality = min(1.0, 0.5 + (early_change - 5) * 0.1)  # 涨幅10%以上得满分
                
                return IntradaySignal(
                    pattern=IntradayPattern.EARLY_SURGE,
                    direction='hold',
                    confidence=65,
                    message=f"早盘30分钟内急拉{early_change:.1f}%，注意追高风险",
                    timestamp=datetime.now().strftime('%H:%M:%S'),
                    match_quality=match_quality
                )
        
        # 尾盘拉升（最后6根线）
        if len(df) >= 12 and now.hour >= 14:
            late_df = df.tail(6)
            late_start = late_df['close'].iloc[0]
            late_end = late_df['close'].iloc[-1]
            late_change = (late_end / late_start - 1) * 100
            
            if late_change > 2:
                return IntradaySignal(
                    pattern=IntradayPattern.LATE_SURGE,
                    direction='hold',
                    confidence=60,
                    message=f"尾盘拉升{late_change:.1f}%，次日可能高开",
                    timestamp=datetime.now().strftime('%H:%M:%S')
                )
        
        return None
    
    def _check_ma_cross(self, df) -> Optional[IntradaySignal]:
        """检测均价突破"""
        if len(df) < 3:
            return None
        
        current = df['close'].iloc[-1]
        prev = df['close'].iloc[-2]
        avg_now = df['avg_price'].iloc[-1]
        avg_prev = df['avg_price'].iloc[-2]
        
        # 上穿均价
        if prev < avg_prev and current > avg_now:
            return IntradaySignal(
                pattern=IntradayPattern.MA_BREAK_UP,
                direction='buy',
                confidence=70,
                message=f"价格上穿均价线 ({avg_now:.2f})，买入信号",
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
        
        # 下穿均价
        if prev > avg_prev and current < avg_now:
            return IntradaySignal(
                pattern=IntradayPattern.MA_BREAK_DOWN,
                direction='sell',
                confidence=70,
                message=f"价格下穿均价线 ({avg_now:.2f})，卖出信号",
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
        
        return None
    
    def _check_wm_pattern(self, df) -> Optional[IntradaySignal]:
        """检测W底/M顶形态"""
        if len(df) < 15:
            return None
        
        closes = df['close'].values
        
        # 寻找极值点
        highs = []
        lows = []
        
        for i in range(2, len(closes) - 2):
            if closes[i] > closes[i-1] and closes[i] > closes[i+1] and \
               closes[i] > closes[i-2] and closes[i] > closes[i+2]:
                highs.append((i, closes[i]))
            if closes[i] < closes[i-1] and closes[i] < closes[i+1] and \
               closes[i] < closes[i-2] and closes[i] < closes[i+2]:
                lows.append((i, closes[i]))
        
        # W底：两个低点，第二个不低于第一个
        if len(lows) >= 2:
            last_two_lows = lows[-2:]
            low1, low2 = last_two_lows[0][1], last_two_lows[1][1]
            
            if low2 >= low1 * 0.99:  # 允许1%误差
                current = closes[-1]
                if current > low2 * 1.01:  # 价格已回升
                    # 动态计算匹配度
                    # 1. 两低点越接近，匹配度越高
                    low_diff_ratio = abs(low2 - low1) / low1
                    low_quality = max(0.5, 1.0 - low_diff_ratio * 5)  # 差距小于2%得满分
                    
                    # 2. 回升幅度越大，匹配度越高
                    recovery_ratio = (current - low2) / low2
                    recovery_quality = min(1.0, 0.5 + recovery_ratio * 10)  # 回升2%以上得满分
                    
                    match_quality = (low_quality + recovery_quality) / 2
                    
                    return IntradaySignal(
                        pattern=IntradayPattern.W_BOTTOM,
                        direction='buy',
                        confidence=75,
                        message=f"W底形态确认，两低点差{low_diff_ratio*100:.1f}%，回升{recovery_ratio*100:.1f}%",
                        timestamp=datetime.now().strftime('%H:%M:%S'),
                        match_quality=match_quality
                    )
        
        # M顶：两个高点，第二个不高于第一个
        if len(highs) >= 2:
            last_two_highs = highs[-2:]
            high1, high2 = last_two_highs[0][1], last_two_highs[1][1]
            
            if high2 <= high1 * 1.01:
                current = closes[-1]
                if current < high2 * 0.99:
                    # 动态计算匹配度
                    high_diff_ratio = abs(high2 - high1) / high1
                    high_quality = max(0.5, 1.0 - high_diff_ratio * 5)
                    
                    decline_ratio = (high2 - current) / high2
                    decline_quality = min(1.0, 0.5 + decline_ratio * 10)
                    
                    match_quality = (high_quality + decline_quality) / 2
                    
                    return IntradaySignal(
                        pattern=IntradayPattern.M_TOP,
                        direction='sell',
                        confidence=75,
                        message=f"M顶形态确认，两高点差{high_diff_ratio*100:.1f}%，下跌{decline_ratio*100:.1f}%",
                        timestamp=datetime.now().strftime('%H:%M:%S'),
                        match_quality=match_quality
                    )
        
        return None
    
    def _check_volume_price(self, df) -> Optional[IntradaySignal]:
        """检测量价关系"""
        if len(df) < 10:
            return None
        
        recent = df.tail(10)
        
        price_trend = recent['close'].iloc[-1] - recent['close'].iloc[0]
        vol_trend = recent['volume'].iloc[-5:].mean() - recent['volume'].iloc[:5].mean()
        
        # 量价齐升
        if price_trend > 0 and vol_trend > 0:
            vol_ratio = recent['volume'].iloc[-1] / recent['vol_ma'].iloc[-1]
            if vol_ratio > 1.5:
                # 动态计算匹配度: 量比越大，匹配度越高
                match_quality = min(1.0, 0.5 + (vol_ratio - 1.5) * 0.25)  # 量比3.5以上得满分
                
                return IntradaySignal(
                    pattern=IntradayPattern.VOLUME_PRICE_UP,
                    direction='buy',
                    confidence=70,
                    message=f"量价齐升，量比{vol_ratio:.1f}，强势延续",
                    timestamp=datetime.now().strftime('%H:%M:%S'),
                    match_quality=match_quality
                )
        
        # 量价背离（价涨量缩）
        if price_trend > 0 and vol_trend < 0:
            # 动态计算匹配度: 量能萎缩越严重，信号越强
            vol_shrink_ratio = abs(vol_trend) / (recent['volume'].iloc[:5].mean() + 1)
            match_quality = min(1.0, 0.4 + vol_shrink_ratio * 0.5)  # 基础0.4，量缩越多越高
            
            return IntradaySignal(
                pattern=IntradayPattern.VOLUME_DIVERGE,
                direction='hold',
                confidence=60,
                message=f"量价背离，价涨量缩{vol_shrink_ratio*100:.0f}%，注意回调风险",
                timestamp=datetime.now().strftime('%H:%M:%S'),
                match_quality=match_quality
            )
        
        return None
    
    def get_trading_advice(self, signals: List[IntradaySignal], quality_threshold: float = 0.6) -> dict:
        """
        根据信号生成交易建议
        
        Args:
            signals: 信号列表
            quality_threshold: 质量过滤阈值，低于此值的信号将被降权
        """
        if not signals:
            return {
                'action': 'hold',
                'confidence': 50,
                'reason': '暂无明确分时信号',
                'high_quality_count': 0
            }
        
        buy_score = 0
        sell_score = 0
        reasons = []
        high_quality_count = 0
        
        for s in signals:
            # 根据质量调整权重
            weight = s.match_quality if s.match_quality >= quality_threshold else 0.3
            weighted_conf = s.confidence * weight
            
            if s.is_high_quality(quality_threshold):
                high_quality_count += 1
            
            if s.direction == 'buy':
                buy_score += weighted_conf
                quality_tag = "🎯" if s.is_high_quality() else "📊"
                reasons.append(f"{quality_tag} {s.pattern.value}: {s.message} (质量{s.match_quality:.0%})")
            elif s.direction == 'sell':
                sell_score += weighted_conf
                quality_tag = "🎯" if s.is_high_quality() else "⚠️"
                reasons.append(f"{quality_tag} {s.pattern.value}: {s.message} (质量{s.match_quality:.0%})")
            else:
                reasons.append(f"📊 {s.pattern.value}: {s.message}")
        
        if buy_score > sell_score + 30:
            action = 'buy'
            confidence = min(90, int(buy_score / len(signals)))
        elif sell_score > buy_score + 30:
            action = 'sell'
            confidence = min(90, int(sell_score / len(signals)))
        else:
            action = 'hold'
            confidence = 50
        
        return {
            'action': action,
            'confidence': confidence,
            'reasons': reasons,
            'high_quality_count': high_quality_count
        }


# 全局实例
intraday_analyzer = IntradayPatternAnalyzer()


def analyze_intraday_patterns(df: pd.DataFrame, pre_close: float = None) -> List[IntradaySignal]:
    """便捷函数：分析分时形态"""
    return intraday_analyzer.analyze(df, pre_close)


if __name__ == '__main__':
    # 测试
    from src.data.collectors.realtime_service import get_intraday_data, get_realtime_quote
    
    quote = get_realtime_quote('000592')
    df = get_intraday_data('000592')
    
    if not df.empty and quote:
        signals = analyze_intraday_patterns(df, quote.pre_close)
        print(f"\n000592 分时形态分析:")
        for s in signals:
            print(f"  [{s.direction.upper()}] {s.pattern.value}: {s.message}")
        
        advice = intraday_analyzer.get_trading_advice(signals)
        print(f"\n交易建议: {advice['action'].upper()} (置信度: {advice['confidence']}%)")
