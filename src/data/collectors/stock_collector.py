# -*- coding: utf-8 -*-
"""
Stock Analysis System - iTick Stock Data Collector
iTick API数据收集器
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.settings import settings
from src.utils.logger import get_logger
from src.utils.helpers import normalize_stock_code

logger = get_logger(__name__)


class ITickCollector:
    """iTick API数据收集器"""
    
    def __init__(self, api_token: str = None):
        """
        初始化收集器
        
        Args:
            api_token: iTick API Token
        """
        self.api_token = api_token or settings.itick.api_token
        self.base_url = settings.itick.base_url
        self.timeout = settings.itick.timeout
        self.max_retries = settings.itick.max_retries
        
        self.session = requests.Session()
        self.session.headers.update({
            'token': self.api_token,
            'Content-Type': 'application/json'
        })
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            API响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('code') == 0 or data.get('ret') == 0:
                    return data.get('data', data)
                else:
                    logger.warning(f"API返回错误: {data.get('msg', 'Unknown error')}")
                    return data
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时，重试 {attempt + 1}/{self.max_retries}")
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)
        
        return {}
    
    def get_stock_list(self, market: str = "CN") -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场代码 CN/HK/US
            
        Returns:
            股票列表DataFrame
        """
        try:
            endpoint = "/stock/stockList"
            params = {"market": market}
            
            data = self._request(endpoint, params)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
                logger.info(f"获取{market}市场股票列表 {len(df)}只")
                return df
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_kline(
        self, 
        stock_code: str, 
        kline_type: int = 1,
        start_timestamp: int = None,
        end_timestamp: int = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            stock_code: 股票代码 (如: HK.00700, US.AAPL, SH.600000)
            kline_type: K线类型 1-日K 2-周K 3-月K 4-1分钟 5-5分钟 6-15分钟 7-30分钟 8-60分钟
            start_timestamp: 开始时间戳(毫秒)
            end_timestamp: 结束时间戳(毫秒)
            limit: 返回条数限制
            
        Returns:
            K线数据DataFrame
        """
        try:
            endpoint = "/stock/kline"
            region = stock_code.split('.')[0] if '.' in stock_code else "CN"
            code = stock_code.split('.')[-1] if '.' in stock_code else stock_code
            
            # 港股需要去掉前导0 (00700 -> 700)
            if region == "HK":
                code = code.lstrip('0') or '0'
            
            params = {
                "region": region,
                "code": code,
                "kType": kline_type,
                "limit": limit
            }
            
            if end_timestamp:
                params["et"] = end_timestamp
            
            data = self._request(endpoint, params)
            
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                
                # 标准化列名
                column_mapping = {
                    't': 'trade_date',
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume',
                    'tu': 'amount'  # iTick API uses 'tu' for turnover/amount
                }
                df = df.rename(columns=column_mapping)
                
                # 转换时间戳
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date'], unit='ms')
                
                logger.info(f"获取{stock_code} K线数据 {len(df)}条")
                return df
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            实时行情DataFrame
        """
        try:
            endpoint = "/stock/quote"
            
            all_data = []
            for code in stock_codes:
                params = {
                    "region": code.split('.')[0] if '.' in code else "CN",
                    "code": code.split('.')[-1] if '.' in code else code
                }
                
                data = self._request(endpoint, params)
                
                if data:
                    data['stock_code'] = code
                    all_data.append(data)
            
            if all_data:
                df = pd.DataFrame(all_data)
                logger.info(f"获取实时行情 {len(df)}只")
                return df
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_trade_date(self, market: str = "CN") -> List[str]:
        """
        获取交易日历
        
        Args:
            market: 市场代码
            
        Returns:
            交易日期列表
        """
        try:
            endpoint = "/stock/tradeDate"
            params = {"market": market}
            
            data = self._request(endpoint, params)
            
            if isinstance(data, list):
                logger.info(f"获取{market}市场交易日历 {len(data)}天")
                return data
            
            return []
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return []
    
    def get_stock_detail(self, stock_code: str) -> Dict:
        """
        获取股票详情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票详情字典
        """
        try:
            endpoint = "/stock/detail"
            params = {
                "region": stock_code.split('.')[0] if '.' in stock_code else "CN",
                "code": stock_code.split('.')[-1] if '.' in stock_code else stock_code
            }
            
            data = self._request(endpoint, params)
            
            if data:
                logger.info(f"获取{stock_code}详情成功")
                return data
            
            return {}
        except Exception as e:
            logger.error(f"获取股票详情失败: {e}")
            return {}


class StockCollector:
    """股票数据收集器统一接口 - 支持AKShare和iTick"""
    
    def __init__(self, source: str = 'akshare'):
        """
        初始化收集器
        
        Args:
            source: 数据源 'akshare' 或 'itick'
        """
        self.itick = ITickCollector()
        self.source = source
        
        # 尝试加载AKShare
        try:
            from src.data.collectors.akshare_collector import akshare_collector
            self.akshare = akshare_collector
            self.akshare_available = akshare_collector.available
        except:
            self.akshare = None
            self.akshare_available = False
        
        # 初始化Baostock（作为第三备选）
        try:
            import baostock as bs
            self.baostock = bs
            self.baostock_available = True
        except:
            self.baostock = None
            self.baostock_available = False
    
    def get_daily_data(
        self, 
        stock_code: str, 
        start_date: str = None, 
        end_date: str = None,
        days: int = 100,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取日线数据
        
        优先级: 数据库缓存 → AKShare → Baostock → iTick
        """
        # 优先级1: 数据库缓存
        if use_cache:
            try:
                from src.data.services.db_service import db_service
                cached_df = db_service.get_cached_daily_data(stock_code)
                if cached_df is not None and not cached_df.empty and len(cached_df) >= days * 0.8:
                    logger.info(f"[缓存命中] {stock_code} 日K线数据 ({len(cached_df)}条)")
                    return cached_df
            except Exception as e:
                logger.debug(f"缓存查询失败: {e}")
        
        # 优先级2: AKShare（如果可用且是A股）
        df = None
        if self.akshare_available and self._is_a_share(stock_code):
            try:
                df = self.akshare.get_stock_daily(stock_code, start_date, end_date, days)
                if df is not None and not df.empty:
                    logger.info(f"AKShare获取数据成功: {stock_code}")
            except Exception as e:
                logger.warning(f"AKShare获取数据失败: {e}，尝试Baostock")
        
        # 优先级3: Baostock（仅A股）
        if (df is None or df.empty) and self.baostock_available and self._is_a_share(stock_code):
            try:
                df = self._get_baostock_data(stock_code, start_date, end_date, days)
                if df is not None and not df.empty:
                    logger.info(f"Baostock获取数据成功: {stock_code}")
            except Exception as e:
                logger.warning(f"Baostock获取数据失败: {e}，尝试iTick")
        
        # 优先级4: iTick
        if df is None or df.empty:
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_ts = int(end_dt.timestamp() * 1000)
            else:
                end_ts = None
            
            df = self.itick.get_stock_kline(
                stock_code=stock_code,
                kline_type=1,
                end_timestamp=end_ts,
                limit=days
            )
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        if start_date:
            start_dt = pd.Timestamp(start_date)
            df = df[df['trade_date'] >= start_dt]
        
        if end_date:
            end_dt = pd.Timestamp(end_date)
            df = df[df['trade_date'] <= end_dt]
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 缓存到数据库
        if use_cache and not df.empty:
            try:
                from src.data.services.db_service import db_service
                db_service.cache_daily_data(stock_code, df)
                logger.info(f"[缓存更新] {stock_code} 日K线数据已缓存")
            except Exception as e:
                logger.debug(f"缓存保存失败: {e}")
        
        return df
    
    def _get_baostock_data(self, stock_code: str, start_date: str = None, 
                          end_date: str = None, days: int = 100) -> pd.DataFrame:
        """使用Baostock获取日K线数据"""
        bs = self.baostock
        
        # 登录
        bs.login()
        
        try:
            # 转换股票代码格式
            code = stock_code.split('.')[-1] if '.' in stock_code else stock_code
            if code.startswith('6'):
                full_code = f'sh.{code}'
            else:
                full_code = f'sz.{code}'
            
            # 计算日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_dt = datetime.now() - timedelta(days=days + 30)
                start_date = start_dt.strftime('%Y-%m-%d')
            
            # 获取数据
            rs = bs.query_history_k_data_plus(
                full_code,
                'date,open,high,low,close,volume,amount,pctChg,turn',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='2'
            )
            
            df = rs.get_data()
            
            if df.empty:
                return pd.DataFrame()
            
            # 转换列名和类型
            df = df.rename(columns={
                'date': 'trade_date',
                'pctChg': 'pct_change',
                'turn': 'turnover'
            })
            
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.dropna(subset=['close']).tail(days)
            
            return df.reset_index(drop=True)
            
        finally:
            bs.logout()
    
    def _is_a_share(self, stock_code: str) -> bool:
        """判断是否为A股"""
        code = stock_code.split('.')[-1] if '.' in stock_code else stock_code
        prefix = stock_code.split('.')[0] if '.' in stock_code else ''
        
        # A股代码特征
        if prefix in ['SH', 'SZ', 'BJ']:
            return True
        if code.startswith(('6', '0', '3', '8', '4')):
            return True
        return False
    
    def get_minute_data(
        self, 
        stock_code: str, 
        kline_type: int = 4,
        limit: int = 500
    ) -> pd.DataFrame:
        """获取分钟线数据"""
        # AKShare分钟数据
        if self.akshare_available and self._is_a_share(stock_code):
            period_map = {4: '1', 5: '5', 6: '15', 7: '30', 8: '60'}
            period = period_map.get(kline_type, '5')
            try:
                df = self.akshare.get_stock_minute(stock_code, period, days=5)
                if not df.empty:
                    return df
            except:
                pass
        
        return self.itick.get_stock_kline(
            stock_code=stock_code,
            kline_type=kline_type,
            limit=limit
        )
    
    def get_realtime(self, stock_codes) -> pd.DataFrame:
        """获取实时行情"""
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        results = []
        for code in stock_codes:
            if self.akshare_available and self._is_a_share(code):
                quote = self.akshare.get_realtime_quote(code)
                if quote:
                    results.append(quote)
        
        if results:
            return pd.DataFrame(results)
        
        return self.itick.get_realtime_quote(stock_codes)
    
    def get_stock_list(self, market: str = "CN") -> pd.DataFrame:
        """获取股票列表"""
        return self.itick.get_stock_list(market)
    
    def get_limit_up_list(self, date: str = None) -> pd.DataFrame:
        """获取涨停股票列表"""
        if self.akshare_available:
            return self.akshare.get_limit_up_list(date)
        return pd.DataFrame()


# 创建全局收集器实例
stock_collector = StockCollector()

