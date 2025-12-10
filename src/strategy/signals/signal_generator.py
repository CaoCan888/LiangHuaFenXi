# -*- coding: utf-8 -*-
"""
信号生成器模块
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger
from src.strategy.signals.limit_chase import limit_chase_strategy, momentum_strategy, intraday_strategy
from src.strategy.signals.chan_strategy import chan_signal_generator, chan_analyzer
from src.strategy.signals.comprehensive_strategy import comprehensive_signal_generator, technical_scorer

logger = get_logger(__name__)


class SignalGenerator:
    """交易信号生成器"""
    
    def __init__(self):
        self.strategies = {
            'ma_cross': self.ma_cross_signal,
            'macd': self.macd_signal,
            'rsi': self.rsi_signal,
            'bollinger': self.bollinger_signal,
            'combined': self.combined_signal,
            'limit_chase': self.limit_chase_signal,  # 打板策略
            'momentum': self.momentum_signal,  # 动量策略
            'czsc': self.czsc_signal,  # 缠论策略
            'comprehensive': self.comprehensive_signal,  # 综合策略
            'intraday': self.intraday_signal,  # 日内策略
        }
    
    def generate(self, df: pd.DataFrame, strategy: str = 'combined') -> pd.DataFrame:
        """生成交易信号"""
        if strategy not in self.strategies:
            raise ValueError(f"未知策略: {strategy}")
        return self.strategies[strategy](df)
    
    def limit_chase_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """打板信号 - 短线涨停追击"""
        return limit_chase_strategy.generate_signals(df)
    
    def momentum_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """动量信号 - 短线强势股追踪"""
        return momentum_strategy.generate_signals(df)
    
    def czsc_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """缠论信号 - 基于分型笔中枢"""
        return chan_signal_generator.generate_signals(df)
    
    def comprehensive_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """综合策略信号 - CZSC经典形态+技术评分"""
        return comprehensive_signal_generator.generate_signals(df)
    
    def intraday_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """日内策略 - 分时量价分析"""
        result = intraday_strategy.analyze_opening(df)
        df = df.copy()
        df['signal'] = 0
        df['intraday_type'] = result.get('opening_type', '')
        # 根据开盘分析生成信号
        if result.get('is_gap_up', False) and result.get('volume_surge', False):
            df.iloc[-1, df.columns.get_loc('signal')] = 1  # 高开放量买入
        elif result.get('is_gap_down', False):
            df.iloc[-1, df.columns.get_loc('signal')] = -1  # 低开卖出
        return df
    
    def ma_cross_signal(self, df: pd.DataFrame, short: int = 5, long: int = 20) -> pd.DataFrame:
        """均线交叉信号"""
        df = df.copy()
        df['signal'] = 0
        
        ma_short = f'ma{short}' if f'ma{short}' in df.columns else None
        ma_long = f'ma{long}' if f'ma{long}' in df.columns else None
        
        if ma_short and ma_long:
            for i in range(1, len(df)):
                if df[ma_short].iloc[i-1] < df[ma_long].iloc[i-1] and df[ma_short].iloc[i] > df[ma_long].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 1  # 买入
                elif df[ma_short].iloc[i-1] > df[ma_long].iloc[i-1] and df[ma_short].iloc[i] < df[ma_long].iloc[i]:
                    df.loc[df.index[i], 'signal'] = -1  # 卖出
        return df
    
    def macd_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD信号"""
        df = df.copy()
        df['signal'] = 0
        
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            for i in range(1, len(df)):
                prev_macd = df['macd'].iloc[i-1]
                prev_sig = df['macd_signal'].iloc[i-1]
                curr_macd = df['macd'].iloc[i]
                curr_sig = df['macd_signal'].iloc[i]
                
                if pd.notna(prev_macd) and pd.notna(curr_macd):
                    if prev_macd < prev_sig and curr_macd > curr_sig:
                        df.loc[df.index[i], 'signal'] = 1
                    elif prev_macd > prev_sig and curr_macd < curr_sig:
                        df.loc[df.index[i], 'signal'] = -1
        return df
    
    def rsi_signal(self, df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> pd.DataFrame:
        """RSI信号"""
        df = df.copy()
        df['signal'] = 0
        
        if 'rsi_14' in df.columns:
            for i in range(1, len(df)):
                rsi = df['rsi_14'].iloc[i]
                prev_rsi = df['rsi_14'].iloc[i-1]
                
                if pd.notna(rsi):
                    if prev_rsi < oversold and rsi > oversold:
                        df.loc[df.index[i], 'signal'] = 1
                    elif prev_rsi > overbought and rsi < overbought:
                        df.loc[df.index[i], 'signal'] = -1
        return df
    
    def bollinger_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """布林带信号"""
        df = df.copy()
        df['signal'] = 0
        
        if all(c in df.columns for c in ['boll_lower', 'boll_upper', 'close']):
            for i in range(1, len(df)):
                if df['close'].iloc[i-1] > df['boll_lower'].iloc[i-1] and df['close'].iloc[i] < df['boll_lower'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 1
                elif df['close'].iloc[i-1] < df['boll_upper'].iloc[i-1] and df['close'].iloc[i] > df['boll_upper'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = -1
        return df
    
    def combined_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """综合信号"""
        df = df.copy()
        signals = pd.DataFrame(index=df.index)
        
        signals['ma'] = self.ma_cross_signal(df.copy())['signal']
        signals['macd'] = self.macd_signal(df.copy())['signal']
        signals['rsi'] = self.rsi_signal(df.copy())['signal']
        
        df['signal'] = signals.sum(axis=1).apply(lambda x: 1 if x >= 2 else (-1 if x <= -2 else 0))
        return df


signal_generator = SignalGenerator()
