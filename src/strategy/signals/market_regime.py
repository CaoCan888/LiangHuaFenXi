# -*- coding: utf-8 -*-
"""
市场环境判断和动态权重调整
根据大盘状态动态调整策略权重
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """市场状态"""
    BULL = "牛市"      # 涨停多，跌停少，大盘上涨
    BEAR = "熊市"      # 跌停多，涨停少，大盘下跌
    VOLATILE = "震荡"  # 涨跌停都有，方向不明
    NEUTRAL = "中性"   # 涨跌停都少，市场平淡


@dataclass
class MarketStatus:
    """市场状态数据"""
    regime: MarketRegime
    limit_up_count: int = 0      # 涨停家数
    limit_down_count: int = 0    # 跌停家数
    up_count: int = 0            # 上涨家数
    down_count: int = 0          # 下跌家数
    index_change_pct: float = 0  # 大盘涨跌幅
    sentiment_score: float = 50  # 市场情绪得分 (0-100)
    
    @property
    def regime_description(self) -> str:
        """获取市场状态描述"""
        if self.regime == MarketRegime.BULL:
            return f"🟢 牛市氛围：涨停{self.limit_up_count}家，情绪高涨"
        elif self.regime == MarketRegime.BEAR:
            return f"🔴 熊市氛围：跌停{self.limit_down_count}家，注意风险"
        elif self.regime == MarketRegime.VOLATILE:
            return f"🟡 震荡市：多空分歧，控制仓位"
        else:
            return f"⚪ 中性市场：观望为主"


class MarketRegimeDetector:
    """市场环境判断器"""
    
    def __init__(self):
        self.current_status: Optional[MarketStatus] = None
    
    def detect(self, sentiment_data: Dict = None) -> MarketStatus:
        """
        检测当前市场状态
        
        Args:
            sentiment_data: 市场情绪数据 (来自sentiment_monitor)
            
        Returns:
            MarketStatus: 市场状态
        """
        if not sentiment_data:
            # 尝试从sentiment_monitor获取
            try:
                from src.strategy.signals.sentiment_monitor import sentiment_monitor
                sentiment_data = sentiment_monitor.get_market_sentiment()
            except Exception as e:
                logger.warning(f"获取市场情绪失败: {e}")
                return MarketStatus(regime=MarketRegime.NEUTRAL)
        
        # 提取数据
        limit_up = sentiment_data.get('limit_up_count', 0)
        limit_down = sentiment_data.get('limit_down_count', 0)
        up_count = sentiment_data.get('up_count', 0)
        down_count = sentiment_data.get('down_count', 0)
        
        # 计算情绪得分
        total = up_count + down_count
        sentiment_score = (up_count / total * 100) if total > 0 else 50
        
        # 判断市场状态
        if limit_up >= 50 and limit_down < 10:
            regime = MarketRegime.BULL
        elif limit_down >= 20 and limit_up < 20:
            regime = MarketRegime.BEAR
        elif limit_up >= 30 or limit_down >= 10:
            regime = MarketRegime.VOLATILE
        else:
            regime = MarketRegime.NEUTRAL
        
        self.current_status = MarketStatus(
            regime=regime,
            limit_up_count=limit_up,
            limit_down_count=limit_down,
            up_count=up_count,
            down_count=down_count,
            sentiment_score=sentiment_score
        )
        
        return self.current_status


class DynamicWeightManager:
    """动态权重管理器"""
    
    # 基础权重
    BASE_WEIGHTS = {
        'technical_score': 1.0,
        'limit_chase': 1.2,
        'intraday': 1.0,
        'realtime': 1.0,
        'risk_control': 0.8,
        'ai_analysis': 1.5,
        'momentum': 1.0,
        'chan': 0.8,
    }
    
    # 不同市场状态下的权重调整系数
    REGIME_ADJUSTMENTS = {
        MarketRegime.BULL: {
            'limit_chase': 1.5,    # 牛市打板策略加权
            'momentum': 1.3,       # 动量策略加权
            'risk_control': 0.6,   # 风控降权
            'ai_analysis': 1.2,
        },
        MarketRegime.BEAR: {
            'limit_chase': 0.5,    # 熊市打板降权
            'momentum': 0.7,
            'risk_control': 1.5,   # 风控加权
            'technical_score': 1.3, # 技术面加权(超跌反弹)
            'ai_analysis': 1.0,
        },
        MarketRegime.VOLATILE: {
            'intraday': 1.3,       # 震荡市日内策略加权
            'risk_control': 1.2,
            'limit_chase': 0.8,
        },
        MarketRegime.NEUTRAL: {
            # 中性市场使用基础权重
        }
    }
    
    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.current_weights = self.BASE_WEIGHTS.copy()
    
    def get_adjusted_weights(self, regime: MarketRegime = None) -> Dict[str, float]:
        """
        获取调整后的策略权重
        
        Args:
            regime: 市场状态，不传则自动检测
            
        Returns:
            调整后的权重字典
        """
        if regime is None:
            status = self.regime_detector.detect()
            regime = status.regime
        
        # 获取调整系数
        adjustments = self.REGIME_ADJUSTMENTS.get(regime, {})
        
        # 应用调整
        adjusted = self.BASE_WEIGHTS.copy()
        for strategy, multiplier in adjustments.items():
            if strategy in adjusted:
                adjusted[strategy] = self.BASE_WEIGHTS[strategy] * multiplier
        
        self.current_weights = adjusted
        
        logger.info(f"市场状态: {regime.value}, 权重已调整")
        return adjusted
    
    def get_weight_explanation(self) -> str:
        """获取当前权重解释"""
        status = self.regime_detector.current_status
        if not status:
            return "权重未调整"
        
        regime = status.regime
        lines = [f"📊 当前市场: {regime.value}"]
        
        if regime == MarketRegime.BULL:
            lines.append("- 打板/动量策略权重提升")
            lines.append("- 风控权重降低")
        elif regime == MarketRegime.BEAR:
            lines.append("- 打板/动量策略权重降低")
            lines.append("- 技术面/风控权重提升")
        elif regime == MarketRegime.VOLATILE:
            lines.append("- 日内策略权重提升")
            lines.append("- 控制仓位，谨慎操作")
        
        return "\n".join(lines)


# 全局实例
market_regime_detector = MarketRegimeDetector()
dynamic_weight_manager = DynamicWeightManager()
