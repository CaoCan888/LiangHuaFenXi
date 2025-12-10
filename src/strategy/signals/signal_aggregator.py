# -*- coding: utf-8 -*-
"""
信号聚合器 (Signal Aggregator)
整合多个策略的信号，通过加权投票输出最终决策

作用：
1. 解决多策略信号冲突问题
2. 提高信号可靠性
3. 输出带置信度的综合决策
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategySignal:
    """单个策略信号"""
    strategy_name: str       # 策略名称
    signal: SignalType       # 信号类型
    confidence: float        # 置信度 0-100
    reasons: List[str] = field(default_factory=list)   # 理由
    weight: float = 1.0      # 策略权重


@dataclass
class AggregatedSignal:
    """聚合后的最终信号"""
    final_signal: SignalType
    confidence: float
    buy_score: float
    sell_score: float
    hold_score: float
    contributing_signals: List[StrategySignal]
    summary: str


class SignalAggregator:
    """
    信号聚合器
    
    使用加权投票机制整合多个策略信号
    """
    
    # 策略默认权重配置
    DEFAULT_WEIGHTS = {
        'limit_chase': 1.2,        # 打板策略权重较高
        'momentum': 1.0,           # 动量策略
        'comprehensive': 1.0,      # 综合策略
        'technical_score': 0.8,    # 技术评分
        'chan': 0.9,               # 缠论策略
        'intraday_pattern': 1.1,   # 分时形态
        'ai_analysis': 1.5,        # AI分析权重最高
        'trading_advisor': 1.0,    # 交易建议
    }
    
    def __init__(self, custom_weights: Dict[str, float] = None):
        """
        初始化聚合器
        
        Args:
            custom_weights: 自定义策略权重
        """
        self.weights = self.DEFAULT_WEIGHTS.copy()
        if custom_weights:
            self.weights.update(custom_weights)
        
        self.signals: List[StrategySignal] = []
    
    def clear(self):
        """清空信号缓存"""
        self.signals = []
    
    def add_signal(
        self, 
        strategy_name: str, 
        signal: str, 
        confidence: float = 50,
        reasons: List[str] = None
    ):
        """
        添加一个策略信号
        
        Args:
            strategy_name: 策略名称
            signal: 信号类型 'BUY'/'SELL'/'HOLD'
            confidence: 置信度 0-100
            reasons: 信号理由
        """
        signal_type = SignalType[signal.upper()] if isinstance(signal, str) else signal
        weight = self.weights.get(strategy_name, 1.0)
        
        self.signals.append(StrategySignal(
            strategy_name=strategy_name,
            signal=signal_type,
            confidence=confidence,
            reasons=reasons or [],
            weight=weight
        ))
    
    def aggregate(self) -> AggregatedSignal:
        """
        聚合所有信号，输出最终决策
        
        Returns:
            AggregatedSignal: 聚合后的信号
        """
        if not self.signals:
            return AggregatedSignal(
                final_signal=SignalType.HOLD,
                confidence=0,
                buy_score=0,
                sell_score=0,
                hold_score=0,
                contributing_signals=[],
                summary="无策略信号输入"
            )
        
        # 计算加权得分
        buy_score = 0.0
        sell_score = 0.0
        hold_score = 0.0
        total_weight = 0.0
        
        for sig in self.signals:
            weighted_confidence = sig.confidence * sig.weight
            total_weight += sig.weight
            
            if sig.signal == SignalType.BUY:
                buy_score += weighted_confidence
            elif sig.signal == SignalType.SELL:
                sell_score += weighted_confidence
            else:
                hold_score += weighted_confidence
        
        # 归一化得分
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
            hold_score /= total_weight
        
        # 确定最终信号
        scores = {
            SignalType.BUY: buy_score,
            SignalType.SELL: sell_score,
            SignalType.HOLD: hold_score
        }
        final_signal = max(scores, key=scores.get)
        final_confidence = scores[final_signal]
        
        # 生成摘要
        summary = self._generate_summary(final_signal, buy_score, sell_score, hold_score)
        
        return AggregatedSignal(
            final_signal=final_signal,
            confidence=final_confidence,
            buy_score=buy_score,
            sell_score=sell_score,
            hold_score=hold_score,
            contributing_signals=self.signals.copy(),
            summary=summary
        )
    
    def _generate_summary(
        self, 
        signal: SignalType, 
        buy_score: float, 
        sell_score: float, 
        hold_score: float
    ) -> str:
        """生成决策摘要"""
        signal_map = {
            SignalType.BUY: "买入",
            SignalType.SELL: "卖出",
            SignalType.HOLD: "观望"
        }
        
        # 信号强度判断
        max_score = max(buy_score, sell_score, hold_score)
        if max_score >= 70:
            strength = "强"
        elif max_score >= 50:
            strength = "中等"
        else:
            strength = "弱"
        
        # 一致性判断
        scores_sorted = sorted([buy_score, sell_score, hold_score], reverse=True)
        if scores_sorted[0] - scores_sorted[1] < 10:
            consensus = "存在分歧"
        else:
            consensus = "信号一致"
        
        return f"{strength}{signal_map[signal]}信号 ({consensus}) | 买:{buy_score:.0f} 卖:{sell_score:.0f} 持:{hold_score:.0f}"
    
    def get_decision_emoji(self, signal: SignalType) -> str:
        """获取决策表情"""
        return {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴",
            SignalType.HOLD: "🟡"
        }.get(signal, "⚪")
    
    def format_report(self, result: AggregatedSignal) -> str:
        """格式化输出报告"""
        lines = []
        lines.append(f"## {self.get_decision_emoji(result.final_signal)} 综合决策: {result.final_signal.value}")
        lines.append(f"**置信度**: {result.confidence:.0f}%")
        lines.append(f"**摘要**: {result.summary}")
        lines.append("")
        lines.append("### 信号来源")
        
        for sig in result.contributing_signals:
            emoji = self.get_decision_emoji(sig.signal)
            lines.append(f"- {emoji} **{sig.strategy_name}**: {sig.signal.value} ({sig.confidence:.0f}%, 权重{sig.weight:.1f})")
            for reason in sig.reasons[:2]:  # 最多显示2条理由
                lines.append(f"  - {reason}")
        
        return "\n".join(lines)


# 全局实例
signal_aggregator = SignalAggregator()


def aggregate_signals(signals: List[Dict[str, Any]]) -> AggregatedSignal:
    """
    便捷函数：聚合多个信号
    
    Args:
        signals: 信号列表，每个元素为 {'strategy': 'xxx', 'signal': 'BUY', 'confidence': 60, 'reasons': [...]}
        
    Returns:
        AggregatedSignal
    """
    agg = SignalAggregator()
    for sig in signals:
        agg.add_signal(
            strategy_name=sig.get('strategy', 'unknown'),
            signal=sig.get('signal', 'HOLD'),
            confidence=sig.get('confidence', 50),
            reasons=sig.get('reasons', [])
        )
    return agg.aggregate()
