# -*- coding: utf-8 -*-
"""
胜率验证服务
验证AI分析建议的准确性
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import logging

from src.data.storage.db_manager import get_db_manager
from src.data.models import AnalysisHistory
from src.data.collectors import stock_collector

logger = logging.getLogger(__name__)


class WinRateVerifier:
    """胜率验证服务"""
    
    def __init__(self, verify_days: int = 5):
        """
        Args:
            verify_days: 验证周期（默认5个交易日后验证）
        """
        self.verify_days = verify_days
        self.db = get_db_manager()
    
    def verify_pending_records(self) -> Dict:
        """
        验证所有待验证的历史记录
        
        Returns:
            验证结果统计
        """
        session = self.db.get_session()
        stats = {"total": 0, "verified": 0, "correct": 0, "errors": 0}
        
        try:
            # 查找N天前未验证的记录
            cutoff_date = datetime.now() - timedelta(days=self.verify_days + 2)
            
            pending = session.query(AnalysisHistory).filter(
                AnalysisHistory.verified == False,
                AnalysisHistory.analysis_time <= cutoff_date
            ).limit(50).all()
            
            stats["total"] = len(pending)
            
            for record in pending:
                try:
                    result = self._verify_single(record, session)
                    if result is not None:
                        stats["verified"] += 1
                        if result:
                            stats["correct"] += 1
                except Exception as e:
                    logger.error(f"验证失败 {record.stock_code}: {e}")
                    stats["errors"] += 1
            
            session.commit()
            logger.info(f"胜率验证完成: {stats}")
            return stats
            
        finally:
            session.close()
    
    def _verify_single(self, record: AnalysisHistory, session) -> Optional[bool]:
        """
        验证单条记录
        
        Returns:
            True=判断正确, False=判断错误, None=无法验证
        """
        # 获取分析时的价格
        analysis_price = record.price
        if not analysis_price or analysis_price <= 0:
            return None
        
        # 计算N天后的日期
        target_date = record.analysis_date + timedelta(days=self.verify_days)
        
        # 获取N天后的价格
        try:
            df = stock_collector.get_daily_data(
                record.stock_code, 
                days=10,
                use_cache=False  # 强制刷新
            )
            
            if df is None or df.empty:
                return None
            
            # 找到目标日期之后最近的交易日收盘价
            df_after = df[df.index >= target_date.strftime('%Y-%m-%d')]
            if df_after.empty:
                return None
            
            price_after = df_after.iloc[0]['close']
            
        except Exception as e:
            logger.error(f"获取后续价格失败: {e}")
            return None
        
        # 计算收益率
        return_pct = (price_after / analysis_price - 1) * 100
        
        # 判断AI是否正确
        verdict = record.aggregated_signal or record.ai_verdict
        if not verdict:
            return None
        
        verdict_upper = verdict.upper()
        
        if "BUY" in verdict_upper:
            # AI说买入，后续涨了就是正确
            is_correct = return_pct > 0
        elif "SELL" in verdict_upper:
            # AI说卖出，后续跌了就是正确
            is_correct = return_pct < 0
        else:
            # HOLD，涨跌幅在±3%内算正确
            is_correct = abs(return_pct) < 3
        
        # 更新记录
        record.verified = True
        record.verified_at = datetime.now()
        record.price_after_5d = price_after
        record.actual_return_5d = return_pct
        record.verdict_correct = is_correct
        
        logger.info(f"验证 {record.stock_code}: {verdict} -> {return_pct:.2f}% -> {'✓' if is_correct else '✗'}")
        
        return is_correct
    
    def get_win_rate_stats(self, days: int = 30) -> Dict:
        """
        获取胜率统计
        
        Args:
            days: 统计最近N天的数据
            
        Returns:
            胜率统计结果
        """
        session = self.db.get_session()
        
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            records = session.query(AnalysisHistory).filter(
                AnalysisHistory.verified == True,
                AnalysisHistory.analysis_time >= cutoff
            ).all()
            
            if not records:
                return {
                    "total_verified": 0,
                    "win_rate": 0,
                    "buy_win_rate": 0,
                    "sell_win_rate": 0,
                    "avg_return": 0,
                    "message": "暂无验证数据"
                }
            
            total = len(records)
            correct = sum(1 for r in records if r.verdict_correct)
            
            # 分类统计
            buy_records = [r for r in records if r.aggregated_signal and 'BUY' in r.aggregated_signal.upper()]
            sell_records = [r for r in records if r.aggregated_signal and 'SELL' in r.aggregated_signal.upper()]
            
            buy_correct = sum(1 for r in buy_records if r.verdict_correct)
            sell_correct = sum(1 for r in sell_records if r.verdict_correct)
            
            # 平均收益
            returns = [r.actual_return_5d for r in records if r.actual_return_5d is not None]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            return {
                "total_verified": total,
                "win_rate": correct / total * 100 if total > 0 else 0,
                "buy_count": len(buy_records),
                "buy_win_rate": buy_correct / len(buy_records) * 100 if buy_records else 0,
                "sell_count": len(sell_records),
                "sell_win_rate": sell_correct / len(sell_records) * 100 if sell_records else 0,
                "avg_return": avg_return,
                "best_return": max(returns) if returns else 0,
                "worst_return": min(returns) if returns else 0
            }
            
        finally:
            session.close()


# 全局实例
win_rate_verifier = WinRateVerifier()
