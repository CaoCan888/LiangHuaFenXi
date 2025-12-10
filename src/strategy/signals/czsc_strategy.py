# -*- coding: utf-8 -*-
"""
CZSC (缠中说禅) 策略集成模块
"""

import warnings
warnings.filterwarnings('ignore')

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from collections import OrderedDict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入czsc
try:
    from czsc import CZSC, RawBar, Freq
    from czsc.signals.bar import (
        bar_zdt_V230331,
        bar_zt_count_V230504,
        bar_vol_grow_V221112,
        bar_fang_liang_break_V221216,
        bar_accelerate_V221110,
        bar_single_V230214,
        bar_triple_V230506,
    )
    from czsc.signals.tas import (
        update_macd_cache,
        update_ma_cache,
        tas_macd_base_V221028,
        tas_macd_bc_V221201,
        tas_ma_base_V221101,
    )
    CZSC_AVAILABLE = True
    logger.info("CZSC库加载成功")
except ImportError as e:
    CZSC_AVAILABLE = False
    logger.warning(f"CZSC库未安装: {e}")


class CZSCStrategy:
    """
    CZSC策略集成类
    
    集成缠论核心分析功能：
    - 分型、笔识别
    - 中枢分析
    - 买卖点信号
    - K线形态信号
    """
    
    def __init__(self):
        self.czsc_available = CZSC_AVAILABLE
    
    def df_to_raw_bars(self, df: pd.DataFrame, freq: str = 'D') -> List:
        """
        将DataFrame转换为CZSC的RawBar格式
        
        Args:
            df: 包含OHLCV的DataFrame
            freq: 频率 'D'-日线 '60'-60分钟 '30'-30分钟 等
        """
        if not self.czsc_available:
            return []
        
        freq_map = {
            'D': Freq.D,
            '60': Freq.F60,
            '30': Freq.F30,
            '15': Freq.F15,
            '5': Freq.F5,
            '1': Freq.F1,
        }
        
        bars = []
        for idx, row in df.iterrows():
            dt = idx if isinstance(idx, pd.Timestamp) else row.get('trade_date')
            if not isinstance(dt, pd.Timestamp):
                dt = pd.Timestamp(dt)
            
            bar = RawBar(
                symbol="",
                dt=dt,
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                close=float(row.get('close', 0)),
                vol=float(row.get('volume', 0)),
                amount=float(row.get('amount', 0)),
                freq=freq_map.get(freq, Freq.D)
            )
            bars.append(bar)
        
        return bars
    
    def analyze(self, df: pd.DataFrame, freq: str = 'D') -> Dict[str, Any]:
        """
        执行CZSC分析
        
        Args:
            df: K线数据
            freq: 频率
            
        Returns:
            分析结果字典
        """
        if not self.czsc_available:
            return {'error': 'CZSC库未安装'}
        
        # 转换数据格式
        bars = self.df_to_raw_bars(df, freq)
        if not bars:
            return {'error': '数据转换失败'}
        
        # 创建CZSC对象
        c = CZSC(bars)
        
        # 获取信号
        signals = {}
        
        try:
            # 涨跌停信号
            signals['zdt'] = bar_zdt_V230331(c)
        except:
            pass
        
        try:
            # 涨停计数
            signals['zt_count'] = bar_zt_count_V230504(c)
        except:
            pass
        
        try:
            # 量能增长
            signals['vol_grow'] = bar_vol_grow_V221112(c)
        except:
            pass
        
        try:
            # 放量突破
            signals['fang_liang_break'] = bar_fang_liang_break_V221216(c)
        except:
            pass
        
        try:
            # K线加速
            signals['accelerate'] = bar_accelerate_V221110(c)
        except:
            pass
        
        try:
            # 单K状态
            signals['single'] = bar_single_V230214(c)
        except:
            pass
        
        try:
            # 三K加速
            signals['triple'] = bar_triple_V230506(c)
        except:
            pass
        
        # 获取笔信息
        result = {
            'signals': signals,
            'bi_list': [self._bi_to_dict(bi) for bi in c.bi_list] if hasattr(c, 'bi_list') else [],
            'fx_list': [self._fx_to_dict(fx) for fx in c.fx_list] if hasattr(c, 'fx_list') else [],
        }
        
        return result
    
    def _bi_to_dict(self, bi) -> Dict:
        """将笔对象转换为字典"""
        try:
            return {
                'start_dt': str(bi.sdt),
                'end_dt': str(bi.edt),
                'direction': bi.direction.value if hasattr(bi.direction, 'value') else str(bi.direction),
                'high': bi.high,
                'low': bi.low,
            }
        except:
            return {}
    
    def _fx_to_dict(self, fx) -> Dict:
        """将分型对象转换为字典"""
        try:
            return {
                'dt': str(fx.dt),
                'mark': fx.mark.value if hasattr(fx.mark, 'value') else str(fx.mark),
                'high': fx.high,
                'low': fx.low,
            }
        except:
            return {}
    
    def get_bs_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取买卖点信号
        
        Returns:
            买卖点信号字典
        """
        if not self.czsc_available:
            return {'error': 'CZSC库未安装'}
        
        bars = self.df_to_raw_bars(df)
        if not bars:
            return {'error': '数据转换失败'}
        
        c = CZSC(bars)
        
        # 分析最新状态
        result = {
            'latest_bi_direction': None,
            'latest_fx_mark': None,
            'bi_count': len(c.bi_list) if hasattr(c, 'bi_list') else 0,
            'suggestion': 'hold'
        }
        
        if hasattr(c, 'bi_list') and c.bi_list:
            last_bi = c.bi_list[-1]
            result['latest_bi_direction'] = last_bi.direction.value if hasattr(last_bi.direction, 'value') else str(last_bi.direction)
            
            # 简单判断
            if result['latest_bi_direction'] == 'up':
                result['suggestion'] = 'sell_warning'  # 上升笔末端，可能回调
            elif result['latest_bi_direction'] == 'down':
                result['suggestion'] = 'buy_warning'  # 下降笔末端，可能反弹
        
        if hasattr(c, 'fx_list') and c.fx_list:
            last_fx = c.fx_list[-1]
            result['latest_fx_mark'] = last_fx.mark.value if hasattr(last_fx.mark, 'value') else str(last_fx.mark)
        
        return result


class CZSCSignalGenerator:
    """
    CZSC信号生成器 - 用于回测
    """
    
    def __init__(self):
        self.strategy = CZSCStrategy()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成基于CZSC的交易信号
        
        Args:
            df: K线数据
            
        Returns:
            添加signal列的DataFrame
        """
        df = df.copy()
        df['signal'] = 0
        
        if not self.strategy.czsc_available:
            logger.warning("CZSC库未安装，无法生成信号")
            return df
        
        # 需要足够的数据
        if len(df) < 30:
            return df
        
        # 使用滑动窗口生成信号
        for i in range(30, len(df)):
            window = df.iloc[:i+1].copy()
            
            try:
                result = self.strategy.get_bs_signals(window)
                
                if result.get('suggestion') == 'buy_warning':
                    # 下降笔末端 + 底分型 = 买入信号
                    if result.get('latest_fx_mark') == 'G':  # 底分型
                        df.iloc[i, df.columns.get_loc('signal')] = 1
                
                elif result.get('suggestion') == 'sell_warning':
                    # 上升笔末端 + 顶分型 = 卖出信号
                    if result.get('latest_fx_mark') == 'D':  # 顶分型
                        df.iloc[i, df.columns.get_loc('signal')] = -1
            except Exception as e:
                pass
        
        return df


# 创建全局实例
czsc_strategy = CZSCStrategy()
czsc_signal_generator = CZSCSignalGenerator()
