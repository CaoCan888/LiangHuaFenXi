# -*- coding: utf-8 -*-
"""
涨停监控模块
扫描接近涨停和涨停股票
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.data.collectors.realtime_service import realtime_service, RealtimeQuote


@dataclass
class LimitStock:
    """涨停/接近涨停股票"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    status: str  # 'limit_up', 'near_limit', 'limit_down'
    limit_price: float  # 涨停价
    distance_pct: float  # 距离涨停价百分比
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'amount': self.amount,
            'status': self.status,
            'limit_price': self.limit_price,
            'distance_pct': self.distance_pct,
            'timestamp': self.timestamp
        }


class LimitMonitor:
    """涨停监控器"""
    
    def __init__(self):
        self.watchlist = []
        self.limit_stocks = {}  # 缓存涨停股票
    
    def set_watchlist(self, codes: List[str]):
        """设置监控列表"""
        self.watchlist = codes
    
    def _calculate_limit_price(self, pre_close: float, code: str = '') -> float:
        """计算涨停价"""
        # 根据股票类型确定涨停幅度
        if code.startswith('688') or code.startswith('30'):
            # 科创板/创业板 20%
            limit_pct = 0.20
        elif 'ST' in code.upper():
            # ST股 5%
            limit_pct = 0.05
        else:
            # 普通A股 10%
            limit_pct = 0.10
        
        return round(pre_close * (1 + limit_pct), 2)
    
    def analyze_quote(self, quote: RealtimeQuote) -> Optional[LimitStock]:
        """分析单个行情是否接近涨停"""
        if quote.pre_close <= 0:
            return None
        
        limit_price = self._calculate_limit_price(quote.pre_close, quote.code)
        distance_pct = (limit_price - quote.price) / quote.pre_close * 100
        
        # 判断状态
        if quote.change_pct >= 9.8:
            status = 'limit_up'
        elif quote.change_pct >= 7.0:
            status = 'near_limit'
        elif quote.change_pct <= -9.8:
            status = 'limit_down'
        else:
            return None
        
        return LimitStock(
            code=quote.code,
            name=quote.name,
            price=quote.price,
            change_pct=quote.change_pct,
            volume=quote.volume,
            amount=quote.amount,
            status=status,
            limit_price=limit_price,
            distance_pct=distance_pct,
            timestamp=datetime.now().strftime('%H:%M:%S')
        )
    
    def scan_limit_candidates(self, codes: List[str] = None) -> Dict[str, List[LimitStock]]:
        """
        扫描涨停候选股
        
        Args:
            codes: 要扫描的股票列表，None则使用watchlist
            
        Returns:
            {
                'limit_up': [涨停股票],
                'near_limit': [接近涨停股票],
                'limit_down': [跌停股票]
            }
        """
        if codes is None:
            codes = self.watchlist
        
        if not codes:
            return {'limit_up': [], 'near_limit': [], 'limit_down': []}
        
        quotes = realtime_service.get_realtime_quotes(codes)
        
        result = {'limit_up': [], 'near_limit': [], 'limit_down': []}
        
        for code, quote in quotes.items():
            limit_stock = self.analyze_quote(quote)
            if limit_stock:
                result[limit_stock.status].append(limit_stock)
        
        # 按涨幅排序
        for key in result:
            result[key].sort(key=lambda x: x.change_pct, reverse=True)
        
        return result
    
    def scan_hot_stocks(self) -> List[LimitStock]:
        """
        扫描热门股票（涨幅前列）
        使用AKShare获取涨幅榜
        """
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                return []
            
            # 获取涨幅>5%的股票
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            hot_df = df[df['涨跌幅'] >= 5].nlargest(50, '涨跌幅')
            
            codes = hot_df['代码'].tolist()
            
            # 获取实时行情
            quotes = realtime_service.get_realtime_quotes(codes)
            
            result = []
            for code, quote in quotes.items():
                limit_stock = self.analyze_quote(quote)
                if limit_stock:
                    result.append(limit_stock)
            
            result.sort(key=lambda x: x.change_pct, reverse=True)
            return result
            
        except Exception as e:
            print(f"扫描热门股票失败: {e}")
            return []
    
    def get_limit_statistics(self, codes: List[str] = None) -> dict:
        """
        获取涨停统计
        
        Returns:
            {
                'limit_up_count': 涨停数量,
                'near_limit_count': 接近涨停数量,
                'limit_down_count': 跌停数量,
                'top_gainers': 涨幅前5
            }
        """
        result = self.scan_limit_candidates(codes)
        
        all_stocks = result['limit_up'] + result['near_limit']
        all_stocks.sort(key=lambda x: x.change_pct, reverse=True)
        
        return {
            'limit_up_count': len(result['limit_up']),
            'near_limit_count': len(result['near_limit']),
            'limit_down_count': len(result['limit_down']),
            'top_gainers': all_stocks[:5],
            'limit_up_list': result['limit_up'],
            'near_limit_list': result['near_limit']
        }
    
    def to_dataframe(self, limit_stocks: List[LimitStock]) -> pd.DataFrame:
        """转换为DataFrame"""
        if not limit_stocks:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in limit_stocks])


# 全局实例
limit_monitor = LimitMonitor()


def scan_limit_candidates(codes: List[str]) -> Dict[str, List[LimitStock]]:
    """便捷函数：扫描涨停候选"""
    return limit_monitor.scan_limit_candidates(codes)


if __name__ == '__main__':
    # 测试
    test_codes = ['000592', '601933', '002682']
    result = scan_limit_candidates(test_codes)
    
    print("\n涨停监控测试:")
    print(f"涨停: {len(result['limit_up'])}只")
    for s in result['limit_up']:
        print(f"  {s.name} {s.change_pct:.1f}%")
    
    print(f"接近涨停: {len(result['near_limit'])}只")
    for s in result['near_limit']:
        print(f"  {s.name} {s.change_pct:.1f}% (距涨停: {s.distance_pct:.1f}%)")
