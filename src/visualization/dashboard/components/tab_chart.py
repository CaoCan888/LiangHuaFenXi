# -*- coding: utf-8 -*-
"""
K线图表组件
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(df: pd.DataFrame, title: str = "K线图") -> go.Figure:
    """
    创建K线图
    
    Args:
        df: 包含OHLCV的DataFrame
        title: 图表标题
        
    Returns:
        plotly Figure对象
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.7, 0.3])
    
    # K线
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing_line_color='#ff4b4b',
            decreasing_line_color='#00cc00'
        ),
        row=1, col=1
    )
    
    # 均线
    ma_colors = {'ma5': '#FFA500', 'ma10': '#FF69B4', 'ma20': '#00CED1', 'ma60': '#9370DB'}
    for ma, color in ma_colors.items():
        if ma in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[ma], name=ma.upper(), 
                          line=dict(color=color, width=1)),
                row=1, col=1
            )
    
    # 成交量
    colors = ['#ff4b4b' if df['close'].iloc[i] >= df['open'].iloc[i] else '#00cc00' 
              for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=df.index, y=df['volume'], name='成交量', marker_color=colors),
        row=2, col=1
    )
    
    fig.update_layout(
        title=title,
        height=600,
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def render_chart_tab(df: pd.DataFrame, code: str):
    """
    渲染K线图表Tab
    
    Args:
        df: 股票数据DataFrame
        code: 股票代码
    """
    fig = create_candlestick_chart(df, f"{code} K线图")
    st.plotly_chart(fig, use_container_width=True)
