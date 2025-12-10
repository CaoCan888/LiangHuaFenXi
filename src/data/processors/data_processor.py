# -*- coding: utf-8 -*-
"""
Stock Analysis System - Data Processor
数据处理器
"""

from typing import Optional, List, Dict, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataProcessor:
    """数据处理器类"""
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        数据清洗
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            清洗后的DataFrame
        """
        if df.empty:
            return df
        
        # 复制数据
        df = df.copy()
        
        # 删除完全重复的行
        df = df.drop_duplicates()
        
        # 处理缺失值
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            # 使用前向填充
            df[col] = df[col].ffill()
            # 剩余的用后向填充
            df[col] = df[col].bfill()
        
        # 删除仍有缺失值的行
        df = df.dropna(subset=['close'] if 'close' in df.columns else None)
        
        logger.debug(f"数据清洗完成，剩余{len(df)}条")
        return df
    
    @staticmethod
    def handle_outliers(
        df: pd.DataFrame, 
        columns: List[str] = None,
        method: str = 'clip',
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        处理异常值
        
        Args:
            df: 数据DataFrame
            columns: 要处理的列，默认处理所有数值列
            method: 处理方法 'clip'-截断 'remove'-删除 'replace'-替换为中位数
            threshold: 异常值阈值（标准差倍数）
            
        Returns:
            处理后的DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df.columns:
                continue
            
            mean = df[col].mean()
            std = df[col].std()
            lower = mean - threshold * std
            upper = mean + threshold * std
            
            if method == 'clip':
                df[col] = df[col].clip(lower=lower, upper=upper)
            elif method == 'remove':
                df = df[(df[col] >= lower) & (df[col] <= upper)]
            elif method == 'replace':
                median = df[col].median()
                df.loc[(df[col] < lower) | (df[col] > upper), col] = median
        
        logger.debug(f"异常值处理完成，使用{method}方法")
        return df
    
    @staticmethod
    def resample_data(
        df: pd.DataFrame, 
        freq: str = 'W',
        date_column: str = None
    ) -> pd.DataFrame:
        """
        数据重采样（如日线转周线）
        
        Args:
            df: 数据DataFrame
            freq: 采样频率 'W'-周 'M'-月 'Q'-季度
            date_column: 日期列名
            
        Returns:
            重采样后的DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 设置日期索引
        if date_column and date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.set_index(date_column)
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # OHLCV重采样规则
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }
        
        # 只使用存在的列
        agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
        
        resampled = df.resample(freq).agg(agg_rules)
        resampled = resampled.dropna()
        
        logger.debug(f"数据重采样完成，频率: {freq}")
        return resampled
    
    @staticmethod
    def normalize(
        df: pd.DataFrame, 
        columns: List[str] = None,
        method: str = 'minmax'
    ) -> pd.DataFrame:
        """
        数据标准化
        
        Args:
            df: 数据DataFrame
            columns: 要标准化的列
            method: 标准化方法 'minmax'-最小最大 'zscore'-Z分数
            
        Returns:
            标准化后的DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df.columns:
                continue
            
            if method == 'minmax':
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val != min_val:
                    df[col] = (df[col] - min_val) / (max_val - min_val)
            elif method == 'zscore':
                mean = df[col].mean()
                std = df[col].std()
                if std != 0:
                    df[col] = (df[col] - mean) / std
        
        logger.debug(f"数据标准化完成，使用{method}方法")
        return df
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        计算收益率
        
        Args:
            df: 数据DataFrame
            price_column: 价格列名
            
        Returns:
            添加收益率列的DataFrame
        """
        if df.empty or price_column not in df.columns:
            return df
        
        df = df.copy()
        
        # 简单收益率
        df['return'] = df[price_column].pct_change()
        
        # 对数收益率
        df['log_return'] = np.log(df[price_column] / df[price_column].shift(1))
        
        # 累计收益率
        df['cum_return'] = (1 + df['return']).cumprod() - 1
        
        return df
    
    @staticmethod
    def merge_data(
        df1: pd.DataFrame, 
        df2: pd.DataFrame, 
        on: Union[str, List[str]] = None,
        how: str = 'left'
    ) -> pd.DataFrame:
        """
        合并数据
        
        Args:
            df1: 第一个DataFrame
            df2: 第二个DataFrame
            on: 合并键
            how: 合并方式
            
        Returns:
            合并后的DataFrame
        """
        if df1.empty:
            return df2
        if df2.empty:
            return df1
        
        return pd.merge(df1, df2, on=on, how=how)
    
    @staticmethod
    def add_time_features(df: pd.DataFrame, date_column: str = None) -> pd.DataFrame:
        """
        添加时间特征
        
        Args:
            df: 数据DataFrame
            date_column: 日期列名
            
        Returns:
            添加时间特征的DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 获取日期索引
        if date_column and date_column in df.columns:
            dates = pd.to_datetime(df[date_column])
        elif isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
        else:
            return df
        
        # 添加时间特征
        df['year'] = dates.year
        df['month'] = dates.month
        df['day'] = dates.day
        df['weekday'] = dates.weekday
        df['quarter'] = dates.quarter
        df['is_month_start'] = dates.is_month_start.astype(int)
        df['is_month_end'] = dates.is_month_end.astype(int)
        df['is_quarter_start'] = dates.is_quarter_start.astype(int)
        df['is_quarter_end'] = dates.is_quarter_end.astype(int)
        
        logger.debug("时间特征添加完成")
        return df


# 创建全局处理器实例
data_processor = DataProcessor()
