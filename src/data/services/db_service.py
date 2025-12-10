# -*- coding: utf-8 -*-
"""
数据库缓存与分析历史服务
提供API数据缓存和AI分析历史记录功能
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd

from src.data.models import AnalysisHistory, DataCache, DailyPrice
from src.data.storage import get_db_manager


class DatabaseService:
    """数据库服务 - 缓存与历史记录"""
    
    def __init__(self):
        self.db = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库连接"""
        try:
            self.db = get_db_manager()
        except Exception as e:
            print(f"数据库连接失败: {e}")
    
    # ==================== 分析历史 ====================
    
    def save_analysis(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        change_pct: float,
        aggregated_signal: str,
        signal_confidence: float,
        buy_score: float,
        sell_score: float,
        hold_score: float,
        ai_response: str,
        ma_trend: str = "",
        macd_signal: str = "",
        rsi_value: float = 50.0,
        support_level: float = 0.0,
        resistance_level: float = 0.0
    ) -> bool:
        """保存分析历史记录"""
        if not self.db:
            return False
        
        try:
            session = self.db.get_session()
            
            record = AnalysisHistory(
                stock_code=stock_code,
                stock_name=stock_name,
                analysis_date=datetime.now().date(),
                analysis_time=datetime.now(),
                price=price,
                change_pct=change_pct,
                aggregated_signal=aggregated_signal,
                signal_confidence=signal_confidence,
                buy_score=buy_score,
                sell_score=sell_score,
                hold_score=hold_score,
                ai_full_response=ai_response,
                ma_trend=ma_trend,
                macd_signal_str=macd_signal,
                rsi_value=rsi_value,
                support_level=support_level,
                resistance_level=resistance_level
            )
            
            session.add(record)
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            print(f"保存分析历史失败: {e}")
            return False
    
    def get_analysis_history(
        self,
        stock_code: str,
        days: int = 30
    ) -> List[Dict]:
        """获取股票的分析历史"""
        if not self.db:
            return []
        
        try:
            session = self.db.get_session()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            records = session.query(AnalysisHistory).filter(
                AnalysisHistory.stock_code == stock_code,
                AnalysisHistory.analysis_time >= cutoff_date
            ).order_by(AnalysisHistory.analysis_time.desc()).all()
            
            session.close()
            
            return [
                {
                    'date': r.analysis_date,
                    'time': r.analysis_time,
                    'price': r.price,
                    'signal': r.aggregated_signal,
                    'confidence': r.signal_confidence,
                    'ai_response': r.ai_full_response
                }
                for r in records
            ]
            
        except Exception as e:
            print(f"获取分析历史失败: {e}")
            return []
    
    # ==================== 数据缓存 ====================
    
    def cache_daily_data(
        self,
        stock_code: str,
        df: pd.DataFrame,
        ttl_hours: int = 4
    ) -> bool:
        """缓存日K线数据"""
        if not self.db or df.empty:
            return False
        
        try:
            session = self.db.get_session()
            
            cache_key = f"daily_{stock_code}_{datetime.now().strftime('%Y%m%d')}"
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            # 转换DataFrame为JSON
            data_json = df.to_json(orient='records', date_format='iso')
            
            # 查找或创建
            existing = session.query(DataCache).filter(
                DataCache.cache_key == cache_key
            ).first()
            
            if existing:
                existing.data_json = data_json
                existing.expires_at = expires_at
                existing.updated_at = datetime.now()
            else:
                cache = DataCache(
                    cache_key=cache_key,
                    cache_type='daily_kline',
                    stock_code=stock_code,
                    data_json=data_json,
                    expires_at=expires_at
                )
                session.add(cache)
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            print(f"缓存数据失败: {e}")
            return False
    
    def get_cached_daily_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """获取缓存的日K线数据"""
        if not self.db:
            return None
        
        try:
            session = self.db.get_session()
            
            cache_key = f"daily_{stock_code}_{datetime.now().strftime('%Y%m%d')}"
            
            cache = session.query(DataCache).filter(
                DataCache.cache_key == cache_key,
                DataCache.expires_at > datetime.now()
            ).first()
            
            session.close()
            
            if cache and cache.data_json:
                df = pd.read_json(cache.data_json, orient='records')
                print(f"[缓存命中] {stock_code} 日K线数据")
                return df
            
            return None
            
        except Exception as e:
            print(f"获取缓存失败: {e}")
            return None
    
    def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        if not self.db:
            return 0
        
        try:
            session = self.db.get_session()
            
            count = session.query(DataCache).filter(
                DataCache.expires_at < datetime.now()
            ).delete()
            
            session.commit()
            session.close()
            
            print(f"清理过期缓存: {count}条")
            return count
            
        except Exception as e:
            print(f"清理缓存失败: {e}")
            return 0
    
    # ==================== 日线数据存储 ====================
    
    def save_daily_prices(self, stock_code: str, df: pd.DataFrame) -> bool:
        """保存日线数据到数据库 (upsert模式)"""
        if not self.db or df.empty:
            return False
        
        try:
            session = self.db.get_session()
            
            for _, row in df.iterrows():
                trade_date = row.get('date') or row.get('trade_date')
                if pd.isna(trade_date):
                    continue
                
                # 查找是否存在
                existing = session.query(DailyPrice).filter(
                    DailyPrice.stock_code == stock_code,
                    DailyPrice.trade_date == trade_date
                ).first()
                
                if existing:
                    # 更新
                    existing.open = row.get('open')
                    existing.high = row.get('high')
                    existing.low = row.get('low')
                    existing.close = row.get('close')
                    existing.volume = row.get('volume')
                    existing.amount = row.get('amount')
                else:
                    # 新增
                    price = DailyPrice(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        open=row.get('open'),
                        high=row.get('high'),
                        low=row.get('low'),
                        close=row.get('close'),
                        volume=row.get('volume'),
                        amount=row.get('amount')
                    )
                    session.add(price)
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            print(f"保存日线数据失败: {e}")
            return False
    
    def get_daily_prices(self, stock_code: str, days: int = 30) -> Optional[pd.DataFrame]:
        """从数据库获取日线数据"""
        if not self.db:
            return None
        
        try:
            session = self.db.get_session()
            
            cutoff_date = datetime.now().date() - timedelta(days=days)
            records = session.query(DailyPrice).filter(
                DailyPrice.stock_code == stock_code,
                DailyPrice.trade_date >= cutoff_date
            ).order_by(DailyPrice.trade_date).all()
            
            session.close()
            
            if records:
                data = [
                    {
                        'date': r.trade_date,
                        'open': r.open,
                        'high': r.high,
                        'low': r.low,
                        'close': r.close,
                        'volume': r.volume,
                        'amount': r.amount
                    }
                    for r in records
                ]
                return pd.DataFrame(data)
            
            return None
            
        except Exception as e:
            print(f"获取日线数据失败: {e}")
            return None


# 全局实例
db_service = DatabaseService()
