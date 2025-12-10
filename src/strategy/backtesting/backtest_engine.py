# -*- coding: utf-8 -*-
"""
回测引擎模块
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.settings import settings
from src.utils.logger import get_logger
from src.utils.helpers import calculate_sharpe_ratio, calculate_max_drawdown

logger = get_logger(__name__)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = None,
        commission_rate: float = None,
        slippage: float = None,
        min_trade_unit: int = None
    ):
        self.initial_capital = initial_capital or settings.backtest.initial_capital
        self.commission_rate = commission_rate or settings.backtest.commission_rate
        self.slippage = slippage or settings.backtest.slippage
        self.min_trade_unit = min_trade_unit or settings.backtest.min_trade_unit
        
        self.reset()
    
    def reset(self):
        """重置回测状态"""
        self.capital = self.initial_capital
        self.position = 0
        self.trades = []
        self.equity_curve = []
        self.holding_price = 0
    
    def run(self, df: pd.DataFrame, strategy_name: str = 'custom') -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            df: 包含signal列的DataFrame
            strategy_name: 策略名称
        """
        self.reset()
        
        if 'signal' not in df.columns:
            raise ValueError("DataFrame必须包含signal列")
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            date = df.index[idx] if isinstance(df.index[idx], (datetime, pd.Timestamp)) else row.get('trade_date')
            price = row['close']
            signal = row['signal']
            
            # 记录持仓市值
            equity = self.capital + self.position * price
            self.equity_curve.append({'date': date, 'equity': equity, 'price': price})
            
            # 执行交易
            if signal == 1 and self.position == 0:  # 买入
                self._buy(date, price)
            elif signal == -1 and self.position > 0:  # 卖出
                self._sell(date, price)
        
        # 计算回测结果
        return self._calculate_results(df, strategy_name)
    
    def _buy(self, date, price):
        """买入"""
        actual_price = price * (1 + self.slippage)
        shares = int(self.capital * 0.95 / actual_price / self.min_trade_unit) * self.min_trade_unit
        
        if shares > 0:
            cost = shares * actual_price
            commission = cost * self.commission_rate
            
            self.capital -= (cost + commission)
            self.position = shares
            self.holding_price = actual_price
            
            self.trades.append({
                'date': date, 'type': 'BUY', 'price': actual_price,
                'shares': shares, 'amount': cost, 'commission': commission
            })
            logger.debug(f"买入: {date} {shares}股 @ {actual_price:.2f}")
    
    def _sell(self, date, price):
        """卖出"""
        actual_price = price * (1 - self.slippage)
        revenue = self.position * actual_price
        commission = revenue * self.commission_rate
        profit = revenue - self.position * self.holding_price - commission
        
        self.capital += (revenue - commission)
        
        self.trades.append({
            'date': date, 'type': 'SELL', 'price': actual_price,
            'shares': self.position, 'amount': revenue, 'commission': commission, 'profit': profit
        })
        logger.debug(f"卖出: {date} {self.position}股 @ {actual_price:.2f} 盈亏:{profit:.2f}")
        
        self.position = 0
        self.holding_price = 0
    
    def _calculate_results(self, df: pd.DataFrame, strategy_name: str) -> Dict[str, Any]:
        """计算回测结果"""
        equity_df = pd.DataFrame(self.equity_curve)
        
        if equity_df.empty:
            return {'error': '回测数据不足'}
        
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 计算收益率序列
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # 年化收益率
        days = len(equity_df)
        annualized_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        dd_result = calculate_max_drawdown(equity_df['equity'])
        max_drawdown = dd_result['max_drawdown']
        
        # 夏普比率 - 只有在有实际交易时才有意义
        returns = equity_df['returns'].dropna()
        if len(self.trades) > 0 and len(returns) > 1:
            sharpe = calculate_sharpe_ratio(returns)
        else:
            sharpe = 0.0
        
        # 交易统计
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        win_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
        
        results = {
            'strategy_name': strategy_name,
            'initial_capital': self.initial_capital,
            'final_capital': final_equity,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        logger.info(f"回测完成: 总收益{total_return*100:.2f}% 最大回撤{max_drawdown*100:.2f}%")
        return results


backtest_engine = BacktestEngine()
