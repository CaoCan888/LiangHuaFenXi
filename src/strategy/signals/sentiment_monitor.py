# -*- coding: utf-8 -*-
"""
市场情绪监控模块 (Market Sentiment Monitor)

功能：
1. 监控市场涨跌家数
2. 涨停/跌停统计
3. 热门板块追踪
4. 综合情绪评分
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


@dataclass
class MarketSentiment:
    """市场情绪数据"""
    up_count: int = 0           # 上涨家数
    down_count: int = 0         # 下跌家数
    flat_count: int = 0         # 平盘家数
    limit_up_count: int = 0     # 涨停家数
    limit_down_count: int = 0   # 跌停家数
    sentiment_score: float = 50 # 情绪评分 0-100
    sentiment_level: str = "中性"  # 情绪级别
    hot_sectors: List[str] = None  # 热门板块
    
    def __post_init__(self):
        if self.hot_sectors is None:
            self.hot_sectors = []


class SentimentMonitor:
    """市场情绪监控器"""
    
    def __init__(self):
        self.cache = None
        self.cache_time = None
        self.cache_ttl = 60  # 缓存60秒
        self.max_retries = 3
    
    def _request_with_retry(self, func, *args, **kwargs):
        """带重试的请求封装"""
        import time
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # 指数退避: 0.5s, 1s, 2s
                    time.sleep(wait_time)
                else:
                    print(f"请求失败(重试{self.max_retries}次): {e}")
                    return None
        return None
    
    def get_market_overview(self) -> MarketSentiment:
        """
        获取市场概览
        
        Returns:
            MarketSentiment: 市场情绪数据
        """
        # 检查缓存
        if self.cache and self.cache_time:
            if (datetime.now() - self.cache_time).seconds < self.cache_ttl:
                return self.cache
        
        sentiment = MarketSentiment()
        
        if not AKSHARE_AVAILABLE:
            return sentiment
        
        try:
            # 获取涨跌家数 (带重试)
            df = self._request_with_retry(ak.stock_zh_a_spot_em)
            
            if df is not None and not df.empty:
                # 计算涨跌分布
                changes = df['涨跌幅'].astype(float)
                sentiment.up_count = int((changes > 0).sum())
                sentiment.down_count = int((changes < 0).sum())
                sentiment.flat_count = int((changes == 0).sum())
                
                # 涨停跌停 (接近10%)
                sentiment.limit_up_count = int((changes >= 9.9).sum())
                sentiment.limit_down_count = int((changes <= -9.9).sum())
            
            # 计算情绪评分
            total = sentiment.up_count + sentiment.down_count + sentiment.flat_count
            if total > 0:
                up_ratio = sentiment.up_count / total
                limit_bonus = min(sentiment.limit_up_count * 0.5, 15)  # 涨停加分
                limit_penalty = min(sentiment.limit_down_count * 0.5, 15)  # 跌停减分
                
                sentiment.sentiment_score = up_ratio * 100 + limit_bonus - limit_penalty
                sentiment.sentiment_score = max(0, min(100, sentiment.sentiment_score))
            
            # 情绪级别
            if sentiment.sentiment_score >= 70:
                sentiment.sentiment_level = "极度乐观"
            elif sentiment.sentiment_score >= 55:
                sentiment.sentiment_level = "偏多"
            elif sentiment.sentiment_score >= 45:
                sentiment.sentiment_level = "中性"
            elif sentiment.sentiment_score >= 30:
                sentiment.sentiment_level = "偏空"
            else:
                sentiment.sentiment_level = "极度悲观"
            
            # 获取热门板块
            try:
                sector_df = ak.stock_board_concept_name_em()
                if sector_df is not None and not sector_df.empty:
                    # 按涨幅排序取前5
                    top_sectors = sector_df.nlargest(5, '涨跌幅')['板块名称'].tolist()
                    sentiment.hot_sectors = top_sectors
            except:
                pass
            
            # 更新缓存
            self.cache = sentiment
            self.cache_time = datetime.now()
            
        except Exception as e:
            print(f"获取市场情绪失败: {e}")
        
        return sentiment
    
    def get_sentiment_emoji(self, score: float) -> str:
        """获取情绪表情"""
        if score >= 70:
            return "🚀"
        elif score >= 55:
            return "📈"
        elif score >= 45:
            return "➡️"
        elif score >= 30:
            return "📉"
        else:
            return "💀"
    
    def format_report(self, sentiment: MarketSentiment) -> str:
        """格式化输出报告"""
        emoji = self.get_sentiment_emoji(sentiment.sentiment_score)
        
        lines = []
        lines.append(f"## {emoji} 市场情绪: {sentiment.sentiment_level} ({sentiment.sentiment_score:.0f}分)")
        lines.append("")
        lines.append(f"**涨跌分布**: ↑{sentiment.up_count} ↓{sentiment.down_count} ➡️{sentiment.flat_count}")
        lines.append(f"**涨停/跌停**: 🔴{sentiment.limit_up_count} / 🟢{sentiment.limit_down_count}")
        
        if sentiment.hot_sectors:
            lines.append("")
            lines.append("**热门板块**:")
            for i, sector in enumerate(sentiment.hot_sectors[:5], 1):
                lines.append(f"  {i}. {sector}")
        
        return "\n".join(lines)


# 全局实例
sentiment_monitor = SentimentMonitor()


def get_market_sentiment() -> MarketSentiment:
    """便捷函数：获取市场情绪"""
    return sentiment_monitor.get_market_overview()
