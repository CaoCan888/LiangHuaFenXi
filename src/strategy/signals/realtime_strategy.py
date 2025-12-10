# -*- coding: utf-8 -*-
"""
实时策略信号生成器
基于实时行情数据生成交易信号
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.data.collectors.realtime_service import get_realtime_quote, RealtimeQuote


class SignalType(Enum):
    """信号类型"""
    BREAKOUT_MA = "突破均线"
    BREAKOUT_HIGH = "突破前高"
    VOLUME_SURGE = "放量预警"
    NEAR_LIMIT_UP = "接近涨停"
    LIMIT_UP = "涨停"
    LIMIT_DOWN = "跌停"
    PRICE_ALERT = "价格预警"
    BUY_PRESSURE = "买盘强势"
    SELL_PRESSURE = "卖盘强势"


@dataclass
class RealtimeSignal:
    """实时信号"""
    code: str
    name: str
    signal_type: SignalType
    price: float
    change_pct: float
    message: str
    confidence: int  # 0-100
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%H:%M:%S'))
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'signal_type': self.signal_type.value,
            'price': self.price,
            'change_pct': self.change_pct,
            'message': self.message,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }


class RealtimeStrategy:
    """实时策略分析器"""
    
    def __init__(self):
        self.ma_cache = {}  # 缓存均线数据
    
    def set_ma_data(self, code: str, ma5: float, ma10: float, ma20: float):
        """设置均线数据（从日K线计算）"""
        self.ma_cache[code] = {'ma5': ma5, 'ma10': ma10, 'ma20': ma20}
    
    def check_breakout_signal(self, quote: RealtimeQuote) -> Optional[RealtimeSignal]:
        """
        检测突破信号
        - 突破5日均线
        - 突破10日均线
        - 突破20日均线
        """
        ma_data = self.ma_cache.get(quote.code)
        if not ma_data:
            return None
        
        price = quote.price
        
        # 检测突破20日均线（最重要）
        if price > ma_data['ma20'] and quote.pre_close <= ma_data['ma20']:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.BREAKOUT_MA,
                price=price,
                change_pct=quote.change_pct,
                message=f"突破20日均线 ({ma_data['ma20']:.2f})",
                confidence=75
            )
        
        # 检测突破5日均线
        if price > ma_data['ma5'] and quote.pre_close <= ma_data['ma5']:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.BREAKOUT_MA,
                price=price,
                change_pct=quote.change_pct,
                message=f"突破5日均线 ({ma_data['ma5']:.2f})",
                confidence=60
            )
        
        return None
    
    def check_volume_alert(self, quote: RealtimeQuote, avg_volume: float = None) -> Optional[RealtimeSignal]:
        """
        检测量能预警
        - 当前成交量超过5日均量的2倍
        """
        if not avg_volume:
            return None
        
        # 估算全天成交量（假设现在是10:30，已过1.5小时，全天4小时）
        now = datetime.now()
        market_open = datetime(now.year, now.month, now.day, 9, 30)
        market_close = datetime(now.year, now.month, now.day, 15, 0)
        
        if now < market_open or now > market_close:
            return None
        
        # 计算交易时间占比
        if now.hour < 11 or (now.hour == 11 and now.minute <= 30):
            # 上午
            elapsed = (now - market_open).seconds / 60
            total_minutes = 120  # 上午2小时
        else:
            # 下午
            elapsed = 120 + (now - datetime(now.year, now.month, now.day, 13, 0)).seconds / 60
            total_minutes = 240  # 全天4小时
        
        time_ratio = elapsed / 240 if elapsed < 240 else 1
        
        if time_ratio > 0:
            estimated_volume = quote.volume / time_ratio
            volume_ratio = estimated_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio >= 2:
                return RealtimeSignal(
                    code=quote.code,
                    name=quote.name,
                    signal_type=SignalType.VOLUME_SURGE,
                    price=quote.price,
                    change_pct=quote.change_pct,
                    message=f"放量预警！预估量比: {volume_ratio:.1f}",
                    confidence=int(min(90, 50 + volume_ratio * 10))
                )
        
        return None
    
    def check_limit_signal(self, quote: RealtimeQuote) -> Optional[RealtimeSignal]:
        """
        检测涨跌停信号
        """
        if quote.is_limit_up:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.LIMIT_UP,
                price=quote.price,
                change_pct=quote.change_pct,
                message="🔥 涨停！",
                confidence=100
            )
        
        if quote.is_limit_down:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.LIMIT_DOWN,
                price=quote.price,
                change_pct=quote.change_pct,
                message="⚠️ 跌停！",
                confidence=100
            )
        
        if quote.near_limit_up:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.NEAR_LIMIT_UP,
                price=quote.price,
                change_pct=quote.change_pct,
                message=f"接近涨停 ({quote.change_pct:.1f}%)",
                confidence=70
            )
        
        return None
    
    def check_pressure_signal(self, quote: RealtimeQuote) -> Optional[RealtimeSignal]:
        """
        检测买卖压力信号
        通过买卖盘挂单量判断
        """
        total_bid = sum(quote.bid_volumes)
        total_ask = sum(quote.ask_volumes)
        
        if total_bid + total_ask == 0:
            return None
        
        bid_ratio = total_bid / (total_bid + total_ask)
        
        if bid_ratio > 0.7:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.BUY_PRESSURE,
                price=quote.price,
                change_pct=quote.change_pct,
                message=f"买盘强势！买单占比: {bid_ratio*100:.0f}%",
                confidence=int(bid_ratio * 100)
            )
        
        if bid_ratio < 0.3:
            return RealtimeSignal(
                code=quote.code,
                name=quote.name,
                signal_type=SignalType.SELL_PRESSURE,
                price=quote.price,
                change_pct=quote.change_pct,
                message=f"卖盘强势！卖单占比: {(1-bid_ratio)*100:.0f}%",
                confidence=int((1-bid_ratio) * 100)
            )
        
        return None
    
    def generate_signals(self, code: str, avg_volume: float = None) -> List[RealtimeSignal]:
        """
        生成所有实时信号
        
        Args:
            code: 股票代码
            avg_volume: 5日平均成交量（手）
            
        Returns:
            信号列表
        """
        quote = get_realtime_quote(code)
        if not quote:
            return []
        
        signals = []
        
        # 检测各类信号
        signal = self.check_limit_signal(quote)
        if signal:
            signals.append(signal)
        
        signal = self.check_breakout_signal(quote)
        if signal:
            signals.append(signal)
        
        signal = self.check_volume_alert(quote, avg_volume)
        if signal:
            signals.append(signal)
        
        signal = self.check_pressure_signal(quote)
        if signal:
            signals.append(signal)
        
        return signals
    
    def scan_signals(self, codes: List[str]) -> List[RealtimeSignal]:
        """
        批量扫描信号
        
        Args:
            codes: 股票代码列表
            
        Returns:
            所有触发的信号
        """
        all_signals = []
        for code in codes:
            signals = self.generate_signals(code)
            all_signals.extend(signals)
        
        # 按置信度排序
        all_signals.sort(key=lambda x: x.confidence, reverse=True)
        return all_signals


# 全局实例
realtime_strategy = RealtimeStrategy()


def generate_realtime_signals(code: str, avg_volume: float = None) -> List[RealtimeSignal]:
    """便捷函数：生成实时信号"""
    return realtime_strategy.generate_signals(code, avg_volume)


if __name__ == '__main__':
    # 测试
    signals = generate_realtime_signals('000592')
    print(f"\n000592 实时信号:")
    for s in signals:
        print(f"  [{s.signal_type.value}] {s.message} (置信度: {s.confidence}%)")
