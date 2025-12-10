# -*- coding: utf-8 -*-
"""
Stock Analysis System - Pattern Recognition
K线形态识别模块
"""

from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PatternRecognition:
    """K线形态识别类"""
    
    # ==================== 单根K线形态 ====================
    
    @staticmethod
    def is_doji(open_: float, high: float, low: float, close: float, threshold: float = 0.1) -> bool:
        """
        判断是否为十字星
        
        Args:
            open_: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
            threshold: 实体占比阈值
            
        Returns:
            是否为十字星
        """
        body = abs(close - open_)
        range_ = high - low
        
        if range_ == 0:
            return False
        
        return body / range_ <= threshold
    
    @staticmethod
    def is_hammer(open_: float, high: float, low: float, close: float) -> bool:
        """
        判断是否为锤子线
        
        Args:
            open_: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
            
        Returns:
            是否为锤子线
        """
        body = abs(close - open_)
        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low
        
        if body == 0:
            return False
        
        # 下影线至少是实体的2倍，上影线很短
        return lower_shadow >= 2 * body and upper_shadow <= 0.3 * body
    
    @staticmethod
    def is_hanging_man(open_: float, high: float, low: float, close: float) -> bool:
        """
        判断是否为上吊线（与锤子线形态相同，但出现在上涨趋势顶部）
        """
        return PatternRecognition.is_hammer(open_, high, low, close)
    
    @staticmethod
    def is_inverted_hammer(open_: float, high: float, low: float, close: float) -> bool:
        """
        判断是否为倒锤子线
        """
        body = abs(close - open_)
        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low
        
        if body == 0:
            return False
        
        # 上影线至少是实体的2倍，下影线很短
        return upper_shadow >= 2 * body and lower_shadow <= 0.3 * body
    
    @staticmethod
    def is_marubozu(open_: float, high: float, low: float, close: float, threshold: float = 0.05) -> Tuple[bool, str]:
        """
        判断是否为光头光脚线
        
        Returns:
            (是否为光头光脚, 方向 'bullish'/'bearish')
        """
        body = abs(close - open_)
        range_ = high - low
        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low
        
        if range_ == 0:
            return False, ""
        
        # 影线占实体的比例很小
        if upper_shadow <= threshold * body and lower_shadow <= threshold * body:
            direction = 'bullish' if close > open_ else 'bearish'
            return True, direction
        
        return False, ""
    
    # ==================== 双K线形态 ====================
    
    @staticmethod
    def is_engulfing(df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        判断是否为吞没形态
        
        Args:
            df: OHLC数据
            idx: 当前索引
            
        Returns:
            (是否为吞没形态, 方向 'bullish'/'bearish')
        """
        if idx < 1:
            return False, ""
        
        prev = df.iloc[idx - 1]
        curr = df.iloc[idx]
        
        # 看涨吞没：前一天阴线，当天阳线包住前一天
        if prev['close'] < prev['open'] and curr['close'] > curr['open']:
            if curr['open'] <= prev['close'] and curr['close'] >= prev['open']:
                return True, 'bullish'
        
        # 看跌吞没：前一天阳线，当天阴线包住前一天
        if prev['close'] > prev['open'] and curr['close'] < curr['open']:
            if curr['open'] >= prev['close'] and curr['close'] <= prev['open']:
                return True, 'bearish'
        
        return False, ""
    
    @staticmethod
    def is_harami(df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        判断是否为孕线形态
        
        Returns:
            (是否为孕线, 方向 'bullish'/'bearish')
        """
        if idx < 1:
            return False, ""
        
        prev = df.iloc[idx - 1]
        curr = df.iloc[idx]
        
        # 看涨孕线：前一天大阴线，当天小阳线被包含
        if prev['close'] < prev['open'] and curr['close'] > curr['open']:
            if curr['open'] > prev['close'] and curr['close'] < prev['open']:
                return True, 'bullish'
        
        # 看跌孕线：前一天大阳线，当天小阴线被包含
        if prev['close'] > prev['open'] and curr['close'] < curr['open']:
            if curr['open'] < prev['close'] and curr['close'] > prev['open']:
                return True, 'bearish'
        
        return False, ""
    
    @staticmethod
    def is_piercing_line(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为刺透形态（看涨反转）
        """
        if idx < 1:
            return False
        
        prev = df.iloc[idx - 1]
        curr = df.iloc[idx]
        
        # 前一天阴线，当天阳线开盘低于前一天最低，收盘超过前一天实体中点
        if prev['close'] < prev['open'] and curr['close'] > curr['open']:
            mid_point = (prev['open'] + prev['close']) / 2
            if curr['open'] < prev['low'] and curr['close'] > mid_point:
                return True
        
        return False
    
    @staticmethod
    def is_dark_cloud_cover(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为乌云盖顶（看跌反转）
        """
        if idx < 1:
            return False
        
        prev = df.iloc[idx - 1]
        curr = df.iloc[idx]
        
        # 前一天阳线，当天阴线开盘高于前一天最高，收盘低于前一天实体中点
        if prev['close'] > prev['open'] and curr['close'] < curr['open']:
            mid_point = (prev['open'] + prev['close']) / 2
            if curr['open'] > prev['high'] and curr['close'] < mid_point:
                return True
        
        return False
    
    # ==================== 三K线形态 ====================
    
    @staticmethod
    def is_morning_star(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为早晨之星（看涨反转）
        """
        if idx < 2:
            return False
        
        first = df.iloc[idx - 2]
        second = df.iloc[idx - 1]
        third = df.iloc[idx]
        
        # 第一天大阴线，第二天小实体（十字星更佳），第三天大阳线
        first_bearish = first['close'] < first['open']
        second_small = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bullish = third['close'] > third['open']
        
        # 第三天收盘超过第一天实体中点
        mid_point = (first['open'] + first['close']) / 2
        
        if first_bearish and second_small and third_bullish and third['close'] > mid_point:
            # 第二天跳空低开
            if second['high'] < first['close']:
                return True
        
        return False
    
    @staticmethod
    def is_evening_star(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为黄昏之星（看跌反转）
        """
        if idx < 2:
            return False
        
        first = df.iloc[idx - 2]
        second = df.iloc[idx - 1]
        third = df.iloc[idx]
        
        # 第一天大阳线，第二天小实体，第三天大阴线
        first_bullish = first['close'] > first['open']
        second_small = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bearish = third['close'] < third['open']
        
        # 第三天收盘低于第一天实体中点
        mid_point = (first['open'] + first['close']) / 2
        
        if first_bullish and second_small and third_bearish and third['close'] < mid_point:
            # 第二天跳空高开
            if second['low'] > first['close']:
                return True
        
        return False
    
    @staticmethod
    def is_three_white_soldiers(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为三白兵（强势看涨）
        """
        if idx < 2:
            return False
        
        candles = [df.iloc[idx - 2], df.iloc[idx - 1], df.iloc[idx]]
        
        for i, c in enumerate(candles):
            # 都是阳线
            if c['close'] <= c['open']:
                return False
            # 每根收盘都比前一根高
            if i > 0 and c['close'] <= candles[i-1]['close']:
                return False
            # 开盘在前一根实体内
            if i > 0 and (c['open'] < candles[i-1]['open'] or c['open'] > candles[i-1]['close']):
                return False
        
        return True
    
    @staticmethod
    def is_three_black_crows(df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为三只乌鸦（强势看跌）
        """
        if idx < 2:
            return False
        
        candles = [df.iloc[idx - 2], df.iloc[idx - 1], df.iloc[idx]]
        
        for i, c in enumerate(candles):
            # 都是阴线
            if c['close'] >= c['open']:
                return False
            # 每根收盘都比前一根低
            if i > 0 and c['close'] >= candles[i-1]['close']:
                return False
            # 开盘在前一根实体内
            if i > 0 and (c['open'] > candles[i-1]['open'] or c['open'] < candles[i-1]['close']):
                return False
        
        return True
    
    # ==================== 形态扫描 ====================
    
    @staticmethod
    def scan_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """
        扫描所有K线形态
        
        Args:
            df: OHLC数据
            
        Returns:
            添加形态标记的DataFrame
        """
        df = df.copy()
        
        # 初始化形态列
        df['pattern'] = None
        df['pattern_direction'] = None
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            patterns = []
            direction = None
            
            # 单根K线形态
            if PatternRecognition.is_doji(row['open'], row['high'], row['low'], row['close']):
                patterns.append('doji')
            
            if PatternRecognition.is_hammer(row['open'], row['high'], row['low'], row['close']):
                patterns.append('hammer')
                direction = 'bullish'
            
            if PatternRecognition.is_inverted_hammer(row['open'], row['high'], row['low'], row['close']):
                patterns.append('inverted_hammer')
            
            is_marubozu, marubozu_dir = PatternRecognition.is_marubozu(
                row['open'], row['high'], row['low'], row['close']
            )
            if is_marubozu:
                patterns.append('marubozu')
                direction = marubozu_dir
            
            # 双K线形态
            is_engulfing, engulf_dir = PatternRecognition.is_engulfing(df, idx)
            if is_engulfing:
                patterns.append('engulfing')
                direction = engulf_dir
            
            is_harami, harami_dir = PatternRecognition.is_harami(df, idx)
            if is_harami:
                patterns.append('harami')
                direction = harami_dir
            
            if PatternRecognition.is_piercing_line(df, idx):
                patterns.append('piercing_line')
                direction = 'bullish'
            
            if PatternRecognition.is_dark_cloud_cover(df, idx):
                patterns.append('dark_cloud')
                direction = 'bearish'
            
            # 三K线形态
            if PatternRecognition.is_morning_star(df, idx):
                patterns.append('morning_star')
                direction = 'bullish'
            
            if PatternRecognition.is_evening_star(df, idx):
                patterns.append('evening_star')
                direction = 'bearish'
            
            if PatternRecognition.is_three_white_soldiers(df, idx):
                patterns.append('three_white_soldiers')
                direction = 'bullish'
            
            if PatternRecognition.is_three_black_crows(df, idx):
                patterns.append('three_black_crows')
                direction = 'bearish'
            
            if patterns:
                df.loc[df.index[idx], 'pattern'] = ','.join(patterns)
                df.loc[df.index[idx], 'pattern_direction'] = direction
        
        logger.info("K线形态扫描完成")
        return df


# 便捷别名
patterns = PatternRecognition
