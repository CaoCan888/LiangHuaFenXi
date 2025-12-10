# -*- coding: utf-8 -*-
"""
Stock Analysis System - Database Manager
数据库操作管理器
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.settings import settings
from src.data.models import Base, Stock, DailyPrice, FinancialData, TechnicalIndicator, Alert, BacktestResult, TradeRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, connection_string: str = None):
        """
        初始化数据库连接
        
        Args:
            connection_string: 数据库连接字符串，默认使用配置文件中的设置
        """
        self.connection_string = connection_string or settings.database.connection_string
        self.engine = None
        self.Session = None
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def init_tables(self):
        """初始化数据库表"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.Session()
    
    # ==================== 股票基本信息操作 ====================
    
    def save_stock(self, code: str, name: str, exchange: str = None, **kwargs) -> Stock:
        """
        保存股票基本信息
        
        Args:
            code: 股票代码
            name: 股票名称
            exchange: 交易所
            **kwargs: 其他字段
            
        Returns:
            Stock对象
        """
        session = self.get_session()
        try:
            stock = session.query(Stock).filter(Stock.code == code).first()
            if stock:
                # 更新
                stock.name = name
                stock.exchange = exchange
                for key, value in kwargs.items():
                    if hasattr(stock, key):
                        setattr(stock, key, value)
            else:
                # 新增
                stock = Stock(code=code, name=name, exchange=exchange, **kwargs)
                session.add(stock)
            
            session.commit()
            logger.debug(f"保存股票信息: {code} - {name}")
            return stock
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"保存股票信息失败: {e}")
            raise
        finally:
            session.close()
    
    def get_stock(self, code: str) -> Optional[Stock]:
        """
        获取股票信息
        
        Args:
            code: 股票代码
            
        Returns:
            Stock对象或None
        """
        session = self.get_session()
        try:
            return session.query(Stock).filter(Stock.code == code).first()
        finally:
            session.close()
    
    def get_all_stocks(self) -> List[Stock]:
        """获取所有股票"""
        session = self.get_session()
        try:
            return session.query(Stock).all()
        finally:
            session.close()
    
    # ==================== 日线数据操作 ====================
    
    def save_daily_prices(self, stock_code: str, data: pd.DataFrame):
        """
        批量保存日线数据
        
        Args:
            stock_code: 股票代码
            data: 包含日线数据的DataFrame
        """
        session = self.get_session()
        try:
            for _, row in data.iterrows():
                trade_date = row.get('trade_date') or row.get('date')
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                
                # 检查是否存在
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
                    existing.turnover = row.get('turnover')
                    existing.pct_change = row.get('pct_change')
                    existing.pre_close = row.get('pre_close')
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
                        amount=row.get('amount'),
                        turnover=row.get('turnover'),
                        pct_change=row.get('pct_change'),
                        pre_close=row.get('pre_close')
                    )
                    session.add(price)
            
            session.commit()
            logger.info(f"保存{stock_code}日线数据 {len(data)}条")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"保存日线数据失败: {e}")
            raise
        finally:
            session.close()
    
    def get_daily_prices(
        self, 
        stock_code: str, 
        start_date: date = None, 
        end_date: date = None
    ) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            日线数据DataFrame
        """
        session = self.get_session()
        try:
            query = session.query(DailyPrice).filter(DailyPrice.stock_code == stock_code)
            
            if start_date:
                query = query.filter(DailyPrice.trade_date >= start_date)
            if end_date:
                query = query.filter(DailyPrice.trade_date <= end_date)
            
            query = query.order_by(DailyPrice.trade_date)
            
            records = query.all()
            
            if not records:
                return pd.DataFrame()
            
            data = [{
                'trade_date': r.trade_date,
                'open': r.open,
                'high': r.high,
                'low': r.low,
                'close': r.close,
                'volume': r.volume,
                'amount': r.amount,
                'turnover': r.turnover,
                'pct_change': r.pct_change,
                'pre_close': r.pre_close
            } for r in records]
            
            df = pd.DataFrame(data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            
            return df
        finally:
            session.close()
    
    # ==================== 技术指标操作 ====================
    
    def save_technical_indicators(self, stock_code: str, data: pd.DataFrame):
        """
        保存技术指标数据
        
        Args:
            stock_code: 股票代码
            data: 技术指标DataFrame
        """
        session = self.get_session()
        try:
            for idx, row in data.iterrows():
                trade_date = idx if isinstance(idx, date) else idx.date()
                
                existing = session.query(TechnicalIndicator).filter(
                    TechnicalIndicator.stock_code == stock_code,
                    TechnicalIndicator.trade_date == trade_date
                ).first()
                
                indicator_data = {
                    'ma5': row.get('ma5'),
                    'ma10': row.get('ma10'),
                    'ma20': row.get('ma20'),
                    'ma60': row.get('ma60'),
                    'macd': row.get('macd'),
                    'macd_signal': row.get('macd_signal'),
                    'macd_hist': row.get('macd_hist'),
                    'rsi_6': row.get('rsi_6'),
                    'rsi_12': row.get('rsi_12'),
                    'rsi_14': row.get('rsi_14'),
                    'boll_upper': row.get('boll_upper'),
                    'boll_middle': row.get('boll_middle'),
                    'boll_lower': row.get('boll_lower'),
                    'kdj_k': row.get('kdj_k'),
                    'kdj_d': row.get('kdj_d'),
                    'kdj_j': row.get('kdj_j')
                }
                
                if existing:
                    for key, value in indicator_data.items():
                        setattr(existing, key, value)
                else:
                    indicator = TechnicalIndicator(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        **indicator_data
                    )
                    session.add(indicator)
            
            session.commit()
            logger.info(f"保存{stock_code}技术指标 {len(data)}条")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"保存技术指标失败: {e}")
            raise
        finally:
            session.close()
    
    # ==================== 回测结果操作 ====================
    
    def save_backtest_result(self, result: Dict[str, Any]) -> int:
        """
        保存回测结果
        
        Args:
            result: 回测结果字典
            
        Returns:
            回测结果ID
        """
        session = self.get_session()
        try:
            backtest = BacktestResult(**result)
            session.add(backtest)
            session.commit()
            logger.info(f"保存回测结果: {result.get('strategy_name')}")
            return backtest.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"保存回测结果失败: {e}")
            raise
        finally:
            session.close()
    
    def execute_sql(self, sql: str) -> pd.DataFrame:
        """
        执行原生SQL查询
        
        Args:
            sql: SQL语句
            
        Returns:
            查询结果DataFrame
        """
        try:
            return pd.read_sql(sql, self.engine)
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接已关闭")


# 创建全局数据库管理器实例
db_manager = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
