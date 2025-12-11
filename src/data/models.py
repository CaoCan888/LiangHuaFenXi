# -*- coding: utf-8 -*-
"""
Stock Analysis System - Data Models
SQLAlchemy数据模型定义
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Text, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Stock(Base):
    """股票基本信息表"""
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    exchange = Column(String(10), comment='交易所 SH/SZ')
    industry = Column(String(50), comment='所属行业')
    sector = Column(String(50), comment='所属板块')
    list_date = Column(Date, comment='上市日期')
    status = Column(String(20), default='active', comment='状态')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_stock_code', 'code'),
        {'comment': '股票基本信息表'}
    )


class DailyPrice(Base):
    """日线行情数据表"""
    __tablename__ = 'daily_prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, comment='收盘价')
    volume = Column(Float, comment='成交量')
    amount = Column(Float, comment='成交额')
    turnover = Column(Float, comment='换手率')
    pct_change = Column(Float, comment='涨跌幅')
    pre_close = Column(Float, comment='昨收价')
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_daily_stock_date', 'stock_code', 'trade_date', unique=True),
        Index('idx_daily_date', 'trade_date'),
        {'comment': '日线行情数据表'}
    )


class MinutePrice(Base):
    """分钟线行情数据表"""
    __tablename__ = 'minute_prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trade_time = Column(DateTime, nullable=False, comment='交易时间')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, comment='收盘价')
    volume = Column(Float, comment='成交量')
    amount = Column(Float, comment='成交额')
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_minute_stock_time', 'stock_code', 'trade_time', unique=True),
        {'comment': '分钟线行情数据表'}
    )


class FinancialData(Base):
    """财务数据表"""
    __tablename__ = 'financial_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    report_date = Column(Date, nullable=False, comment='报告期')
    report_type = Column(String(20), comment='报告类型')
    
    # 利润表指标
    revenue = Column(Float, comment='营业收入')
    net_profit = Column(Float, comment='净利润')
    gross_profit = Column(Float, comment='毛利润')
    operating_profit = Column(Float, comment='营业利润')
    
    # 资产负债表指标
    total_assets = Column(Float, comment='总资产')
    total_liabilities = Column(Float, comment='总负债')
    total_equity = Column(Float, comment='股东权益')
    
    # 现金流量表指标
    operating_cash_flow = Column(Float, comment='经营现金流')
    investing_cash_flow = Column(Float, comment='投资现金流')
    financing_cash_flow = Column(Float, comment='筹资现金流')
    
    # 财务比率
    roe = Column(Float, comment='净资产收益率ROE')
    roa = Column(Float, comment='总资产收益率ROA')
    eps = Column(Float, comment='每股收益EPS')
    bps = Column(Float, comment='每股净资产BPS')
    pe_ratio = Column(Float, comment='市盈率PE')
    pb_ratio = Column(Float, comment='市净率PB')
    debt_ratio = Column(Float, comment='资产负债率')
    current_ratio = Column(Float, comment='流动比率')
    quick_ratio = Column(Float, comment='速动比率')
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_financial_stock_date', 'stock_code', 'report_date', unique=True),
        {'comment': '财务数据表'}
    )


class TechnicalIndicator(Base):
    """技术指标数据表"""
    __tablename__ = 'technical_indicators'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    
    # 均线指标
    ma5 = Column(Float, comment='5日均线')
    ma10 = Column(Float, comment='10日均线')
    ma20 = Column(Float, comment='20日均线')
    ma60 = Column(Float, comment='60日均线')
    
    # MACD指标
    macd = Column(Float, comment='MACD')
    macd_signal = Column(Float, comment='MACD信号线')
    macd_hist = Column(Float, comment='MACD柱状图')
    
    # RSI指标
    rsi_6 = Column(Float, comment='6日RSI')
    rsi_12 = Column(Float, comment='12日RSI')
    rsi_14 = Column(Float, comment='14日RSI')
    
    # 布林带
    boll_upper = Column(Float, comment='布林带上轨')
    boll_middle = Column(Float, comment='布林带中轨')
    boll_lower = Column(Float, comment='布林带下轨')
    
    # KDJ指标
    kdj_k = Column(Float, comment='KDJ-K值')
    kdj_d = Column(Float, comment='KDJ-D值')
    kdj_j = Column(Float, comment='KDJ-J值')
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_tech_stock_date', 'stock_code', 'trade_date', unique=True),
        {'comment': '技术指标数据表'}
    )


class Alert(Base):
    """预警记录表"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    alert_type = Column(String(50), nullable=False, comment='预警类型')
    condition = Column(Text, comment='触发条件')
    message = Column(Text, comment='预警消息')
    is_triggered = Column(Boolean, default=False, comment='是否已触发')
    triggered_at = Column(DateTime, comment='触发时间')
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_alert_stock', 'stock_code'),
        {'comment': '预警记录表'}
    )


class BacktestResult(Base):
    """回测结果表"""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False, comment='策略名称')
    stock_code = Column(String(20), comment='股票代码')
    start_date = Column(Date, comment='开始日期')
    end_date = Column(Date, comment='结束日期')
    initial_capital = Column(Float, comment='初始资金')
    final_capital = Column(Float, comment='最终资金')
    total_return = Column(Float, comment='总收益率')
    annualized_return = Column(Float, comment='年化收益率')
    max_drawdown = Column(Float, comment='最大回撤')
    sharpe_ratio = Column(Float, comment='夏普比率')
    win_rate = Column(Float, comment='胜率')
    total_trades = Column(Integer, comment='总交易次数')
    parameters = Column(Text, comment='策略参数JSON')
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_backtest_strategy', 'strategy_name'),
        {'comment': '回测结果表'}
    )


class TradeRecord(Base):
    """交易记录表"""
    __tablename__ = 'trade_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, comment='回测ID')
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    trade_type = Column(String(10), comment='交易类型 BUY/SELL')
    price = Column(Float, comment='成交价格')
    quantity = Column(Integer, comment='成交数量')
    amount = Column(Float, comment='成交金额')
    commission = Column(Float, comment='手续费')
    profit = Column(Float, comment='盈亏')
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_trade_backtest', 'backtest_id'),
        {'comment': '交易记录表'}
    )


class AnalysisHistory(Base):
    """AI分析历史记录表"""
    __tablename__ = 'analysis_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    stock_name = Column(String(50), comment='股票名称')
    analysis_date = Column(Date, nullable=False, comment='分析日期')
    analysis_time = Column(DateTime, nullable=False, comment='分析时间')
    
    # 分析时的行情数据
    price = Column(Float, comment='当时价格')
    change_pct = Column(Float, comment='当时涨跌幅')
    
    # 信号聚合结果
    aggregated_signal = Column(String(10), comment='综合信号 BUY/SELL/HOLD')
    signal_confidence = Column(Float, comment='信号置信度')
    buy_score = Column(Float, comment='买入分数')
    sell_score = Column(Float, comment='卖出分数')
    hold_score = Column(Float, comment='持有分数')
    
    # AI分析结果
    ai_verdict = Column(String(50), comment='AI核心研判')
    ai_strategy = Column(Text, comment='AI交易策略')
    ai_stop_loss = Column(Float, comment='AI建议止损')
    ai_take_profit = Column(Float, comment='AI建议止盈')
    ai_position = Column(String(20), comment='AI仓位建议')
    ai_full_response = Column(Text, comment='AI完整回复')
    
    # 技术指标快照
    ma_trend = Column(String(50), comment='均线趋势')
    macd_signal_str = Column(String(20), comment='MACD信号')
    rsi_value = Column(Float, comment='RSI值')
    support_level = Column(Float, comment='支撑位')
    resistance_level = Column(Float, comment='压力位')
    
    # 胜率验证 (P0新增)
    verified = Column(Boolean, default=False, comment='是否已验证')
    verified_at = Column(DateTime, comment='验证时间')
    price_after_5d = Column(Float, comment='5日后价格')
    actual_return_5d = Column(Float, comment='5日实际收益率%')
    verdict_correct = Column(Boolean, comment='AI判断是否正确')
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_analysis_stock_date', 'stock_code', 'analysis_date'),
        Index('idx_analysis_time', 'analysis_time'),
        Index('idx_analysis_verified', 'verified'),
        {'comment': 'AI分析历史记录表'}
    )


class DataCache(Base):
    """API数据缓存表"""
    __tablename__ = 'data_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(100), unique=True, nullable=False, comment='缓存键')
    cache_type = Column(String(50), comment='缓存类型')
    stock_code = Column(String(20), comment='股票代码')
    data_json = Column(Text, comment='缓存的JSON数据')
    expires_at = Column(DateTime, comment='过期时间')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_cache_expires', 'expires_at'),
        {'comment': 'API数据缓存表'}
    )


class Watchlist(Base):
    """自选股列表"""
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    stock_name = Column(String(50), comment='股票名称')
    group_name = Column(String(50), default='默认', comment='分组名称')
    notes = Column(String(200), comment='备注')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    added_price = Column(Float, comment='加入时价格')
    added_at = Column(DateTime, default=datetime.now, comment='加入时间')
    
    __table_args__ = (
        Index('idx_watchlist_code', 'stock_code'),
        Index('idx_watchlist_group', 'group_name'),
        {'comment': '自选股列表'}
    )


class Position(Base):
    """持仓记录"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    stock_name = Column(String(50), comment='股票名称')
    
    # 持仓信息
    shares = Column(Integer, default=0, comment='持仓数量(股)')
    avg_cost = Column(Float, comment='持仓成本价')
    total_cost = Column(Float, comment='总成本')
    
    # 交易记录
    buy_date = Column(Date, comment='首次买入日期')
    last_trade_date = Column(Date, comment='最后交易日期')
    
    # 状态
    is_active = Column(Boolean, default=True, comment='是否持仓中')
    strategy_tag = Column(String(50), comment='策略标签 (如: 打板/趋势/底部)')
    notes = Column(String(500), comment='交易笔记')
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_position_code', 'stock_code'),
        Index('idx_position_active', 'is_active'),
        {'comment': '持仓记录表'}
    )
