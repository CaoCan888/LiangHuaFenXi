# -*- coding: utf-8 -*-
"""
投资组合管理模块
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Portfolio:
    """投资组合管理"""
    
    def __init__(self, total_capital: float = 1000000):
        self.total_capital = total_capital
        self.holdings = {}  # {stock_code: {'shares': n, 'cost': price}}
    
    def add_position(self, code: str, shares: int, price: float):
        """添加持仓"""
        if code in self.holdings:
            old = self.holdings[code]
            total_shares = old['shares'] + shares
            avg_cost = (old['shares'] * old['cost'] + shares * price) / total_shares
            self.holdings[code] = {'shares': total_shares, 'cost': avg_cost}
        else:
            self.holdings[code] = {'shares': shares, 'cost': price}
    
    def remove_position(self, code: str, shares: int = None):
        """减少持仓"""
        if code not in self.holdings:
            return
        if shares is None or shares >= self.holdings[code]['shares']:
            del self.holdings[code]
        else:
            self.holdings[code]['shares'] -= shares
    
    def get_value(self, prices: Dict[str, float]) -> float:
        """计算持仓市值"""
        value = 0
        for code, holding in self.holdings.items():
            if code in prices:
                value += holding['shares'] * prices[code]
        return value
    
    def get_weights(self, prices: Dict[str, float]) -> Dict[str, float]:
        """计算各持仓权重"""
        total = self.get_value(prices)
        if total == 0:
            return {}
        return {code: holding['shares'] * prices.get(code, 0) / total for code, holding in self.holdings.items()}
    
    @staticmethod
    def optimize_weights(returns: pd.DataFrame, method: str = 'equal') -> Dict[str, float]:
        """
        权重优化
        
        Args:
            returns: 收益率DataFrame，每列为一只股票
            method: 'equal' 等权 | 'min_var' 最小方差 | 'sharpe' 最大夏普
        """
        stocks = returns.columns.tolist()
        n = len(stocks)
        
        if method == 'equal':
            return {s: 1/n for s in stocks}
        
        elif method == 'min_var':
            cov = returns.cov()
            inv_cov = np.linalg.pinv(cov.values)
            ones = np.ones(n)
            weights = inv_cov.dot(ones) / ones.dot(inv_cov).dot(ones)
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()
            return {stocks[i]: weights[i] for i in range(n)}
        
        return {s: 1/n for s in stocks}
    
    def summary(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """持仓汇总"""
        holdings_detail = []
        for code, holding in self.holdings.items():
            price = prices.get(code, 0)
            market_value = holding['shares'] * price
            profit = (price - holding['cost']) * holding['shares']
            profit_pct = (price / holding['cost'] - 1) if holding['cost'] > 0 else 0
            
            holdings_detail.append({
                'code': code,
                'shares': holding['shares'],
                'cost': holding['cost'],
                'price': price,
                'market_value': market_value,
                'profit': profit,
                'profit_pct': profit_pct
            })
        
        return {
            'total_value': self.get_value(prices),
            'holdings': holdings_detail,
            'weights': self.get_weights(prices)
        }


portfolio = Portfolio()
