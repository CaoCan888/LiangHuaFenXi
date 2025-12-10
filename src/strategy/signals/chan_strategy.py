# -*- coding: utf-8 -*-
"""
缠论策略模块 - 简化实现
基于缠中说禅理论的分型、笔识别和买卖点信号

不依赖外部czsc库，自行实现核心逻辑
"""

import warnings
warnings.filterwarnings('ignore')

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Direction(Enum):
    """方向枚举"""
    UP = "up"
    DOWN = "down"


class Mark(Enum):
    """分型标记"""
    D = "顶分型"  # 顶分型
    G = "底分型"  # 底分型


@dataclass
class FX:
    """分型"""
    dt: pd.Timestamp  # 分型时间
    mark: Mark        # 分型类型
    high: float       # 最高价
    low: float        # 最低价
    fx: float         # 分型价格（顶分型取high，底分型取low）


@dataclass 
class BI:
    """笔"""
    start_dt: pd.Timestamp
    end_dt: pd.Timestamp
    direction: Direction
    high: float
    low: float
    power: float  # 笔的力度


@dataclass
class ZhongShu:
    """中枢（Pivot Zone）"""
    start_dt: pd.Timestamp
    end_dt: pd.Timestamp
    zg: float  # 中枢高点 (ZG)
    zd: float  # 中枢低点 (ZD)
    gg: float  # 中枢区间最高点
    dd: float  # 中枢区间最低点
    bi_count: int  # 构成中枢的笔数量
    direction: Direction  # 中枢方向（由形成中枢的笔决定）


class ChanAnalyzer:
    """
    缠论分析器
    
    核心功能:
    1. K线包含处理
    2. 分型识别
    3. 笔划分
    4. 买卖点判断
    """
    
    def __init__(self):
        self.min_bi_len = 5  # 笔的最小K线数
    
    def process_include(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        K线包含处理
        
        规则：
        - 相邻两根K线存在包含关系时，合并为一根
        - 上涨趋势：取高点最高、低点最高
        - 下跌趋势：取高点最低、低点最低
        """
        df = df.copy()
        
        # 确保有必要的列
        if 'high' not in df.columns or 'low' not in df.columns:
            return df
        
        # 判断趋势方向（通过前后K线高低点判断）
        processed = []
        
        for i, row in df.iterrows():
            if len(processed) == 0:
                processed.append({
                    'dt': i if isinstance(i, pd.Timestamp) else row.get('trade_date', i),
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row.get('volume', 0)
                })
                continue
            
            prev = processed[-1]
            curr_high, curr_low = row['high'], row['low']
            prev_high, prev_low = prev['high'], prev['low']
            
            # 检查包含关系
            is_include = (curr_high <= prev_high and curr_low >= prev_low) or \
                        (curr_high >= prev_high and curr_low <= prev_low)
            
            if is_include:
                # 存在包含关系，合并K线
                # 判断方向：比较前一根与更前一根的高低点
                if len(processed) >= 2:
                    direction_up = processed[-2]['high'] < prev_high
                else:
                    direction_up = row['close'] > row['open']
                
                if direction_up:
                    # 上涨趋势：取高点最高、低点最高
                    prev['high'] = max(prev_high, curr_high)
                    prev['low'] = max(prev_low, curr_low)
                else:
                    # 下跌趋势：取高点最低、低点最低
                    prev['high'] = min(prev_high, curr_high)
                    prev['low'] = min(prev_low, curr_low)
            else:
                processed.append({
                    'dt': i if isinstance(i, pd.Timestamp) else row.get('trade_date', i),
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row.get('volume', 0)
                })
        
        return pd.DataFrame(processed).set_index('dt')
    
    def find_fx(self, df: pd.DataFrame) -> List[FX]:
        """
        识别分型
        
        顶分型：中间K线的高点是三根中最高的
        底分型：中间K线的低点是三根中最低的
        """
        fx_list = []
        
        if len(df) < 3:
            return fx_list
        
        for i in range(1, len(df) - 1):
            k1 = df.iloc[i - 1]
            k2 = df.iloc[i]
            k3 = df.iloc[i + 1]
            
            dt = df.index[i]
            
            # 顶分型
            if k2['high'] > k1['high'] and k2['high'] > k3['high']:
                if k2['low'] > k1['low'] and k2['low'] > k3['low']:
                    fx = FX(dt=dt, mark=Mark.D, high=k2['high'], low=k2['low'], fx=k2['high'])
                    fx_list.append(fx)
            
            # 底分型
            elif k2['low'] < k1['low'] and k2['low'] < k3['low']:
                if k2['high'] < k1['high'] and k2['high'] < k3['high']:
                    fx = FX(dt=dt, mark=Mark.G, high=k2['high'], low=k2['low'], fx=k2['low'])
                    fx_list.append(fx)
        
        return fx_list
    
    def find_bi(self, df: pd.DataFrame, fx_list: List[FX]) -> List[BI]:
        """
        划分笔
        
        规则：
        1. 顶分型与底分型之间至少有1根独立K线
        2. 顶底分型之间价格有重合（顶低于前底或底高于前顶则不成笔）
        """
        bi_list = []
        
        if len(fx_list) < 2:
            return bi_list
        
        # 过滤：相邻分型必须是顶底交替
        valid_fx = [fx_list[0]]
        for fx in fx_list[1:]:
            if fx.mark != valid_fx[-1].mark:
                valid_fx.append(fx)
            else:
                # 同类型分型，保留更极端的
                if fx.mark == Mark.D and fx.fx > valid_fx[-1].fx:
                    valid_fx[-1] = fx
                elif fx.mark == Mark.G and fx.fx < valid_fx[-1].fx:
                    valid_fx[-1] = fx
        
        # 构建笔
        for i in range(1, len(valid_fx)):
            start_fx = valid_fx[i - 1]
            end_fx = valid_fx[i]
            
            if start_fx.mark == Mark.G:  # 从底到顶，上涨笔
                direction = Direction.UP
                high = end_fx.high
                low = start_fx.low
            else:  # 从顶到底，下跌笔
                direction = Direction.DOWN
                high = start_fx.high
                low = end_fx.low
            
            power = abs(high - low) / low if low > 0 else 0
            
            bi = BI(
                start_dt=start_fx.dt,
                end_dt=end_fx.dt,
                direction=direction,
                high=high,
                low=low,
                power=power
            )
            bi_list.append(bi)
        
        return bi_list
    
    def find_zhongshu(self, bi_list: List[BI]) -> List[ZhongShu]:
        """
        识别中枢
        
        中枢定义：至少三笔重叠的价格区间
        ZG = min(第二、三笔的高点)
        ZD = max(第二、三笔的低点)
        条件：ZG > ZD 才形成有效中枢
        """
        zs_list = []
        
        if len(bi_list) < 3:
            return zs_list
        
        i = 0
        while i < len(bi_list) - 2:
            bi1 = bi_list[i]
            bi2 = bi_list[i + 1]
            bi3 = bi_list[i + 2]
            
            # 计算中枢区间
            # 方法1：取三笔的重叠区间
            highs = [bi1.high, bi2.high, bi3.high]
            lows = [bi1.low, bi2.low, bi3.low]
            
            zg = min(bi2.high, bi3.high)  # 中枢高点
            zd = max(bi2.low, bi3.low)    # 中枢低点
            
            # 中枢有效条件：ZG > ZD（存在重叠区间）
            if zg > zd:
                # 尝试延伸中枢（后续笔是否仍在中枢区间内）
                bi_count = 3
                end_dt = bi3.end_dt
                gg = max(highs)  # 区间最高
                dd = min(lows)   # 区间最低
                
                j = i + 3
                while j < len(bi_list):
                    next_bi = bi_list[j]
                    # 如果下一笔的高低点与中枢有重叠，继续延伸
                    if next_bi.low < zg and next_bi.high > zd:
                        bi_count += 1
                        end_dt = next_bi.end_dt
                        gg = max(gg, next_bi.high)
                        dd = min(dd, next_bi.low)
                        j += 1
                    else:
                        break
                
                zs = ZhongShu(
                    start_dt=bi1.start_dt,
                    end_dt=end_dt,
                    zg=zg,
                    zd=zd,
                    gg=gg,
                    dd=dd,
                    bi_count=bi_count,
                    direction=bi1.direction
                )
                zs_list.append(zs)
                
                # 跳过已处理的笔
                i = j
            else:
                i += 1
        
        return zs_list
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行缠论分析
        
        Returns:
            分析结果字典
        """
        # 包含处理
        processed_df = self.process_include(df)
        
        # 识别分型
        fx_list = self.find_fx(processed_df)
        
        # 划分笔
        bi_list = self.find_bi(processed_df, fx_list)
        
        # 识别中枢
        zs_list = self.find_zhongshu(bi_list)
        
        # 当前状态
        result = {
            'processed_bars': len(processed_df),
            'fx_count': len(fx_list),
            'bi_count': len(bi_list),
            'zs_count': len(zs_list),  # 中枢数量
            'fx_list': fx_list,
            'bi_list': bi_list,
            'zs_list': zs_list,  # 中枢列表
            'latest_fx': fx_list[-1] if fx_list else None,
            'latest_bi': bi_list[-1] if bi_list else None,
            'latest_zs': zs_list[-1] if zs_list else None,  # 最新中枢
        }
        
        return result
    
    def get_bs_point(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取买卖点信号
        
        一买：下跌笔结束，出现底分型
        一卖：上涨笔结束，出现顶分型
        二买：回调到中枢下沿附近不创新低
        三买：中枢上沿突破后回踩不跌破中枢高点
        """
        analysis = self.analyze(df)
        
        result = {
            'signal': 0,  # 1=买, -1=卖, 0=无
            'signal_type': '',
            'latest_fx': None,
            'latest_bi': None,
            'latest_zs': None,
            'suggestion': 'hold'
        }
        
        # 获取中枢信息
        if analysis.get('latest_zs'):
            zs = analysis['latest_zs']
            result['latest_zs'] = {
                'zg': zs.zg,
                'zd': zs.zd,
                'bi_count': zs.bi_count
            }
        
        if analysis['latest_bi']:
            bi = analysis['latest_bi']
            result['latest_bi'] = {
                'direction': bi.direction.value,
                'power': bi.power
            }
            
            if analysis['latest_fx']:
                fx = analysis['latest_fx']
                result['latest_fx'] = {
                    'mark': fx.mark.value,
                    'fx': fx.fx
                }
                
                # 一买信号：下跌笔 + 底分型
                if bi.direction == Direction.DOWN and fx.mark == Mark.G:
                    result['signal'] = 1
                    result['signal_type'] = '一买'
                    result['suggestion'] = 'buy'
                
                # 一卖信号：上涨笔 + 顶分型
                elif bi.direction == Direction.UP and fx.mark == Mark.D:
                    result['signal'] = -1
                    result['signal_type'] = '一卖'
                    result['suggestion'] = 'sell'
                
                # 二买/三买信号（需要有中枢）
                elif analysis.get('latest_zs'):
                    zs = analysis['latest_zs']
                    latest_price = df['close'].iloc[-1] if 'close' in df.columns else 0
                    
                    # 二买：回调到中枢下沿附近，出现底分型，且不创新低
                    if fx.mark == Mark.G and bi.direction == Direction.DOWN:
                        # 回调接近中枢下沿ZD
                        if fx.fx <= zs.zd * 1.02 and fx.fx > zs.dd:
                            result['signal'] = 1
                            result['signal_type'] = '二买'
                            result['suggestion'] = 'buy'
                    
                    # 三买：突破中枢上沿后回踩，不跌破中枢高点ZG
                    if fx.mark == Mark.G and bi.direction == Direction.DOWN:
                        # 回踩在中枢上沿ZG之上
                        if fx.fx >= zs.zg:
                            result['signal'] = 1
                            result['signal_type'] = '三买'
                            result['suggestion'] = 'buy'
        
        return result


class ChanSignalGenerator:
    """
    缠论信号生成器
    """
    
    def __init__(self):
        self.analyzer = ChanAnalyzer()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成缠论交易信号
        """
        df = df.copy()
        df['signal'] = 0
        df['signal_type'] = ''
        
        if len(df) < 10:
            return df
        
        # 设置索引
        if 'trade_date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df.set_index('trade_date', inplace=True)
        
        # 滑动窗口分析
        window_size = 30
        for i in range(window_size, len(df)):
            window = df.iloc[:i+1].copy()
            
            try:
                result = self.analyzer.get_bs_point(window)
                
                if result['signal'] == 1:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('signal_type')] = result['signal_type']
                elif result['signal'] == -1:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('signal_type')] = result['signal_type']
            except Exception as e:
                pass
        
        return df


# 创建全局实例
chan_analyzer = ChanAnalyzer()
chan_signal_generator = ChanSignalGenerator()
