# -*- coding: utf-8 -*-
"""
Stock Analysis System - Technical Indicators
技术指标计算模块
"""

from typing import Optional, List, Dict, Any, Union
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """技术指标计算类"""
    
    # ==================== 移动平均线 ====================
    
    @staticmethod
    def SMA(series: pd.Series, period: int = 20) -> pd.Series:
        """
        简单移动平均线
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            SMA序列
        """
        return series.rolling(window=period).mean()
    
    @staticmethod
    def EMA(series: pd.Series, period: int = 20, adjust: bool = True) -> pd.Series:
        """
        指数移动平均线
        
        Args:
            series: 价格序列
            period: 周期
            adjust: 是否调整权重
            
        Returns:
            EMA序列
        """
        return series.ewm(span=period, adjust=adjust).mean()
    
    @staticmethod
    def WMA(series: pd.Series, period: int = 20) -> pd.Series:
        """
        加权移动平均线
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            WMA序列
        """
        weights = np.arange(1, period + 1)
        return series.rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
    
    @staticmethod
    def add_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60], column: str = 'close') -> pd.DataFrame:
        """
        添加多个均线
        
        Args:
            df: 数据DataFrame
            periods: 均线周期列表
            column: 价格列名
            
        Returns:
            添加均线的DataFrame
        """
        df = df.copy()
        for period in periods:
            df[f'ma{period}'] = TechnicalIndicators.SMA(df[column], period)
        return df
    
    # ==================== MACD指标 ====================
    
    @staticmethod
    def MACD(
        series: pd.Series, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> pd.DataFrame:
        """
        MACD指标
        
        Args:
            series: 价格序列
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            包含MACD, Signal, Histogram的DataFrame
        """
        ema_fast = TechnicalIndicators.EMA(series, fast)
        ema_slow = TechnicalIndicators.EMA(series, slow)
        
        macd = ema_fast - ema_slow
        signal_line = TechnicalIndicators.EMA(macd, signal)
        histogram = macd - signal_line
        
        return pd.DataFrame({
            'macd': macd,
            'macd_signal': signal_line,
            'macd_hist': histogram
        })
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """添加MACD指标"""
        df = df.copy()
        macd_df = TechnicalIndicators.MACD(df['close'], fast, slow, signal)
        return pd.concat([df, macd_df], axis=1)
    
    # ==================== RSI指标 ====================
    
    @staticmethod
    def RSI(series: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指标RSI
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            RSI序列
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, periods: List[int] = [6, 12, 14]) -> pd.DataFrame:
        """添加RSI指标"""
        df = df.copy()
        for period in periods:
            df[f'rsi_{period}'] = TechnicalIndicators.RSI(df['close'], period)
        return df
    
    # ==================== 布林带 ====================
    
    @staticmethod
    def BOLL(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """
        布林带指标
        
        Args:
            series: 价格序列
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            包含上轨、中轨、下轨的DataFrame
        """
        middle = TechnicalIndicators.SMA(series, period)
        std = series.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return pd.DataFrame({
            'boll_upper': upper,
            'boll_middle': middle,
            'boll_lower': lower
        })
    
    @staticmethod
    def add_boll(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """添加布林带指标"""
        df = df.copy()
        boll_df = TechnicalIndicators.BOLL(df['close'], period, std_dev)
        return pd.concat([df, boll_df], axis=1)
    
    # ==================== KDJ指标 ====================
    
    @staticmethod
    def KDJ(
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series,
        k_period: int = 9,
        d_period: int = 3,
        j_period: int = 3
    ) -> pd.DataFrame:
        """
        KDJ随机指标
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            k_period: K值周期
            d_period: D值周期
            j_period: J值周期
            
        Returns:
            包含K, D, J的DataFrame
        """
        # 计算RSV
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)
        
        # 计算K值
        k = rsv.ewm(alpha=1/d_period, adjust=False).mean()
        
        # 计算D值
        d = k.ewm(alpha=1/j_period, adjust=False).mean()
        
        # 计算J值
        j = 3 * k - 2 * d
        
        return pd.DataFrame({
            'kdj_k': k,
            'kdj_d': d,
            'kdj_j': j
        })
    
    @staticmethod
    def add_kdj(df: pd.DataFrame, k_period: int = 9, d_period: int = 3, j_period: int = 3) -> pd.DataFrame:
        """添加KDJ指标"""
        df = df.copy()
        kdj_df = TechnicalIndicators.KDJ(df['high'], df['low'], df['close'], k_period, d_period, j_period)
        return pd.concat([df, kdj_df], axis=1)
    
    # ==================== ATR指标 ====================
    
    @staticmethod
    def ATR(
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅ATR
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期
            
        Returns:
            ATR序列
        """
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """添加ATR指标"""
        df = df.copy()
        df['atr'] = TechnicalIndicators.ATR(df['high'], df['low'], df['close'], period)
        return df
    
    # ==================== OBV指标 ====================
    
    @staticmethod
    def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标OBV
        
        Args:
            close: 收盘价序列
            volume: 成交量序列
            
        Returns:
            OBV序列
        """
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        
        return (volume * direction).cumsum()
    
    @staticmethod
    def add_obv(df: pd.DataFrame) -> pd.DataFrame:
        """添加OBV指标"""
        df = df.copy()
        df['obv'] = TechnicalIndicators.OBV(df['close'], df['volume'])
        return df
    
    # ==================== VWAP指标 ====================
    
    @staticmethod
    def VWAP(
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        成交量加权平均价格VWAP
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            volume: 成交量序列
            
        Returns:
            VWAP序列
        """
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
        """添加VWAP指标"""
        df = df.copy()
        df['vwap'] = TechnicalIndicators.VWAP(df['high'], df['low'], df['close'], df['volume'])
        return df
    
    # ==================== CCI指标 ====================
    
    @staticmethod
    def CCI(
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        顺势指标CCI
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期
            
        Returns:
            CCI序列
        """
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        
        return (typical_price - sma) / (0.015 * mad)
    
    @staticmethod
    def add_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """添加CCI指标"""
        df = df.copy()
        df['cci'] = TechnicalIndicators.CCI(df['high'], df['low'], df['close'], period)
        return df
    
    # ==================== 威廉指标 ====================
    
    @staticmethod
    def WR(
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        威廉指标WR
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期
            
        Returns:
            WR序列
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        return -100 * (highest_high - close) / (highest_high - lowest_low)
    
    @staticmethod
    def add_wr(df: pd.DataFrame, periods: List[int] = [10, 20]) -> pd.DataFrame:
        """添加WR指标"""
        df = df.copy()
        for period in periods:
            df[f'wr_{period}'] = TechnicalIndicators.WR(df['high'], df['low'], df['close'], period)
        return df
    
    # ==================== 综合添加指标 ====================
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        添加所有常用技术指标
        
        Args:
            df: OHLCV数据DataFrame
            
        Returns:
            添加所有指标的DataFrame
        """
        df = df.copy()
        
        # 均线
        df = TechnicalIndicators.add_ma(df, [5, 10, 20, 60])
        
        # MACD
        df = TechnicalIndicators.add_macd(df)
        
        # RSI
        df = TechnicalIndicators.add_rsi(df, [6, 12, 14])
        
        # 布林带
        df = TechnicalIndicators.add_boll(df)
        
        # KDJ
        df = TechnicalIndicators.add_kdj(df)
        
        # ATR
        df = TechnicalIndicators.add_atr(df)
        
        # OBV
        if 'volume' in df.columns:
            df = TechnicalIndicators.add_obv(df)
            df = TechnicalIndicators.add_vwap(df)
        
        # CCI
        df = TechnicalIndicators.add_cci(df)
        
        # WR
        df = TechnicalIndicators.add_wr(df)
        
        logger.info("所有技术指标添加完成")
        return df


# 便捷别名
indicators = TechnicalIndicators
