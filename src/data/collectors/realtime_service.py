# -*- coding: utf-8 -*-
"""
实时行情服务
使用新浪财经API获取实时股票数据
"""
import requests
import pandas as pd
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import time
import threading


@dataclass
class RealtimeQuote:
    """实时行情数据"""
    code: str
    name: str
    open: float
    pre_close: float
    price: float
    high: float
    low: float
    volume: float  # 手
    amount: float  # 元
    bid_prices: List[float]  # 买1-5价
    ask_prices: List[float]  # 卖1-5价
    bid_volumes: List[int]   # 买1-5量
    ask_volumes: List[int]   # 卖1-5量
    date: str
    time: str
    
    @property
    def change_pct(self) -> float:
        """涨跌幅"""
        if self.pre_close > 0:
            return (self.price / self.pre_close - 1) * 100
        return 0.0
    
    @property
    def change_amount(self) -> float:
        """涨跌额"""
        return self.price - self.pre_close
    
    @property
    def amplitude(self) -> float:
        """振幅"""
        if self.pre_close > 0:
            return (self.high - self.low) / self.pre_close * 100
        return 0.0
    
    @property
    def volume_ratio(self) -> float:
        """量比（简化版，与5日均量比）"""
        # 这里暂时返回1，实际需要历史数据计算
        return 1.0
    
    @property
    def is_limit_up(self) -> bool:
        """是否涨停"""
        return self.change_pct >= 9.8
    
    @property
    def is_limit_down(self) -> bool:
        """是否跌停"""
        return self.change_pct <= -9.8
    
    @property
    def near_limit_up(self) -> bool:
        """接近涨停（涨幅>7%）"""
        return self.change_pct >= 7.0
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'pre_close': self.pre_close,
            'volume': self.volume,
            'amount': self.amount,
            'date': self.date,
            'time': self.time,
            'is_limit_up': self.is_limit_up,
            'near_limit_up': self.near_limit_up
        }


class RealtimeService:
    """实时行情服务"""
    
    SINA_API = 'http://hq.sinajs.cn/list='
    HEADERS = {'Referer': 'http://finance.sina.com.cn'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._monitor_running = False
        self._monitor_thread = None
    
    def _code_to_symbol(self, code: str) -> str:
        """转换股票代码为新浪格式"""
        # 去除市场前缀
        if '.' in code:
            parts = code.split('.')
            market = parts[0].upper()
            symbol = parts[-1]
        else:
            symbol = code
            market = ''
        
        # 判断市场
        if market in ['SH', 'SSE']:
            return f'sh{symbol}'
        elif market in ['SZ', 'SZSE']:
            return f'sz{symbol}'
        elif symbol.startswith('6'):
            return f'sh{symbol}'
        elif symbol.startswith(('0', '3')):
            return f'sz{symbol}'
        else:
            return f'sz{symbol}'
    
    def get_realtime_quote(self, code: str) -> Optional[RealtimeQuote]:
        """
        获取单个股票的实时行情
        
        Args:
            code: 股票代码，如 '000592' 或 'SZ.000592'
            
        Returns:
            RealtimeQuote对象，失败返回None
        """
        quotes = self.get_realtime_quotes([code])
        return quotes.get(code)
    
    def get_realtime_quotes(self, codes: List[str]) -> Dict[str, RealtimeQuote]:
        """
        批量获取实时行情
        
        Args:
            codes: 股票代码列表
            
        Returns:
            {code: RealtimeQuote} 字典
        """
        if not codes:
            return {}
        
        # 转换代码
        code_map = {self._code_to_symbol(c): c for c in codes}
        symbols = ','.join(code_map.keys())
        
        try:
            url = f'{self.SINA_API}{symbols}'
            response = self.session.get(url, timeout=5)
            response.encoding = 'gbk'
            
            result = {}
            for line in response.text.strip().split('\n'):
                if not line or '=' not in line:
                    continue
                
                # 解析: var hq_str_sz000592="平潭发展,..."
                parts = line.split('=')
                if len(parts) != 2:
                    continue
                
                symbol = parts[0].split('_')[-1].strip()
                data_str = parts[1].strip().strip('"').strip(';').strip('"')
                
                if not data_str:
                    continue
                
                data = data_str.split(',')
                if len(data) < 32:
                    continue
                
                original_code = code_map.get(symbol, symbol)
                
                quote = RealtimeQuote(
                    code=original_code,
                    name=data[0],
                    open=float(data[1]) if data[1] else 0,
                    pre_close=float(data[2]) if data[2] else 0,
                    price=float(data[3]) if data[3] else 0,
                    high=float(data[4]) if data[4] else 0,
                    low=float(data[5]) if data[5] else 0,
                    volume=float(data[8]) / 100 if data[8] else 0,  # 转换为手
                    amount=float(data[9]) if data[9] else 0,
                    bid_prices=[float(data[i]) if data[i] else 0 for i in [11, 13, 15, 17, 19]],
                    ask_prices=[float(data[i]) if data[i] else 0 for i in [21, 23, 25, 27, 29]],
                    bid_volumes=[int(float(data[i])/100) if data[i] else 0 for i in [10, 12, 14, 16, 18]],
                    ask_volumes=[int(float(data[i])/100) if data[i] else 0 for i in [20, 22, 24, 26, 28]],
                    date=data[30] if len(data) > 30 else '',
                    time=data[31] if len(data) > 31 else ''
                )
                
                result[original_code] = quote
            
            return result
            
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return {}
    
    def get_realtime_df(self, codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情DataFrame
        
        Args:
            codes: 股票代码列表
            
        Returns:
            DataFrame with columns: code, name, price, change_pct, ...
        """
        quotes = self.get_realtime_quotes(codes)
        if not quotes:
            return pd.DataFrame()
        
        data = [q.to_dict() for q in quotes.values()]
        return pd.DataFrame(data)
    
    def start_monitor(self, codes: List[str], callback: Callable, interval: float = 3.0):
        """
        开始监控股票价格变动
        
        Args:
            codes: 要监控的股票代码列表
            callback: 回调函数，接收 Dict[str, RealtimeQuote] 参数
            interval: 刷新间隔（秒）
        """
        self._monitor_running = True
        
        def _monitor_loop():
            while self._monitor_running:
                quotes = self.get_realtime_quotes(codes)
                if quotes:
                    callback(quotes)
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitor(self):
        """停止监控"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def get_intraday_data(self, code: str, datalen: int = 48) -> pd.DataFrame:
        """
        获取分时数据（5分钟线）
        使用新浪财经API，盘中实时更新
        
        Args:
            code: 股票代码
            datalen: 数据条数（48条约为一天）
            
        Returns:
            DataFrame with columns: time, open, high, low, close, volume
        """
        symbol = self._code_to_symbol(code)
        
        url = f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {
            'symbol': symbol,
            'scale': 5,  # 5分钟
            'ma': 'no',
            'datalen': datalen
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if not response.ok or not response.text:
                return pd.DataFrame()
            
            # 解析JSON
            import json
            data = json.loads(response.text)
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # 重命名列
            df = df.rename(columns={
                'day': 'time',
            })
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"获取分时数据失败: {e}")
            return pd.DataFrame()


# 全局实例
realtime_service = RealtimeService()


def get_realtime_quote(code: str) -> Optional[RealtimeQuote]:
    """便捷函数：获取单个股票实时行情"""
    return realtime_service.get_realtime_quote(code)


def get_realtime_quotes(codes: List[str]) -> Dict[str, RealtimeQuote]:
    """便捷函数：批量获取实时行情"""
    return realtime_service.get_realtime_quotes(codes)


def get_intraday_data(code: str, datalen: int = 48) -> pd.DataFrame:
    """便捷函数：获取分时数据"""
    return realtime_service.get_intraday_data(code, datalen)


if __name__ == '__main__':
    # 测试
    quote = get_realtime_quote('000592')
    if quote:
        print(f"股票: {quote.name}")
        print(f"价格: {quote.price:.2f}")
        print(f"涨跌: {quote.change_pct:+.2f}%")
        print(f"成交量: {quote.volume/10000:.0f}万手")
        print(f"涨停: {quote.is_limit_up}")
        print(f"接近涨停: {quote.near_limit_up}")
    
    # 测试分时数据
    intraday = get_intraday_data('000592')
    print(f"\n分时数据: {len(intraday)}条")
    if not intraday.empty:
        print(intraday.tail(5))
