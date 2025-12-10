# -*- coding: utf-8 -*-
"""
AKShare 数据采集器
数据源：东方财富、新浪财经等
"""

import warnings
warnings.filterwarnings('ignore')

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AKShare加载成功")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装")


class AKShareCollector:
    """
    AKShare数据采集器
    
    支持:
    - A股日K/分钟K线
    - 实时行情
    - 涨跌停数据
    - 龙虎榜数据
    """
    
    def __init__(self):
        self.available = AKSHARE_AVAILABLE
    
    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        标准化股票代码
        
        输入: SH.600000 或 SZ.000001 或 600000
        输出: 600000 或 000001
        """
        if '.' in stock_code:
            return stock_code.split('.')[-1]
        return stock_code
    
    def _get_market(self, stock_code: str) -> str:
        """判断市场"""
        code = self._normalize_stock_code(stock_code)
        if code.startswith(('6', '9')):
            return 'sh'
        elif code.startswith(('0', '3', '2')):
            return 'sz'
        elif code.startswith(('4', '8')):
            return 'bj'  # 北交所
        return 'sh'
    
    def get_stock_daily(self, stock_code: str, start_date: str = None, end_date: str = None, days: int = 120) -> pd.DataFrame:
        """
        获取A股日K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            days: 获取天数
            
        Returns:
            DataFrame with columns: trade_date, open, high, low, close, volume, amount
        """
        if not self.available:
            logger.error("AKShare未安装")
            return pd.DataFrame()
        
        try:
            code = self._normalize_stock_code(stock_code)
            
            # 计算日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=days * 1.5)).strftime('%Y%m%d')
            
            # 获取数据 - 使用东方财富接口
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"未获取到数据: {stock_code}")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # 选择需要的列
            cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            extra_cols = ['pct_change', 'change', 'turnover']
            for col in extra_cols:
                if col in df.columns:
                    cols.append(col)
            
            df = df[cols]
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            # 限制数据量
            if len(df) > days:
                df = df.tail(days)
            
            logger.info(f"获取 {stock_code} 日K线数据 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取日K线失败: {e}")
            return pd.DataFrame()
    
    def get_stock_minute(self, stock_code: str, period: str = '5', days: int = 5) -> pd.DataFrame:
        """
        获取分钟K线数据
        
        Args:
            stock_code: 股票代码
            period: 周期 '1'/'5'/'15'/'30'/'60'
            days: 获取天数
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            code = self._normalize_stock_code(stock_code)
            
            # 分钟K线接口
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                period=period,
                start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S'),
                end_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                adjust="qfq"
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '时间': 'trade_time',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            logger.info(f"获取 {stock_code} {period}分钟K线数据 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取分钟K线失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, stock_code: str) -> Dict:
        """
        获取实时行情
        
        Returns:
            实时行情字典
        """
        if not self.available:
            return {}
        
        try:
            code = self._normalize_stock_code(stock_code)
            market = self._get_market(stock_code)
            
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 筛选目标股票
            row = df[df['代码'] == code]
            
            if row.empty:
                return {}
            
            row = row.iloc[0]
            
            result = {
                'code': code,
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'open': float(row.get('今开', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'pre_close': float(row.get('昨收', 0)),
                'change': float(row.get('涨跌额', 0)),
                'pct_change': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'turnover': float(row.get('换手率', 0)),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return {}
    
    def get_limit_up_list(self, date: str = None) -> pd.DataFrame:
        """
        获取涨停板股票列表
        
        Args:
            date: 日期 YYYYMMDD，默认今天
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            if not date:
                date = datetime.now().strftime('%Y%m%d')
            
            df = ak.stock_zt_pool_em(date=date)
            
            if df.empty:
                return pd.DataFrame()
            
            logger.info(f"获取涨停股 {len(df)} 只")
            return df
            
        except Exception as e:
            logger.error(f"获取涨停板数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_up_continuous(self) -> pd.DataFrame:
        """获取连板股票"""
        if not self.available:
            return pd.DataFrame()
        
        try:
            df = ak.stock_zt_pool_strong_em()
            logger.info(f"获取强势连板股 {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"获取连板数据失败: {e}")
            return pd.DataFrame()
    
    def get_dragon_tiger(self, date: str = None) -> pd.DataFrame:
        """获取龙虎榜数据"""
        if not self.available:
            return pd.DataFrame()
        
        try:
            if not date:
                date = datetime.now().strftime('%Y%m%d')
            
            df = ak.stock_lhb_detail_em(
                start_date=date,
                end_date=date
            )
            
            logger.info(f"获取龙虎榜数据 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取龙虎榜失败: {e}")
            return pd.DataFrame()
    
    def get_dragon_tiger_summary(self, stock_code: str = None) -> pd.DataFrame:
        """获取龙虎榜汇总 - 营业部统计"""
        if not self.available:
            return pd.DataFrame()
        
        try:
            df = ak.stock_lhb_hyyyb_em()
            if stock_code:
                code = self._normalize_stock_code(stock_code)
                df = df[df['代码'].str.contains(code)]
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜汇总失败: {e}")
            return pd.DataFrame()
    
    def get_stock_dragon_tiger(self, stock_code: str) -> pd.DataFrame:
        """获取个股龙虎榜历史"""
        if not self.available:
            return pd.DataFrame()
        
        try:
            code = self._normalize_stock_code(stock_code)
            df = ak.stock_lhb_stock_detail_em(symbol=code)
            return df
        except Exception as e:
            logger.error(f"获取个股龙虎榜失败: {e}")
            return pd.DataFrame()
    
    def get_hot_stocks(self) -> pd.DataFrame:
        """获取人气榜"""
        if not self.available:
            return pd.DataFrame()
        
        try:
            df = ak.stock_hot_rank_em()
            return df
        except Exception as e:
            logger.error(f"获取人气榜失败: {e}")
            return pd.DataFrame()


# 创建全局实例
akshare_collector = AKShareCollector()

