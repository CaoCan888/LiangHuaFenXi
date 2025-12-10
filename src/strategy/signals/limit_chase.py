# -*- coding: utf-8 -*-
"""
打板策略模块 - 短线涨停板追击
"""

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class LimitChaseStrategy:
    """
    打板策略 - 涨停板追击
    
    核心逻辑:
    1. 首板策略: 寻找即将涨停或刚涨停的股票
    2. 二板策略: 寻找连续涨停的股票
    3. 放量突破策略: 涨幅+量能配合
    """
    
    # A股涨跌停限制
    LIMIT_UP_PCT = 0.10  # 普通股涨停10%
    LIMIT_UP_PCT_ST = 0.05  # ST股涨停5%
    LIMIT_UP_PCT_NEW = 0.20  # 科创板/创业板涨停20%
    
    def __init__(self):
        self.params = {
            'volume_ratio_threshold': 2.0,  # 量比阈值
            'pct_change_threshold': 0.05,   # 涨幅阈值5%
            'near_limit_threshold': 0.02,   # 距离涨停2%以内
            'turnover_threshold': 0.03,     # 换手率阈值3%
            'min_amount': 50000000,         # 最小成交额5000万
        }
    
    def calculate_limit_price(self, pre_close: float, stock_code: str) -> float:
        """计算涨停价"""
        # 判断涨停幅度
        if stock_code.startswith(('30', '68')):  # 创业板/科创板
            limit_pct = self.LIMIT_UP_PCT_NEW
        elif 'ST' in stock_code:  # ST股
            limit_pct = self.LIMIT_UP_PCT_ST
        else:  # 普通股
            limit_pct = self.LIMIT_UP_PCT
        
        return round(pre_close * (1 + limit_pct), 2)
    
    def detect_limit_up(self, df: pd.DataFrame, stock_code: str = '') -> pd.DataFrame:
        """
        检测涨停状态
        
        Args:
            df: 包含OHLCV的DataFrame
            stock_code: 股票代码，用于判断涨跌幅限制
            
        Returns:
            添加涨停标记的DataFrame
        """
        df = df.copy()
        
        # 根据股票代码确定涨跌幅限制
        if stock_code.startswith(('30', '68', '688')):  # 创业板/科创板
            limit_threshold = 0.195  # 20%涨停，留0.5%容错
            limit_pct = 0.20
        elif 'ST' in stock_code.upper():  # ST股
            limit_threshold = 0.045  # 5%涨停
            limit_pct = 0.05
        else:  # 普通A股
            limit_threshold = 0.095  # 10%涨停
            limit_pct = 0.10
        
        # 计算涨跌幅
        df['pct_change'] = df['close'].pct_change()
        
        # 计算涨停价
        df['pre_close'] = df['close'].shift(1)
        df['limit_up_price'] = (df['pre_close'] * (1 + limit_pct)).round(2)
        
        # 判断是否涨停 (使用动态阈值)
        df['is_limit_up'] = df['pct_change'] >= limit_threshold
        
        # 距离涨停价的幅度
        df['dist_to_limit'] = (df['limit_up_price'] - df['close']) / df['close']
        
        # 计算连板数
        df['limit_streak'] = 0
        streak = 0
        for i in range(len(df)):
            if df.iloc[i]['is_limit_up']:
                streak += 1
            else:
                streak = 0
            df.iloc[i, df.columns.get_loc('limit_streak')] = streak
        
        # 是否为首板（连板数=1）
        df['is_first_limit'] = df['limit_streak'] == 1
        
        # 是否为二板（连板数=2）
        df['is_second_limit'] = df['limit_streak'] == 2
        
        # 是否为三板及以上
        df['is_high_limit'] = df['limit_streak'] >= 3
        
        return df
    
    def calculate_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算量能特征
        
        Args:
            df: 包含volume的DataFrame
            
        Returns:
            添加量能特征的DataFrame
        """
        df = df.copy()
        
        # 量比（今日成交量 / 过去5日平均成交量）
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ratio'] = df['volume'] / df['vol_ma5']
        
        # 成交额变化
        if 'amount' in df.columns:
            df['amount_ma5'] = df['amount'].rolling(5).mean()
            df['amount_ratio'] = df['amount'] / df['amount_ma5']
        
        # 量能趋势（连续放量）
        df['vol_increase'] = (df['volume'] > df['volume'].shift(1)).astype(int)
        df['vol_increase_streak'] = df['vol_increase'].rolling(3).sum()
        
        return df
    
    def generate_signals(self, df: pd.DataFrame, stock_code: str = '') -> pd.DataFrame:
        """
        生成打板信号
        
        Args:
            df: OHLCV数据
            stock_code: 股票代码，用于判断涨跌幅限制
            
        Returns:
            添加信号的DataFrame
        """
        df = df.copy()
        
        # 检测涨停（传入股票代码用于动态阈值）
        df = self.detect_limit_up(df, stock_code)
        
        # 计算量能特征
        df = self.calculate_volume_features(df)
        
        # 初始化信号
        df['signal'] = 0
        df['signal_type'] = ''
        df['signal_score'] = 0.0
        
        for idx in range(5, len(df)):
            row = df.iloc[idx]
            score = 0.0
            signal_types = []
            
            # === 首板追击信号 ===
            if row.get('is_first_limit', False):
                score += 0.4
                signal_types.append('首板')
                
                # 放量首板加分
                if row.get('volume_ratio', 0) > 3:
                    score += 0.2
                    signal_types.append('放量')
            
            # === 二板接力信号 ===
            elif row.get('is_second_limit', False):
                score += 0.3
                signal_types.append('二板')
                
                # 缩量二板（惜售）更佳
                if row.get('volume_ratio', 0) < 0.8:
                    score += 0.15
                    signal_types.append('缩量')
            
            # === 涨停近端信号（距离涨停<2%）===
            elif 0 < row.get('dist_to_limit', 1) < self.params['near_limit_threshold']:
                # 涨幅超过5%
                if row.get('pct_change', 0) > self.params['pct_change_threshold']:
                    score += 0.25
                    signal_types.append('近涨停')
                    
                    # 量比配合
                    if row.get('volume_ratio', 0) > self.params['volume_ratio_threshold']:
                        score += 0.2
                        signal_types.append('量比达标')
            
            # === 放量突破信号 ===
            elif row.get('pct_change', 0) > 0.03:  # 涨幅>3%
                if row.get('volume_ratio', 0) > 2.5:  # 量比>2.5
                    if row.get('close', 0) > row.get('high', 0) * 0.98:  # 收在高位
                        score += 0.2
                        signal_types.append('放量突破')
            
            # === 连续放量加速 ===
            if row.get('vol_increase_streak', 0) >= 3:
                score += 0.1
                signal_types.append('连续放量')
            
            # 确定信号
            if score >= 0.3:
                df.loc[df.index[idx], 'signal'] = 1
                df.loc[df.index[idx], 'signal_type'] = '+'.join(signal_types)
                df.loc[df.index[idx], 'signal_score'] = min(score, 1.0)
        
        return df
    
    def find_candidates(self, df: pd.DataFrame) -> List[Dict]:
        """
        筛选打板候选股
        
        Returns:
            符合条件的候选股列表
        """
        df = self.generate_signals(df)
        
        # 筛选最新有信号的
        latest = df.iloc[-1]
        
        if latest.get('signal', 0) == 1:
            return [{
                'signal_type': latest.get('signal_type', ''),
                'signal_score': latest.get('signal_score', 0),
                'pct_change': latest.get('pct_change', 0),
                'volume_ratio': latest.get('volume_ratio', 0),
                'is_limit_up': latest.get('is_limit_up', False),
                'dist_to_limit': latest.get('dist_to_limit', 0)
            }]
        
        return []
    
    def get_stop_loss_price(self, buy_price: float, strategy_type: str = '首板') -> float:
        """
        计算止损价
        
        Args:
            buy_price: 买入价格
            strategy_type: 策略类型
            
        Returns:
            止损价格
        """
        # 打板策略止损较严格
        if strategy_type == '首板':
            return buy_price * 0.95  # 首板止损5%
        elif strategy_type == '二板':
            return buy_price * 0.93  # 二板止损7%
        else:
            return buy_price * 0.97  # 其他止损3%
    
    def get_take_profit_price(self, buy_price: float, strategy_type: str = '首板') -> float:
        """
        计算止盈价
        
        Args:
            buy_price: 买入价格
            strategy_type: 策略类型
            
        Returns:
            止盈价格
        """
        if strategy_type == '首板':
            return buy_price * 1.10  # 首板目标+10%（次日涨停）
        elif strategy_type == '二板':
            return buy_price * 1.15  # 二板目标+15%
        else:
            return buy_price * 1.05  # 其他目标+5%


class MomentumStrategy:
    """
    动量策略 - 短线强势股追踪
    """
    
    def __init__(self):
        self.params = {
            'momentum_period': 5,      # 动量周期
            'volume_surge': 2.0,       # 量能激增阈值
            'price_surge': 0.05,       # 价格激增阈值5%
            'rsi_oversold': 30,        # RSI超卖
            'rsi_overbought': 80,      # RSI超买
        }
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算动量指标"""
        df = df.copy()
        period = self.params['momentum_period']
        
        # 价格动量
        df['momentum'] = df['close'] / df['close'].shift(period) - 1
        
        # 动量加速度
        df['momentum_acc'] = df['momentum'] - df['momentum'].shift(1)
        
        # 动量排名分数 (0-100)
        df['momentum_rank'] = df['momentum'].rolling(20).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 50
        )
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成动量信号"""
        df = self.calculate_momentum(df)
        df['signal'] = 0
        
        for idx in range(10, len(df)):
            row = df.iloc[idx]
            
            # 强势动量信号
            if row.get('momentum', 0) > self.params['price_surge']:
                if row.get('momentum_acc', 0) > 0:  # 动量加速
                    if row.get('momentum_rank', 0) > 80:  # 排名靠前
                        df.loc[df.index[idx], 'signal'] = 1
        
        return df


class IntradayStrategy:
    """
    日内策略 - 分时图量价分析
    """
    
    def __init__(self):
        self.params = {
            'open_surge': 0.02,      # 高开幅度2%
            'volume_first_30min': 0.3,  # 前30分钟量能占比
        }
    
    def analyze_opening(self, df: pd.DataFrame) -> Dict:
        """
        分析开盘情况（需要分钟数据）
        
        Args:
            df: 分钟K线数据
            
        Returns:
            开盘分析结果
        """
        if df.empty or len(df) < 30:
            return {}
        
        # 假设数据按时间排序
        first_bar = df.iloc[0]
        first_30min = df.head(30)
        
        result = {
            'open_price': first_bar['open'],
            'gap_up': first_bar['open'] > first_bar.get('pre_close', first_bar['open']) * 1.02,
            'first_30min_volume': first_30min['volume'].sum(),
            'first_30min_high': first_30min['high'].max(),
            'first_30min_low': first_30min['low'].min(),
        }
        
        return result


# 创建全局策略实例
limit_chase_strategy = LimitChaseStrategy()
momentum_strategy = MomentumStrategy()
intraday_strategy = IntradayStrategy()
