# -*- coding: utf-8 -*-
"""
板块联动分析模块 (Sector Correlation Analyzer)

功能：
1. 识别个股所属板块
2. 统计同板块涨停股数量
3. 计算板块联动度
4. 辅助判断连板成功率
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

# 尝试导入akshare获取板块数据
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


@dataclass
class SectorInfo:
    """板块信息"""
    sector_name: str           # 板块名称
    sector_code: str           # 板块代码
    limit_up_count: int        # 板块内涨停数
    total_stocks: int          # 板块总股票数
    correlation_score: float   # 联动度评分 0-100


@dataclass
class SectorAnalysisResult:
    """板块分析结果"""
    stock_code: str
    stock_name: str
    sectors: List[SectorInfo]           # 所属板块列表
    best_sector: Optional[SectorInfo]   # 最强板块
    sector_strength: str                # 板块强度描述
    limit_continuation_boost: float     # 连板概率加成


class SectorCorrelationAnalyzer:
    """板块联动分析器"""
    
    def __init__(self):
        self.sector_cache = {}
        self.limit_up_cache = {}
        self.cache_date = None
    
    def _refresh_cache_if_needed(self):
        """刷新缓存（每日更新）"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.cache_date != today:
            self.sector_cache = {}
            self.limit_up_cache = {}
            self.cache_date = today
    
    def get_stock_sectors(self, stock_code: str) -> List[str]:
        """
        获取个股所属板块
        
        Args:
            stock_code: 股票代码
            
        Returns:
            板块名称列表
        """
        self._refresh_cache_if_needed()
        
        if stock_code in self.sector_cache:
            return self.sector_cache[stock_code]
        
        sectors = []
        
        if AKSHARE_AVAILABLE:
            try:
                # 获取概念板块
                code = stock_code.split('.')[-1] if '.' in stock_code else stock_code
                df = ak.stock_board_concept_name_em()
                
                # 简化处理：基于股票代码前缀判断行业
                if code.startswith('300') or code.startswith('301'):
                    sectors.append('创业板')
                elif code.startswith('688'):
                    sectors.append('科创板')
                elif code.startswith('00'):
                    sectors.append('深证主板')
                elif code.startswith('60'):
                    sectors.append('沪证主板')
                
                # 更多板块可以通过API获取
                # 这里为了性能采用简化逻辑
                
            except Exception as e:
                print(f"获取板块信息失败: {e}")
        
        self.sector_cache[stock_code] = sectors
        return sectors
    
    def get_sector_limit_up_count(self, sector_name: str, date: str = None) -> int:
        """
        获取板块内涨停股数量
        
        Args:
            sector_name: 板块名称
            date: 日期，默认今天
            
        Returns:
            涨停股数量
        """
        if not AKSHARE_AVAILABLE:
            return 0
            
        try:
            # 获取今日涨停股
            df = ak.stock_zt_pool_em(date=date) if date else ak.stock_zt_pool_em()
            
            if df.empty:
                return 0
            
            # 简化：统计总涨停数作为市场热度参考
            return len(df)
            
        except Exception as e:
            print(f"获取涨停数据失败: {e}")
            return 0
    
    def analyze(self, stock_code: str, stock_name: str = "") -> SectorAnalysisResult:
        """
        分析个股的板块联动情况
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            SectorAnalysisResult
        """
        sectors_info = []
        
        # 获取所属板块
        sector_names = self.get_stock_sectors(stock_code)
        
        # 获取市场整体涨停数
        total_limit_ups = self.get_sector_limit_up_count("")
        
        # 构建板块信息
        for name in sector_names:
            info = SectorInfo(
                sector_name=name,
                sector_code="",
                limit_up_count=total_limit_ups,  # 简化处理
                total_stocks=0,
                correlation_score=min(total_limit_ups * 2, 100)  # 涨停数越多，联动度越高
            )
            sectors_info.append(info)
        
        # 确定最强板块
        best_sector = max(sectors_info, key=lambda x: x.correlation_score) if sectors_info else None
        
        # 计算板块强度
        if total_limit_ups >= 50:
            strength = "极强 (涨停潮)"
            boost = 0.15
        elif total_limit_ups >= 30:
            strength = "较强"
            boost = 0.10
        elif total_limit_ups >= 15:
            strength = "一般"
            boost = 0.05
        else:
            strength = "较弱"
            boost = 0.0
        
        return SectorAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            sectors=sectors_info,
            best_sector=best_sector,
            sector_strength=strength,
            limit_continuation_boost=boost
        )
    
    def get_continuation_probability(self, base_prob: float, stock_code: str) -> Tuple[float, str]:
        """
        根据板块联动度调整连板概率
        
        Args:
            base_prob: 基础连板概率
            stock_code: 股票代码
            
        Returns:
            (调整后概率, 说明)
        """
        result = self.analyze(stock_code)
        adjusted_prob = min(base_prob + result.limit_continuation_boost, 1.0)
        
        reason = f"板块强度{result.sector_strength}，连板概率加成{result.limit_continuation_boost*100:.0f}%"
        
        return adjusted_prob, reason
    
    def format_report(self, result: SectorAnalysisResult) -> str:
        """格式化输出报告"""
        lines = []
        lines.append(f"## 📊 板块联动分析: {result.stock_name} ({result.stock_code})")
        lines.append("")
        lines.append(f"**板块强度**: {result.sector_strength}")
        lines.append(f"**连板加成**: +{result.limit_continuation_boost*100:.0f}%")
        lines.append("")
        
        if result.sectors:
            lines.append("### 所属板块")
            for s in result.sectors:
                lines.append(f"- {s.sector_name} (联动度: {s.correlation_score:.0f})")
        
        return "\n".join(lines)


# 全局实例
sector_analyzer = SectorCorrelationAnalyzer()


def analyze_sector_correlation(stock_code: str, stock_name: str = "") -> SectorAnalysisResult:
    """便捷函数：分析板块联动"""
    return sector_analyzer.analyze(stock_code, stock_name)
