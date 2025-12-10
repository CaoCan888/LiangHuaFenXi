# -*- coding: utf-8 -*-
"""
Stock Analysis System - Helper Functions
通用辅助函数
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np


def ensure_dir(path: str) -> str:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def format_date(date: Union[str, datetime], fmt: str = "%Y-%m-%d") -> str:
    """
    格式化日期
    
    Args:
        date: 日期对象或字符串
        fmt: 目标格式
        
    Returns:
        格式化后的日期字符串
    """
    if isinstance(date, str):
        # 尝试解析常见格式
        for parse_fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
            try:
                date = datetime.strptime(date, parse_fmt)
                break
            except ValueError:
                continue
    
    if isinstance(date, datetime):
        return date.strftime(fmt)
    return str(date)


def parse_date(date_str: str) -> datetime:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        
    Returns:
        datetime对象
    """
    formats = ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}")


def get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """
    获取交易日期列表(简化版，排除周末)
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        交易日期列表
    """
    start = parse_date(start_date)
    end = parse_date(end_date)
    
    dates = []
    current = start
    while current <= end:
        # 排除周末
        if current.weekday() < 5:
            dates.append(format_date(current))
        current += timedelta(days=1)
    
    return dates


def calculate_returns(prices: pd.Series) -> pd.Series:
    """
    计算收益率
    
    Args:
        prices: 价格序列
        
    Returns:
        收益率序列
    """
    return prices.pct_change()


def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    计算累计收益率
    
    Args:
        returns: 收益率序列
        
    Returns:
        累计收益率序列
    """
    return (1 + returns).cumprod() - 1


def calculate_annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算年化收益率
    
    Args:
        returns: 收益率序列
        periods_per_year: 每年交易日数
        
    Returns:
        年化收益率
    """
    total_return = (1 + returns).prod() - 1
    n_periods = len(returns)
    return (1 + total_return) ** (periods_per_year / n_periods) - 1


def calculate_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算年化波动率
    
    Args:
        returns: 收益率序列
        periods_per_year: 每年交易日数
        
    Returns:
        年化波动率
    """
    return returns.std() * np.sqrt(periods_per_year)


def calculate_sharpe_ratio(
    returns: pd.Series, 
    risk_free_rate: float = 0.03,
    periods_per_year: int = 252
) -> float:
    """
    计算夏普比率
    
    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率(年化)
        periods_per_year: 每年交易日数
        
    Returns:
        夏普比率
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0
    
    excess_returns = returns - risk_free_rate / periods_per_year
    std = excess_returns.std()
    
    if std == 0 or pd.isna(std):
        return 0.0
    
    return np.sqrt(periods_per_year) * excess_returns.mean() / std


def calculate_max_drawdown(prices: pd.Series) -> Dict[str, Any]:
    """
    计算最大回撤
    
    Args:
        prices: 价格序列
        
    Returns:
        包含最大回撤相关信息的字典
    """
    # 处理空数据或NaN
    prices = prices.dropna()
    
    # 边界情况处理
    if len(prices) < 2:
        return {
            "max_drawdown": 0,
            "start_date": None,
            "end_date": None,
            "drawdown_series": pd.Series()
        }
    
    try:
        # 累计最高点
        cummax = prices.cummax()
        
        # 避免除以零
        cummax = cummax.replace(0, np.nan)
        
        # 回撤
        drawdown = (prices - cummax) / cummax
        drawdown = drawdown.replace([np.inf, -np.inf], 0).fillna(0)
        
        # 检查drawdown是否为空
        if drawdown.empty or len(drawdown) == 0:
            return {
                "max_drawdown": 0,
                "start_date": None,
                "end_date": None,
                "drawdown_series": pd.Series()
            }
        
        # 最大回撤
        max_drawdown = drawdown.min()
        
        # 安全获取索引
        try:
            end_idx = drawdown.idxmin()
            # 获取结束点之前的数据来找开始点
            prices_before_end = prices.loc[:end_idx] if end_idx is not None else prices
            start_idx = prices_before_end.idxmax() if len(prices_before_end) > 0 else None
        except (ValueError, KeyError, TypeError):
            end_idx = None
            start_idx = None
        
        return {
            "max_drawdown": abs(max_drawdown) if pd.notna(max_drawdown) else 0,
            "start_date": start_idx,
            "end_date": end_idx,
            "drawdown_series": drawdown
        }
    except Exception as e:
        # 任何异常都返回默认值
        return {
            "max_drawdown": 0,
            "start_date": None,
            "end_date": None,
            "drawdown_series": pd.Series()
        }


def format_number(value: float, decimals: int = 2, percentage: bool = False) -> str:
    """
    格式化数字
    
    Args:
        value: 数值
        decimals: 小数位数
        percentage: 是否转换为百分比
        
    Returns:
        格式化后的字符串
    """
    if percentage:
        return f"{value * 100:.{decimals}f}%"
    return f"{value:.{decimals}f}"


def format_currency(value: float, currency: str = "¥") -> str:
    """
    格式化货币
    
    Args:
        value: 金额
        currency: 货币符号
        
    Returns:
        格式化后的货币字符串
    """
    if abs(value) >= 100000000:
        return f"{currency}{value / 100000000:.2f}亿"
    elif abs(value) >= 10000:
        return f"{currency}{value / 10000:.2f}万"
    else:
        return f"{currency}{value:.2f}"


def to_json(data: Any, indent: int = 2) -> str:
    """
    转换为JSON字符串
    
    Args:
        data: 数据
        indent: 缩进
        
    Returns:
        JSON字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=indent, default=str)


def from_json(json_str: str) -> Any:
    """
    解析JSON字符串
    
    Args:
        json_str: JSON字符串
        
    Returns:
        解析后的数据
    """
    return json.loads(json_str)


def validate_stock_code(code: str) -> bool:
    """
    验证股票代码格式
    
    Args:
        code: 股票代码
        
    Returns:
        是否有效
    """
    if not code:
        return False
    
    # A股代码格式: 6位数字
    if len(code) == 6 and code.isdigit():
        # 上证: 60开头
        # 深证: 00开头
        # 创业板: 30开头
        # 科创板: 68开头
        if code.startswith(('60', '00', '30', '68')):
            return True
    
    return False


def get_stock_exchange(code: str) -> str:
    """
    获取股票所属交易所
    
    Args:
        code: 股票代码
        
    Returns:
        交易所代码 (SH/SZ)
    """
    if code.startswith(('60', '68')):
        return "SH"
    elif code.startswith(('00', '30')):
        return "SZ"
    return "UNKNOWN"


def normalize_stock_code(code: str) -> str:
    """
    标准化股票代码
    
    Args:
        code: 原始股票代码
        
    Returns:
        标准化后的股票代码 (如: SH.600000)
    """
    # 移除可能的前缀
    code = code.replace("SH.", "").replace("SZ.", "").replace("sh", "").replace("sz", "")
    code = code.strip()
    
    if len(code) == 6 and code.isdigit():
        exchange = get_stock_exchange(code)
        return f"{exchange}.{code}"
    
    return code
