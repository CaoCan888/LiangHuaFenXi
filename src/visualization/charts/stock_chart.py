# -*- coding: utf-8 -*-
"""
K线图表模块
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StockChart:
    """股票图表类"""
    
    def __init__(self, title: str = "股票分析图表"):
        self.title = title
    
    def plot_kline(self, df: pd.DataFrame, stock_code: str = "", show_volume: bool = True, indicators: List[str] = None) -> go.Figure:
        """
        绘制K线图
        
        Args:
            df: OHLCV数据
            stock_code: 股票代码
            show_volume: 是否显示成交量
            indicators: 要显示的技术指标列表
        """
        rows = 2 if show_volume else 1
        row_heights = [0.7, 0.3] if show_volume else [1]
        
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_heights, vertical_spacing=0.05)
        
        # 获取日期
        dates = df.index if isinstance(df.index, pd.DatetimeIndex) else df.get('trade_date', range(len(df)))
        
        # K线图
        fig.add_trace(go.Candlestick(
            x=dates,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing_line_color='red',
            decreasing_line_color='green'
        ), row=1, col=1)
        
        # 添加均线
        colors = {'ma5': 'yellow', 'ma10': 'purple', 'ma20': 'blue', 'ma60': 'green'}
        for ma, color in colors.items():
            if ma in df.columns:
                fig.add_trace(go.Scatter(x=dates, y=df[ma], mode='lines', name=ma.upper(), line=dict(color=color, width=1)), row=1, col=1)
        
        # 添加布林带
        if all(c in df.columns for c in ['boll_upper', 'boll_middle', 'boll_lower']):
            fig.add_trace(go.Scatter(x=dates, y=df['boll_upper'], mode='lines', name='BOLL上轨', line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=dates, y=df['boll_lower'], mode='lines', name='BOLL下轨', line=dict(color='gray', width=1, dash='dot'), fill='tonexty'), row=1, col=1)
        
        # 成交量
        if show_volume and 'volume' in df.columns:
            colors = ['red' if c >= o else 'green' for o, c in zip(df['open'], df['close'])]
            fig.add_trace(go.Bar(x=dates, y=df['volume'], name='成交量', marker_color=colors), row=2, col=1)
        
        # 更新布局
        fig.update_layout(
            title=f'{stock_code} K线图' if stock_code else self.title,
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            height=600
        )
        
        return fig
    
    def plot_macd(self, df: pd.DataFrame) -> go.Figure:
        """绘制MACD图"""
        fig = go.Figure()
        dates = df.index if isinstance(df.index, pd.DatetimeIndex) else range(len(df))
        
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            fig.add_trace(go.Scatter(x=dates, y=df['macd'], mode='lines', name='MACD', line=dict(color='white')))
            fig.add_trace(go.Scatter(x=dates, y=df['macd_signal'], mode='lines', name='Signal', line=dict(color='yellow')))
            
            if 'macd_hist' in df.columns:
                colors = ['red' if v >= 0 else 'green' for v in df['macd_hist']]
                fig.add_trace(go.Bar(x=dates, y=df['macd_hist'], name='Histogram', marker_color=colors))
        
        fig.update_layout(title='MACD指标', template='plotly_dark', height=300)
        return fig
    
    def plot_rsi(self, df: pd.DataFrame) -> go.Figure:
        """绘制RSI图"""
        fig = go.Figure()
        dates = df.index if isinstance(df.index, pd.DatetimeIndex) else range(len(df))
        
        for col in ['rsi_6', 'rsi_12', 'rsi_14']:
            if col in df.columns:
                fig.add_trace(go.Scatter(x=dates, y=df[col], mode='lines', name=col.upper()))
        
        fig.add_hline(y=70, line_dash="dash", line_color="red")
        fig.add_hline(y=30, line_dash="dash", line_color="green")
        
        fig.update_layout(title='RSI指标', template='plotly_dark', height=300)
        return fig
    
    def plot_full_analysis(self, df: pd.DataFrame, stock_code: str = "") -> go.Figure:
        """绘制完整分析图（K线+MACD+RSI）"""
        fig = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True,
            row_heights=[0.5, 0.15, 0.15, 0.2],
            vertical_spacing=0.03
        )
        
        dates = df.index if isinstance(df.index, pd.DatetimeIndex) else range(len(df))
        
        # K线
        fig.add_trace(go.Candlestick(x=dates, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K线', increasing_line_color='red', decreasing_line_color='green'), row=1, col=1)
        
        # 均线
        for ma in ['ma5', 'ma20', 'ma60']:
            if ma in df.columns:
                fig.add_trace(go.Scatter(x=dates, y=df[ma], mode='lines', name=ma.upper()), row=1, col=1)
        
        # 成交量
        if 'volume' in df.columns:
            colors = ['red' if c >= o else 'green' for o, c in zip(df['open'], df['close'])]
            fig.add_trace(go.Bar(x=dates, y=df['volume'], name='成交量', marker_color=colors, showlegend=False), row=2, col=1)
        
        # MACD
        if 'macd' in df.columns:
            fig.add_trace(go.Scatter(x=dates, y=df['macd'], mode='lines', name='MACD'), row=3, col=1)
            if 'macd_signal' in df.columns:
                fig.add_trace(go.Scatter(x=dates, y=df['macd_signal'], mode='lines', name='Signal'), row=3, col=1)
        
        # RSI
        if 'rsi_14' in df.columns:
            fig.add_trace(go.Scatter(x=dates, y=df['rsi_14'], mode='lines', name='RSI14'), row=4, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)
        
        fig.update_layout(
            title=f'{stock_code} 技术分析',
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            height=800,
            showlegend=True
        )
        
        return fig


stock_chart = StockChart()
