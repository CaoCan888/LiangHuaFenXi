# -*- coding: utf-8 -*-
"""
综合策略模块 - 整合CZSC经典策略和Stock-Scanner财务分析

包含:
1. CZSC K线形态策略 (双飞涨停、R-Breaker、Dual Thrust等)
2. 财务指标评分系统
3. 技术面综合评分
"""

import warnings
warnings.filterwarnings('ignore')

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==================== CZSC 经典K线策略 ====================

class CZSCBarSignals:
    """CZSC K线形态信号"""
    
    @staticmethod
    def r_breaker(df: pd.DataFrame) -> pd.DataFrame:
        """
        R-Breaker 策略
        
        六个价位:
        - 突破买入价 = 昨高 + 2*(昨中 - 昨低)
        - 观察卖出价 = 昨中 + 昨高 - 昨低
        - 反转卖出价 = 2*昨中 - 昨低
        - 反转买入价 = 2*昨中 - 昨高  
        - 观察买入价 = 昨中 - (昨高 - 昨低)
        - 突破卖出价 = 昨低 - 2*(昨高 - 昨中)
        """
        df = df.copy()
        df['r_signal'] = 0
        df['r_type'] = ''
        
        for i in range(1, len(df)):
            H = df.iloc[i-1]['high']
            C = df.iloc[i-1]['close']
            L = df.iloc[i-1]['low']
            P = (H + C + L) / 3  # 昨中
            
            break_buy = H + 2 * P - 2 * L
            see_sell = P + H - L
            verse_sell = 2 * P - L
            verse_buy = 2 * P - H
            see_buy = P - (H - L)
            break_sell = L - 2 * (H - P)
            
            curr = df.iloc[i]
            if curr['close'] > break_buy:
                df.iloc[i, df.columns.get_loc('r_signal')] = 1
                df.iloc[i, df.columns.get_loc('r_type')] = '趋势做多'
            elif curr['close'] < break_sell:
                df.iloc[i, df.columns.get_loc('r_signal')] = -1
                df.iloc[i, df.columns.get_loc('r_type')] = '趋势做空'
            elif curr['high'] > see_sell and curr['close'] < verse_sell:
                df.iloc[i, df.columns.get_loc('r_signal')] = -1
                df.iloc[i, df.columns.get_loc('r_type')] = '反转做空'
            elif curr['low'] < see_buy and curr['close'] > verse_buy:
                df.iloc[i, df.columns.get_loc('r_signal')] = 1
                df.iloc[i, df.columns.get_loc('r_type')] = '反转做多'
        
        return df
    
    @staticmethod
    def dual_thrust(df: pd.DataFrame, n: int = 5, k1: float = 0.5, k2: float = 0.5) -> pd.DataFrame:
        """
        Dual Thrust 通道突破策略
        
        上轨 = 开盘价 + Range * K1
        下轨 = 开盘价 - Range * K2
        Range = max(HH-LC, HC-LL)
        """
        df = df.copy()
        df['dt_signal'] = 0
        
        for i in range(n, len(df)):
            bars = df.iloc[i-n:i]
            HH = bars['high'].max()
            HC = bars['close'].max()
            LC = bars['close'].min()
            LL = bars['low'].min()
            Range = max(HH - LC, HC - LL)
            
            curr = df.iloc[i]
            buy_line = curr['open'] + Range * k1
            sell_line = curr['open'] - Range * k2
            
            if curr['close'] > buy_line:
                df.iloc[i, df.columns.get_loc('dt_signal')] = 1
            elif curr['close'] < sell_line:
                df.iloc[i, df.columns.get_loc('dt_signal')] = -1
        
        return df
    
    @staticmethod
    def shuang_fei_zt(df: pd.DataFrame) -> pd.DataFrame:
        """
        双飞涨停形态
        
        条件:
        1. 今天涨停
        2. 昨天收阴，跌幅>5%
        3. 前天涨停
        """
        df = df.copy()
        df['shuangfei'] = False
        
        if len(df) < 4:
            return df
        
        df['pct_change'] = df['close'].pct_change()
        
        for i in range(3, len(df)):
            b4 = df.iloc[i-3]
            b3 = df.iloc[i-2]
            b2 = df.iloc[i-1]
            b1 = df.iloc[i]
            
            # 前天涨停 (涨幅>7%且几乎无上影线)
            first_zt = (b3['close'] / b4['close'] - 1) > 0.07 and b3['close'] == b3['high']
            
            # 昨天收阴，跌幅>5%
            bar2_down = b2['close'] < b2['open'] and (b2['close'] / b3['close'] - 1) < -0.05
            
            # 今天涨停
            last_zt = (b1['close'] / b2['close'] - 1) > 0.07
            
            # 今天收盘价高于昨天最高价
            close_above = b1['close'] > b2['high']
            
            if first_zt and bar2_down and last_zt and close_above:
                df.iloc[i, df.columns.get_loc('shuangfei')] = True
        
        return df
    
    @staticmethod
    def limit_down_reverse(df: pd.DataFrame) -> pd.DataFrame:
        """
        跌停后长阳反转信号
        
        条件:
        1. 前天收盘接近跌停 (跌幅>9%)
        2. 昨天继续跌停
        3. 今天出现长实体阳线且无下影线
        """
        df = df.copy()
        df['ld_reverse'] = False
        
        if len(df) < 3:
            return df
        
        for i in range(2, len(df)):
            b1 = df.iloc[i-2]
            b2 = df.iloc[i-1]
            b3 = df.iloc[i]
            
            # 昨天跌停
            b2_limit_down = b2['low'] == b2['close'] and (b2['close'] / b1['close'] - 1) < -0.09
            
            # 今天阳线反包
            b3_yang = b3['close'] > b3['open']
            b3_solid = b3['close'] - b3['open']
            b3_lower = b3['open'] - b3['low']
            b3_no_lower = b3_lower < b3_solid * 0.1  # 无下影线
            
            if b2_limit_down and b3_yang and b3_no_lower and b3['close'] > b2['high']:
                df.iloc[i, df.columns.get_loc('ld_reverse')] = True
        
        return df
    
    @staticmethod
    def tnr_trend(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        TNR趋势噪音指标
        
        TNR = |首尾close差| / sum(|相邻close差|)
        TNR越大趋势越明显，越小震荡越强
        """
        df = df.copy()
        df['tnr'] = 0.0
        
        for i in range(period, len(df)):
            bars = df.iloc[i-period:i+1]
            sum_abs = sum(abs(bars['close'].iloc[j] - bars['close'].iloc[j-1]) for j in range(1, len(bars)))
            if sum_abs > 0:
                tnr = abs(bars['close'].iloc[-1] - bars['close'].iloc[0]) / sum_abs
                df.iloc[i, df.columns.get_loc('tnr')] = tnr
        
        return df


# ==================== 技术面评分系统 ====================

class TechnicalScorer:
    """技术面评分系统 (0-100)"""
    
    def __init__(self, custom_weights: dict = None):
        """
        初始化技术评分系统
        
        Args:
            custom_weights: 自定义权重字典，不提供则从配置文件读取
        """
        # 默认权重
        default_weights = {
            'ma_score': 0.2,      # 均线评分
            'macd_score': 0.15,   # MACD评分
            'rsi_score': 0.15,    # RSI评分
            'volume_score': 0.15, # 量能评分
            'trend_score': 0.2,   # 趋势评分
            'pattern_score': 0.15 # 形态评分
        }
        
        # 尝试从配置文件加载权重
        try:
            from config.settings import settings
            config_weights = getattr(settings, 'TECHNICAL_SCORE_WEIGHTS', None)
            if config_weights:
                default_weights.update(config_weights)
        except:
            pass
        
        # 使用自定义权重覆盖
        if custom_weights:
            default_weights.update(custom_weights)
        
        self.weights = default_weights
    
    def calculate_ma_score(self, df: pd.DataFrame) -> float:
        """均线系统评分"""
        if len(df) < 60:
            return 50.0
        
        score = 50.0
        latest = df.iloc[-1]
        close = latest['close']
        
        # 计算均线
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        
        # 多头排列加分
        if ma5 > ma10 > ma20 > ma60:
            score += 30
        elif ma5 > ma10 > ma20:
            score += 20
        elif ma5 > ma10:
            score += 10
        
        # 价格在均线上方加分
        if close > ma5:
            score += 5
        if close > ma20:
            score += 5
        if close > ma60:
            score += 10
        
        return min(100, max(0, score))
    
    def calculate_macd_score(self, df: pd.DataFrame) -> float:
        """MACD评分"""
        if len(df) < 35:
            return 50.0
        
        score = 50.0
        
        # 计算MACD
        exp12 = df['close'].ewm(span=12).mean()
        exp26 = df['close'].ewm(span=26).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9).mean()
        macd = (dif - dea) * 2
        
        latest_dif = dif.iloc[-1]
        latest_dea = dea.iloc[-1]
        latest_macd = macd.iloc[-1]
        prev_macd = macd.iloc[-2]
        
        # DIF在DEA上方
        if latest_dif > latest_dea:
            score += 15
        
        # 金叉
        if dif.iloc[-2] < dea.iloc[-2] and latest_dif > latest_dea:
            score += 20
        
        # MACD柱放大
        if latest_macd > prev_macd > 0:
            score += 10
        
        # DIF和DEA都在0轴上方
        if latest_dif > 0 and latest_dea > 0:
            score += 10
        
        return min(100, max(0, score))
    
    def calculate_rsi_score(self, df: pd.DataFrame, period: int = 14) -> float:
        """RSI评分"""
        if len(df) < period + 1:
            return 50.0
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        latest_rsi = rsi.iloc[-1]
        
        if pd.isna(latest_rsi):
            return 50.0
        
        # RSI评分逻辑
        if latest_rsi < 30:
            score = 80  # 超卖，买入机会
        elif latest_rsi < 50:
            score = 60
        elif latest_rsi < 70:
            score = 50
        elif latest_rsi < 80:
            score = 40
        else:
            score = 20  # 超买，风险较高
        
        return score
    
    def calculate_volume_score(self, df: pd.DataFrame) -> float:
        """量能评分"""
        if len(df) < 20:
            return 50.0
        
        score = 50.0
        
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        vol_ma20 = df['volume'].rolling(20).mean().iloc[-1]
        latest_vol = df['volume'].iloc[-1]
        
        # 量比
        if vol_ma20 > 0:
            volume_ratio = latest_vol / vol_ma20
            
            if volume_ratio > 2:
                score += 20  # 放量
            elif volume_ratio > 1.5:
                score += 10
            elif volume_ratio < 0.5:
                score -= 10  # 缩量
        
        # 价涨量增
        price_up = df['close'].iloc[-1] > df['close'].iloc[-2]
        vol_up = latest_vol > df['volume'].iloc[-2]
        
        if price_up and vol_up:
            score += 15
        elif not price_up and not vol_up:
            score += 5  # 价跌量缩也是好的
        
        return min(100, max(0, score))
    
    def calculate_trend_score(self, df: pd.DataFrame) -> float:
        """趋势评分"""
        if len(df) < 20:
            return 50.0
        
        score = 50.0
        
        # 20日涨幅
        pct_20 = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100
        
        if pct_20 > 20:
            score += 30
        elif pct_20 > 10:
            score += 20
        elif pct_20 > 5:
            score += 10
        elif pct_20 < -10:
            score -= 20
        elif pct_20 < -5:
            score -= 10
        
        # 新高
        high_20 = df['high'].rolling(20).max().iloc[-1]
        if df['close'].iloc[-1] >= high_20 * 0.98:
            score += 15
        
        return min(100, max(0, score))
    
    def calculate_pattern_score(self, df: pd.DataFrame) -> float:
        """形态评分"""
        score = 50.0
        
        if len(df) < 5:
            return score
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 阳线加分
        if latest['close'] > latest['open']:
            score += 10
        
        # 突破前高
        if latest['close'] > prev['high']:
            score += 10
        
        # K线实体大
        body = abs(latest['close'] - latest['open'])
        total = latest['high'] - latest['low']
        if total > 0 and body / total > 0.7:
            score += 10
        
        # 收在高位
        if total > 0:
            position = (latest['close'] - latest['low']) / total
            if position > 0.8:
                score += 10
        
        return min(100, max(0, score))
    
    def calculate_total_score(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算综合评分"""
        scores = {
            'ma_score': self.calculate_ma_score(df),
            'macd_score': self.calculate_macd_score(df),
            'rsi_score': self.calculate_rsi_score(df),
            'volume_score': self.calculate_volume_score(df),
            'trend_score': self.calculate_trend_score(df),
            'pattern_score': self.calculate_pattern_score(df),
        }
        
        total = sum(scores[k] * self.weights[k] for k in scores)
        scores['total_score'] = round(total, 2)
        
        # 评级
        if total >= 80:
            scores['rating'] = '强烈推荐'
        elif total >= 70:
            scores['rating'] = '推荐'
        elif total >= 60:
            scores['rating'] = '中性偏多'
        elif total >= 50:
            scores['rating'] = '中性'
        elif total >= 40:
            scores['rating'] = '中性偏空'
        else:
            scores['rating'] = '回避'
        
        return scores


# ==================== 综合策略生成器 ====================

class ComprehensiveSignalGenerator:
    """综合策略信号生成器"""
    
    def __init__(self):
        self.bar_signals = CZSCBarSignals()
        self.scorer = TechnicalScorer()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成综合交易信号"""
        df = df.copy()
        
        # 应用各种策略
        df = self.bar_signals.r_breaker(df)
        df = self.bar_signals.dual_thrust(df)
        df = self.bar_signals.shuang_fei_zt(df)
        df = self.bar_signals.limit_down_reverse(df)
        df = self.bar_signals.tnr_trend(df)
        
        # 综合信号
        df['signal'] = 0
        df['signal_type'] = ''
        
        for i in range(5, len(df)):
            signals = []
            
            # R-Breaker信号
            if df.iloc[i]['r_signal'] == 1:
                signals.append(('R-Breaker', 0.3))
            
            # Dual Thrust信号
            if df.iloc[i]['dt_signal'] == 1:
                signals.append(('通道突破', 0.3))
            
            # 双飞涨停
            if df.iloc[i]['shuangfei']:
                signals.append(('双飞涨停', 0.5))
            
            # 跌停反转
            if df.iloc[i]['ld_reverse']:
                signals.append(('跌停反转', 0.4))
            
            # TNR趋势
            if df.iloc[i]['tnr'] > 0.5:
                signals.append(('强趋势', 0.2))
            
            if signals:
                total_score = sum(s[1] for s in signals)
                if total_score >= 0.3:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('signal_type')] = '+'.join([s[0] for s in signals])
        
        return df
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """综合分析"""
        # 生成信号
        df = self.generate_signals(df)
        
        # 技术评分
        scores = self.scorer.calculate_total_score(df)
        
        # 最新状态
        latest = df.iloc[-1]
        
        result = {
            'scores': scores,
            'latest_signal': latest.get('signal', 0),
            'signal_type': latest.get('signal_type', ''),
            'tnr': latest.get('tnr', 0),
            'shuangfei': latest.get('shuangfei', False),
            'r_signal': latest.get('r_signal', 0),
            'r_type': latest.get('r_type', ''),
        }
        
        return result


# 创建全局实例
czsc_bar_signals = CZSCBarSignals()
technical_scorer = TechnicalScorer()
comprehensive_signal_generator = ComprehensiveSignalGenerator()
