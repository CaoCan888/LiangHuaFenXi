# -*- coding: utf-8 -*-
"""
Stock Analysis System - Technical Analyzer
技术分析引擎
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.analysis.indicators import TechnicalIndicators
from src.analysis.technical.pattern_recognition import PatternRecognition
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalAnalyzer:
    """技术分析引擎"""
    
    def __init__(self):
        """初始化技术分析器"""
        self.indicators = TechnicalIndicators
        self.patterns = PatternRecognition
    
    def analyze(self, df: pd.DataFrame, include_patterns: bool = True) -> pd.DataFrame:
        """
        执行完整技术分析
        
        Args:
            df: OHLCV数据
            include_patterns: 是否包含形态识别
            
        Returns:
            添加技术指标和形态的DataFrame
        """
        if df.empty:
            return df
        
        # 添加技术指标
        df = self.indicators.add_all_indicators(df)
        
        # 添加形态识别
        if include_patterns:
            df = self.patterns.scan_patterns(df)
        
        logger.info("技术分析完成")
        return df
    
    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 包含技术指标的DataFrame
            
        Returns:
            添加信号的DataFrame
        """
        df = df.copy()
        
        # 初始化信号列
        df['signal'] = 0  # 0: 持有, 1: 买入, -1: 卖出
        df['signal_strength'] = 0.0  # 信号强度 0-1
        df['signal_reason'] = ''  # 信号原因
        
        for idx in range(1, len(df)):
            signals = []
            strength = 0.0
            reasons = []
            
            curr = df.iloc[idx]
            prev = df.iloc[idx - 1]
            
            # MACD金叉/死叉
            if 'macd' in curr and 'macd_signal' in curr:
                if pd.notna(curr['macd']) and pd.notna(prev['macd']):
                    # 金叉
                    if prev['macd'] < prev['macd_signal'] and curr['macd'] > curr['macd_signal']:
                        signals.append(1)
                        strength += 0.3
                        reasons.append('MACD金叉')
                    # 死叉
                    elif prev['macd'] > prev['macd_signal'] and curr['macd'] < curr['macd_signal']:
                        signals.append(-1)
                        strength += 0.3
                        reasons.append('MACD死叉')
            
            # RSI超买超卖
            if 'rsi_14' in curr:
                if pd.notna(curr['rsi_14']):
                    if curr['rsi_14'] < 30:
                        signals.append(1)
                        strength += 0.2
                        reasons.append('RSI超卖')
                    elif curr['rsi_14'] > 70:
                        signals.append(-1)
                        strength += 0.2
                        reasons.append('RSI超买')
            
            # 均线金叉/死叉
            if 'ma5' in curr and 'ma20' in curr:
                if pd.notna(curr['ma5']) and pd.notna(prev['ma5']):
                    if prev['ma5'] < prev['ma20'] and curr['ma5'] > curr['ma20']:
                        signals.append(1)
                        strength += 0.25
                        reasons.append('MA5上穿MA20')
                    elif prev['ma5'] > prev['ma20'] and curr['ma5'] < curr['ma20']:
                        signals.append(-1)
                        strength += 0.25
                        reasons.append('MA5下穿MA20')
            
            # KDJ信号
            if 'kdj_k' in curr and 'kdj_d' in curr:
                if pd.notna(curr['kdj_k']) and pd.notna(prev['kdj_k']):
                    if prev['kdj_k'] < prev['kdj_d'] and curr['kdj_k'] > curr['kdj_d']:
                        if curr['kdj_k'] < 20:
                            signals.append(1)
                            strength += 0.2
                            reasons.append('KDJ低位金叉')
                    elif prev['kdj_k'] > prev['kdj_d'] and curr['kdj_k'] < curr['kdj_d']:
                        if curr['kdj_k'] > 80:
                            signals.append(-1)
                            strength += 0.2
                            reasons.append('KDJ高位死叉')
            
            # 布林带信号
            if 'boll_lower' in curr and 'boll_upper' in curr:
                if pd.notna(curr['boll_lower']):
                    if curr['close'] < curr['boll_lower']:
                        signals.append(1)
                        strength += 0.15
                        reasons.append('触及布林下轨')
                    elif curr['close'] > curr['boll_upper']:
                        signals.append(-1)
                        strength += 0.15
                        reasons.append('突破布林上轨')
            
            # K线形态信号
            if 'pattern_direction' in curr and pd.notna(curr['pattern_direction']):
                if curr['pattern_direction'] == 'bullish':
                    signals.append(1)
                    strength += 0.2
                    reasons.append(f"看涨形态:{curr.get('pattern', '')}")
                elif curr['pattern_direction'] == 'bearish':
                    signals.append(-1)
                    strength += 0.2
                    reasons.append(f"看跌形态:{curr.get('pattern', '')}")
            
            # 综合信号
            if signals:
                signal = 1 if sum(signals) > 0 else (-1 if sum(signals) < 0 else 0)
                df.loc[df.index[idx], 'signal'] = signal
                df.loc[df.index[idx], 'signal_strength'] = min(strength, 1.0)
                df.loc[df.index[idx], 'signal_reason'] = '; '.join(reasons)
        
        logger.info("交易信号生成完成")
        return df
    
    def get_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """
        计算支撑位和阻力位
        
        Args:
            df: OHLC数据
            window: 窗口大小
            
        Returns:
            包含支撑位和阻力位的字典
        """
        supports = []
        resistances = []
        
        for i in range(window, len(df) - window):
            # 局部最低点作为支撑位
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                supports.append(df['low'].iloc[i])
            
            # 局部最高点作为阻力位
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                resistances.append(df['high'].iloc[i])
        
        # 合并相近的支撑/阻力位
        supports = self._merge_levels(supports)
        resistances = self._merge_levels(resistances)
        
        return {
            'supports': sorted(supports)[-5:],  # 最近5个支撑位
            'resistances': sorted(resistances)[:5]  # 最近5个阻力位
        }
    
    def _merge_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """合并相近的价位"""
        if not levels:
            return []
        
        levels = sorted(levels)
        merged = [levels[0]]
        
        for level in levels[1:]:
            if (level - merged[-1]) / merged[-1] > threshold:
                merged.append(level)
            else:
                merged[-1] = (merged[-1] + level) / 2
        
        return merged
    
    def get_trend(self, df: pd.DataFrame, period: int = 20) -> str:
        """
        判断趋势方向
        
        Args:
            df: OHLC数据
            period: 观察周期
            
        Returns:
            趋势方向 'uptrend'/'downtrend'/'sideways'
        """
        if len(df) < period:
            return 'unknown'
        
        recent = df.tail(period)
        
        # 使用线性回归斜率判断趋势
        x = np.arange(len(recent))
        y = recent['close'].values
        
        slope = np.polyfit(x, y, 1)[0]
        
        # 归一化斜率
        avg_price = recent['close'].mean()
        normalized_slope = slope / avg_price * 100
        
        if normalized_slope > 0.1:
            return 'uptrend'
        elif normalized_slope < -0.1:
            return 'downtrend'
        else:
            return 'sideways'
    
    def get_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取技术分析摘要
        
        Args:
            df: 技术分析后的DataFrame
            
        Returns:
            分析摘要字典
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        summary = {
            'latest_price': latest.get('close'),
            'trend': self.get_trend(df),
            'ma_status': {
                'ma5': latest.get('ma5'),
                'ma20': latest.get('ma20'),
                'ma60': latest.get('ma60'),
                'position': 'above_ma' if latest.get('close', 0) > latest.get('ma20', 0) else 'below_ma'
            },
            'macd_status': {
                'macd': latest.get('macd'),
                'signal': latest.get('macd_signal'),
                'histogram': latest.get('macd_hist'),
                'trend': 'bullish' if latest.get('macd_hist', 0) > 0 else 'bearish'
            },
            'rsi_status': {
                'rsi_14': latest.get('rsi_14'),
                'condition': 'overbought' if latest.get('rsi_14', 50) > 70 else ('oversold' if latest.get('rsi_14', 50) < 30 else 'neutral')
            },
            'kdj_status': {
                'k': latest.get('kdj_k'),
                'd': latest.get('kdj_d'),
                'j': latest.get('kdj_j')
            },
            'boll_status': {
                'upper': latest.get('boll_upper'),
                'middle': latest.get('boll_middle'),
                'lower': latest.get('boll_lower'),
                'position': self._get_boll_position(latest)
            },
            'latest_pattern': latest.get('pattern'),
            'latest_signal': {
                'direction': 'buy' if latest.get('signal', 0) > 0 else ('sell' if latest.get('signal', 0) < 0 else 'hold'),
                'strength': latest.get('signal_strength', 0),
                'reason': latest.get('signal_reason', '')
            }
        }
        
        return summary
    
    def _get_boll_position(self, row: pd.Series) -> str:
        """获取价格在布林带中的位置"""
        close = row.get('close', 0)
        upper = row.get('boll_upper', 0)
        lower = row.get('boll_lower', 0)
        middle = row.get('boll_middle', 0)
        
        if pd.isna(upper) or pd.isna(lower):
            return 'unknown'
        
        if close >= upper:
            return 'above_upper'
        elif close <= lower:
            return 'below_lower'
        elif close > middle:
            return 'upper_half'
        else:
            return 'lower_half'


# 创建全局分析器实例
technical_analyzer = TechnicalAnalyzer()
