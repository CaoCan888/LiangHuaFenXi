# -*- coding: utf-8 -*-
"""
大单追踪模块
监控主力资金流向和大单交易
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.data.collectors.realtime_service import get_realtime_quote, RealtimeQuote


@dataclass  
class FundFlowData:
    """资金流向数据"""
    code: str
    name: str
    price: float
    change_pct: float
    main_net_inflow: float  # 主力净流入（万元）
    main_net_ratio: float   # 主力净占比（%）
    super_big_net: float    # 超大单净流入
    big_net: float          # 大单净流入
    mid_net: float          # 中单净流入
    small_net: float        # 小单净流入
    timestamp: str
    
    @property
    def flow_direction(self) -> str:
        """资金流向"""
        if self.main_net_inflow > 0:
            return "流入"
        elif self.main_net_inflow < 0:
            return "流出"
        return "均衡"
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'main_net_inflow': self.main_net_inflow,
            'main_net_ratio': self.main_net_ratio,
            'flow_direction': self.flow_direction,
            'timestamp': self.timestamp
        }


@dataclass
class BuySellPressure:
    """买卖压力分析"""
    code: str
    name: str
    bid_volume: int    # 买盘挂单量
    ask_volume: int    # 卖盘挂单量
    bid_ratio: float   # 买盘占比
    pressure: str      # 'buy_strong', 'sell_strong', 'balanced'
    pressure_score: int  # 压力评分 -100到100
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'bid_volume': self.bid_volume,
            'ask_volume': self.ask_volume,
            'bid_ratio': self.bid_ratio,
            'pressure': self.pressure,
            'pressure_score': self.pressure_score,
            'timestamp': self.timestamp
        }


class BigOrderTracker:
    """大单追踪器"""
    
    def __init__(self):
        self.cache = {}
    
    def get_fund_flow(self, code: str) -> Optional[FundFlowData]:
        """
        获取个股资金流向
        使用AKShare获取数据
        """
        try:
            import akshare as ak
            
            # 清洗代码
            clean_code = code.split('.')[-1] if '.' in code else code
            market = 'sh' if clean_code.startswith('6') else 'sz'
            
            # 获取资金流向
            df = ak.stock_individual_fund_flow(stock=clean_code, market=market)
            
            if df is None or df.empty:
                return None
            
            # 获取最新一天数据
            latest = df.iloc[-1]
            
            # 获取实时行情
            quote = get_realtime_quote(code)
            
            # 解析资金流向列
            main_net = 0
            super_big = 0
            big_net = 0
            
            for col in df.columns:
                if '主力' in col and '净' in col:
                    main_net = float(latest[col]) if pd.notna(latest[col]) else 0
                elif '超大单' in col and '净' in col:
                    super_big = float(latest[col]) if pd.notna(latest[col]) else 0
                elif '大单' in col and '净' in col and '超' not in col:
                    big_net = float(latest[col]) if pd.notna(latest[col]) else 0
            
            return FundFlowData(
                code=code,
                name=quote.name if quote else '',
                price=quote.price if quote else 0,
                change_pct=quote.change_pct if quote else 0,
                main_net_inflow=main_net / 10000,  # 转万元
                main_net_ratio=0,
                super_big_net=super_big / 10000,
                big_net=big_net / 10000,
                mid_net=0,
                small_net=0,
                timestamp=datetime.now().strftime('%H:%M:%S')
            )
            
        except Exception as e:
            print(f"获取资金流向失败: {e}")
            return None
    
    def get_buy_sell_pressure(self, code: str) -> Optional[BuySellPressure]:
        """
        分析买卖压力
        通过实时行情的买卖盘挂单分析
        """
        quote = get_realtime_quote(code)
        if not quote:
            return None
        
        bid_volume = sum(quote.bid_volumes)
        ask_volume = sum(quote.ask_volumes)
        total = bid_volume + ask_volume
        
        if total == 0:
            return None
        
        bid_ratio = bid_volume / total
        
        # 计算压力评分
        pressure_score = int((bid_ratio - 0.5) * 200)
        
        if bid_ratio > 0.6:
            pressure = 'buy_strong'
        elif bid_ratio < 0.4:
            pressure = 'sell_strong'
        else:
            pressure = 'balanced'
        
        return BuySellPressure(
            code=code,
            name=quote.name,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            bid_ratio=bid_ratio,
            pressure=pressure,
            pressure_score=pressure_score,
            timestamp=datetime.now().strftime('%H:%M:%S')
        )
    
    def scan_fund_flow(self, codes: List[str]) -> List[FundFlowData]:
        """批量扫描资金流向"""
        results = []
        for code in codes:
            data = self.get_fund_flow(code)
            if data:
                results.append(data)
        
        # 按主力净流入排序
        results.sort(key=lambda x: x.main_net_inflow, reverse=True)
        return results
    
    def scan_pressure(self, codes: List[str]) -> List[BuySellPressure]:
        """批量扫描买卖压力"""
        results = []
        for code in codes:
            data = self.get_buy_sell_pressure(code)
            if data:
                results.append(data)
        
        # 按压力评分排序
        results.sort(key=lambda x: x.pressure_score, reverse=True)
        return results
    
    def get_top_inflow_stocks(self, limit: int = 20) -> pd.DataFrame:
        """
        获取主力资金流入前N名
        """
        try:
            import akshare as ak
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 选择需要的列
            cols = []
            for c in df.columns:
                if any(x in c for x in ['代码', '名称', '价格', '涨跌', '主力', '净']):
                    cols.append(c)
            
            if cols:
                df = df[cols].head(limit)
            else:
                df = df.head(limit)
            
            return df
            
        except Exception as e:
            print(f"获取资金流入榜失败: {e}")
            return pd.DataFrame()
    
    def get_top_outflow_stocks(self, limit: int = 20) -> pd.DataFrame:
        """
        获取主力资金流出前N名
        """
        try:
            import akshare as ak
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 找到主力净流入列并排序
            net_col = None
            for c in df.columns:
                if '主力' in c and '净' in c:
                    net_col = c
                    break
            
            if net_col:
                df[net_col] = pd.to_numeric(df[net_col], errors='coerce')
                df = df.nsmallest(limit, net_col)
            else:
                df = df.tail(limit)
            
            return df
            
        except Exception as e:
            print(f"获取资金流出榜失败: {e}")
            return pd.DataFrame()


# 全局实例
big_order_tracker = BigOrderTracker()


def get_buy_sell_pressure(code: str) -> Optional[BuySellPressure]:
    """便捷函数：获取买卖压力"""
    return big_order_tracker.get_buy_sell_pressure(code)


def get_fund_flow(code: str) -> Optional[FundFlowData]:
    """便捷函数：获取资金流向"""
    return big_order_tracker.get_fund_flow(code)


if __name__ == '__main__':
    # 测试
    print("\n测试买卖压力分析:")
    pressure = get_buy_sell_pressure('000592')
    if pressure:
        print(f"  {pressure.name}")
        print(f"  买盘: {pressure.bid_volume}手")
        print(f"  卖盘: {pressure.ask_volume}手")
        print(f"  买盘占比: {pressure.bid_ratio*100:.1f}%")
        print(f"  压力: {pressure.pressure}")
        print(f"  评分: {pressure.pressure_score}")
