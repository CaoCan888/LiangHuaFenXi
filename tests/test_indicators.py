# -*- coding: utf-8 -*-
"""
技术指标测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis.indicators import TechnicalIndicators


class TestTechnicalIndicators:
    """技术指标测试类"""
    
    @pytest.fixture
    def sample_data(self):
        """生成测试数据"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=100)
        
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        high = close + np.abs(np.random.randn(100))
        low = close - np.abs(np.random.randn(100))
        open_ = close + np.random.randn(100) * 0.5
        volume = np.random.randint(1000000, 10000000, 100)
        
        df = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        
        return df
    
    def test_sma(self, sample_data):
        """测试简单移动平均"""
        result = TechnicalIndicators.SMA(sample_data['close'], 20)
        
        assert len(result) == len(sample_data)
        assert pd.isna(result.iloc[:19]).all()
        assert not pd.isna(result.iloc[19])
    
    def test_ema(self, sample_data):
        """测试指数移动平均"""
        result = TechnicalIndicators.EMA(sample_data['close'], 20)
        
        assert len(result) == len(sample_data)
        assert not pd.isna(result.iloc[-1])
    
    def test_macd(self, sample_data):
        """测试MACD"""
        result = TechnicalIndicators.MACD(sample_data['close'])
        
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_hist' in result.columns
    
    def test_rsi(self, sample_data):
        """测试RSI"""
        result = TechnicalIndicators.RSI(sample_data['close'], 14)
        
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()
    
    def test_bollinger(self, sample_data):
        """测试布林带"""
        result = TechnicalIndicators.BOLL(sample_data['close'])
        
        assert 'boll_upper' in result.columns
        assert 'boll_middle' in result.columns
        assert 'boll_lower' in result.columns
        
        valid_idx = result['boll_middle'].dropna().index
        assert (result.loc[valid_idx, 'boll_upper'] >= result.loc[valid_idx, 'boll_middle']).all()
        assert (result.loc[valid_idx, 'boll_middle'] >= result.loc[valid_idx, 'boll_lower']).all()
    
    def test_kdj(self, sample_data):
        """测试KDJ"""
        result = TechnicalIndicators.KDJ(sample_data['high'], sample_data['low'], sample_data['close'])
        
        assert 'kdj_k' in result.columns
        assert 'kdj_d' in result.columns
        assert 'kdj_j' in result.columns
    
    def test_add_all_indicators(self, sample_data):
        """测试添加所有指标"""
        result = TechnicalIndicators.add_all_indicators(sample_data)
        
        assert 'ma5' in result.columns
        assert 'macd' in result.columns
        assert 'rsi_14' in result.columns
        assert 'boll_upper' in result.columns
        assert 'kdj_k' in result.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
