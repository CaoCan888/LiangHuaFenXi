# -*- coding: utf-8 -*-
"""
报表生成模块
"""

from typing import Dict, Any
import pandas as pd
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger
from src.utils.helpers import format_number, format_currency

logger = get_logger(__name__)


class ReportGenerator:
    """报表生成器"""
    
    def generate_analysis_report(self, stock_code: str, df: pd.DataFrame, summary: Dict, backtest: Dict = None) -> str:
        """生成分析报告"""
        report = []
        report.append(f"# {stock_code} 技术分析报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本信息
        report.append("## 基本信息")
        report.append(f"- 数据周期: {len(df)} 个交易日")
        report.append(f"- 最新价格: {format_number(summary.get('latest_price', 0))}")
        report.append(f"- 趋势判断: {summary.get('trend', 'N/A')}")
        report.append("")
        
        # 技术指标
        report.append("## 技术指标状态")
        
        ma = summary.get('ma_status', {})
        report.append(f"- MA5: {format_number(ma.get('ma5', 0))}")
        report.append(f"- MA20: {format_number(ma.get('ma20', 0))}")
        report.append(f"- 位置: {'站上均线' if ma.get('position') == 'above_ma' else '跌破均线'}")
        
        rsi = summary.get('rsi_status', {})
        report.append(f"- RSI(14): {format_number(rsi.get('rsi_14', 0))}")
        report.append(f"- RSI状态: {rsi.get('condition', 'N/A')}")
        report.append("")
        
        # 交易信号
        signal = summary.get('latest_signal', {})
        report.append("## 交易信号")
        report.append(f"- 信号方向: {signal.get('direction', 'hold')}")
        report.append(f"- 信号强度: {format_number(signal.get('strength', 0) * 100)}%")
        if signal.get('reason'):
            report.append(f"- 信号原因: {signal.get('reason')}")
        report.append("")
        
        # 回测结果
        if backtest:
            report.append("## 回测结果")
            report.append(f"- 总收益率: {format_number(backtest['total_return'] * 100, percentage=True)}")
            report.append(f"- 年化收益: {format_number(backtest['annualized_return'] * 100, percentage=True)}")
            report.append(f"- 最大回撤: {format_number(backtest['max_drawdown'] * 100, percentage=True)}")
            report.append(f"- 夏普比率: {format_number(backtest['sharpe_ratio'])}")
            report.append(f"- 胜率: {format_number(backtest['win_rate'] * 100, percentage=True)}")
            report.append(f"- 交易次数: {backtest['total_trades']}")
        
        return "\n".join(report)
    
    def export_to_excel(self, df: pd.DataFrame, filepath: str, sheet_name: str = "数据"):
        """导出Excel"""
        df.to_excel(filepath, sheet_name=sheet_name, index=True)
        logger.info(f"数据已导出: {filepath}")


report_generator = ReportGenerator()
