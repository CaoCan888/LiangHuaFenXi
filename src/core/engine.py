# -*- coding: utf-8 -*-
"""
分析引擎 - 整合各模块的统一接口
"""

from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data.collectors import stock_collector
from src.data.processors import data_processor
from src.data.storage import get_db_manager
from src.analysis import technical_analyzer
from src.strategy import signal_generator, backtest_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisEngine:
    """分析引擎"""
    
    def __init__(self):
        self.collector = stock_collector
        self.processor = data_processor
        self.analyzer = technical_analyzer
        self.signal_gen = signal_generator
        self.backtest = backtest_engine
    
    def fetch_data(self, stock_code: str, days: int = 120, save_to_db: bool = False) -> pd.DataFrame:
        """获取并处理数据"""
        logger.info(f"获取数据: {stock_code}, {days}天")
        
        # 获取数据
        df = self.collector.get_daily_data(stock_code, days=days)
        
        if df.empty:
            logger.warning(f"未获取到数据: {stock_code}")
            return df
        
        # 数据清洗
        df = self.processor.clean_data(df)
        
        # 保存到数据库
        if save_to_db:
            try:
                db = get_db_manager()
                db.save_daily_prices(stock_code, df)
            except Exception as e:
                logger.error(f"保存数据失败: {e}")
        
        return df
    
    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行技术分析"""
        return self.analyzer.analyze(df)
    
    def get_signals(self, df: pd.DataFrame, strategy: str = 'combined') -> pd.DataFrame:
        """生成交易信号"""
        return self.signal_gen.generate(df, strategy)
    
    def run_backtest(self, df: pd.DataFrame, strategy: str = 'combined', initial_capital: float = 1000000) -> Dict:
        """运行回测"""
        df_signal = self.get_signals(df, strategy)
        self.backtest.initial_capital = initial_capital
        return self.backtest.run(df_signal, strategy)
    
    def full_analysis(self, stock_code: str, days: int = 120, strategy: str = 'combined') -> Dict[str, Any]:
        """完整分析流程"""
        logger.info(f"开始完整分析: {stock_code}")
        
        # 获取数据
        df = self.fetch_data(stock_code, days)
        if df.empty:
            return {'error': '获取数据失败'}
        
        # 技术分析
        df = self.analyze(df)
        
        # 设置索引
        if 'trade_date' in df.columns:
            df.set_index('trade_date', inplace=True)
        
        # 分析摘要
        summary = self.analyzer.get_summary(df)
        
        # 回测
        backtest_result = self.run_backtest(df, strategy)
        
        return {
            'stock_code': stock_code,
            'data': df,
            'summary': summary,
            'backtest': backtest_result
        }


analysis_engine = AnalysisEngine()
