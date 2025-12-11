# -*- coding: utf-8 -*-
"""
A股股票类型识别工具
根据股票代码判断板块类型和涨跌幅限制
"""

from enum import Enum
from typing import Tuple
from dataclasses import dataclass


class StockBoard(Enum):
    """A股板块类型"""
    MAIN_SH = "沪市主板"      # 60xxxx
    MAIN_SZ = "深市主板"      # 00xxxx
    CHINEXT = "创业板"        # 30xxxx (20%涨跌幅)
    STAR = "科创板"           # 688xxx (20%涨跌幅)
    BSE = "北交所"            # 8xxxxx, 4xxxxx (30%涨跌幅)
    ST = "ST/*ST"             # 5%涨跌幅
    UNKNOWN = "未知"


@dataclass
class StockInfo:
    """股票信息"""
    code: str
    board: StockBoard
    limit_up_pct: float    # 涨停幅度 (如 0.10 表示 10%)
    limit_down_pct: float  # 跌停幅度
    is_st: bool = False
    is_new_stock: bool = False  # 新股首日无涨跌幅限制


def get_stock_board(code: str) -> StockBoard:
    """
    根据股票代码判断板块
    
    Args:
        code: 股票代码 (如 "000001", "300750", "688001")
        
    Returns:
        StockBoard: 板块类型
    """
    # 清理代码格式
    code = code.replace("SH.", "").replace("SZ.", "").replace("BJ.", "")
    code = code.replace("sh", "").replace("sz", "").replace("bj", "")
    code = code.strip()
    
    if len(code) != 6:
        return StockBoard.UNKNOWN
    
    # 科创板: 688xxx
    if code.startswith("688"):
        return StockBoard.STAR
    
    # 创业板: 300xxx, 301xxx
    if code.startswith("30"):
        return StockBoard.CHINEXT
    
    # 北交所: 8xxxxx, 4xxxxx
    if code.startswith("8") or code.startswith("4"):
        return StockBoard.BSE
    
    # 沪市主板: 60xxxx
    if code.startswith("60"):
        return StockBoard.MAIN_SH
    
    # 深市主板: 00xxxx
    if code.startswith("00"):
        return StockBoard.MAIN_SZ
    
    return StockBoard.UNKNOWN


def get_limit_pct(code: str, name: str = "") -> Tuple[float, float]:
    """
    获取股票的涨跌停幅度
    
    Args:
        code: 股票代码
        name: 股票名称 (用于判断ST)
        
    Returns:
        (涨停幅度, 跌停幅度) 如 (0.10, -0.10)
    """
    # ST股判断 (名称包含ST或*ST)
    is_st = "ST" in name.upper() if name else False
    
    if is_st:
        return (0.05, -0.05)  # ST股 5%
    
    board = get_stock_board(code)
    
    if board == StockBoard.STAR:
        return (0.20, -0.20)  # 科创板 20%
    
    if board == StockBoard.CHINEXT:
        return (0.20, -0.20)  # 创业板 20%
    
    if board == StockBoard.BSE:
        return (0.30, -0.30)  # 北交所 30%
    
    # 主板 10%
    return (0.10, -0.10)


def get_stock_info(code: str, name: str = "") -> StockInfo:
    """
    获取完整的股票信息
    
    Args:
        code: 股票代码
        name: 股票名称
        
    Returns:
        StockInfo: 股票信息对象
    """
    is_st = "ST" in name.upper() if name else False
    board = get_stock_board(code)
    
    # 如果是ST，覆盖板块显示
    if is_st:
        limit_up, limit_down = 0.05, -0.05
        display_board = StockBoard.ST
    else:
        limit_up, limit_down = get_limit_pct(code, name)
        display_board = board
    
    return StockInfo(
        code=code,
        board=display_board,
        limit_up_pct=limit_up,
        limit_down_pct=limit_down,
        is_st=is_st
    )


def is_limit_up(code: str, name: str, change_pct: float) -> bool:
    """
    判断是否涨停
    
    Args:
        code: 股票代码
        name: 股票名称
        change_pct: 涨跌幅 (如 9.98 表示涨9.98%)
        
    Returns:
        bool: 是否涨停
    """
    limit_up_pct, _ = get_limit_pct(code, name)
    # 涨停判断: 涨幅 >= 涨停幅度 - 0.2% (容差)
    return change_pct >= (limit_up_pct * 100 - 0.2)


def is_limit_down(code: str, name: str, change_pct: float) -> bool:
    """
    判断是否跌停
    
    Args:
        code: 股票代码
        name: 股票名称
        change_pct: 涨跌幅 (如 -9.98 表示跌9.98%)
        
    Returns:
        bool: 是否跌停
    """
    _, limit_down_pct = get_limit_pct(code, name)
    # 跌停判断: 跌幅 <= 跌停幅度 + 0.2% (容差)
    return change_pct <= (limit_down_pct * 100 + 0.2)


def is_near_limit_up(code: str, name: str, change_pct: float, threshold: float = 0.7) -> bool:
    """
    判断是否接近涨停
    
    Args:
        code: 股票代码
        name: 股票名称
        change_pct: 涨跌幅
        threshold: 接近涨停的阈值 (默认0.7表示达到涨停幅度的70%)
        
    Returns:
        bool: 是否接近涨停
    """
    limit_up_pct, _ = get_limit_pct(code, name)
    return change_pct >= (limit_up_pct * 100 * threshold)


# 便捷函数
def get_limit_price(pre_close: float, code: str, name: str = "") -> Tuple[float, float]:
    """
    计算涨停价和跌停价
    
    Args:
        pre_close: 昨收价
        code: 股票代码
        name: 股票名称
        
    Returns:
        (涨停价, 跌停价)
    """
    limit_up_pct, limit_down_pct = get_limit_pct(code, name)
    limit_up_price = round(pre_close * (1 + limit_up_pct), 2)
    limit_down_price = round(pre_close * (1 + limit_down_pct), 2)
    return (limit_up_price, limit_down_price)


if __name__ == "__main__":
    # 测试
    test_cases = [
        ("000001", "平安银行", 9.98),    # 主板
        ("300750", "宁德时代", 19.98),   # 创业板
        ("688001", "华兴源创", 19.98),   # 科创板
        ("000592", "平潭发展", 9.98),    # 主板
        ("600519", "贵州茅台", 9.98),    # 沪市主板
        ("000001", "ST冠福", 4.98),      # ST股
    ]
    
    for code, name, pct in test_cases:
        info = get_stock_info(code, name)
        is_up = is_limit_up(code, name, pct)
        print(f"{name}({code}): {info.board.value}, 涨停{info.limit_up_pct*100:.0f}%, 当前{pct}%, 涨停={is_up}")
