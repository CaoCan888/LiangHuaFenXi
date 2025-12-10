# -*- coding: utf-8 -*-
"""
基本面分析模块
"""

from typing import Dict, Any
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FundamentalAnalyzer:
    """基本面分析器"""
    
    @staticmethod
    def calculate_roe(net_profit: float, total_equity: float) -> float:
        """净资产收益率 ROE"""
        return net_profit / total_equity if total_equity != 0 else 0
    
    @staticmethod
    def calculate_roa(net_profit: float, total_assets: float) -> float:
        """总资产收益率 ROA"""
        return net_profit / total_assets if total_assets != 0 else 0
    
    @staticmethod
    def calculate_pe(price: float, eps: float) -> float:
        """市盈率 PE"""
        return price / eps if eps > 0 else float('inf')
    
    @staticmethod
    def calculate_pb(price: float, bps: float) -> float:
        """市净率 PB"""
        return price / bps if bps > 0 else float('inf')
    
    @staticmethod
    def calculate_debt_ratio(total_liabilities: float, total_assets: float) -> float:
        """资产负债率"""
        return total_liabilities / total_assets if total_assets != 0 else 0
    
    @staticmethod
    def dupont_analysis(net_profit: float, revenue: float, total_assets: float, total_equity: float) -> Dict:
        """杜邦分析"""
        net_margin = net_profit / revenue if revenue != 0 else 0
        asset_turnover = revenue / total_assets if total_assets != 0 else 0
        equity_multiplier = total_assets / total_equity if total_equity != 0 else 0
        roe = net_margin * asset_turnover * equity_multiplier
        return {'net_margin': net_margin, 'asset_turnover': asset_turnover, 'equity_multiplier': equity_multiplier, 'roe': roe}
    
    @staticmethod
    def analyze(data: Dict[str, float]) -> Dict[str, Any]:
        """综合分析"""
        result = {'profitability': {}, 'valuation': {}, 'solvency': {}}
        
        if 'net_profit' in data and 'total_equity' in data:
            result['profitability']['roe'] = FundamentalAnalyzer.calculate_roe(data['net_profit'], data['total_equity'])
        if 'price' in data and 'eps' in data:
            result['valuation']['pe'] = FundamentalAnalyzer.calculate_pe(data['price'], data['eps'])
        if 'total_liabilities' in data and 'total_assets' in data:
            result['solvency']['debt_ratio'] = FundamentalAnalyzer.calculate_debt_ratio(data['total_liabilities'], data['total_assets'])
        
        return result


fundamental_analyzer = FundamentalAnalyzer()
