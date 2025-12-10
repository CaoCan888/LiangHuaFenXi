# -*- coding: utf-8 -*-
"""
回测结果组件
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.strategy import signal_generator, backtest_engine


def render_backtest_tab(df: pd.DataFrame, strategy: str, initial_capital: float):
    """
    渲染回测Tab
    
    Args:
        df: 股票数据DataFrame
        strategy: 策略名称
        initial_capital: 初始资金
    """
    st.subheader("📈 策略回测")
    
    with st.spinner("正在回测..."):
        df_signal = signal_generator.generate(df.copy(), strategy)
        backtest_engine.initial_capital = initial_capital
        results = backtest_engine.run(df_signal, strategy)
    
    # 回测指标
    _render_backtest_metrics(results)
    
    # 权益曲线
    _render_equity_curve(results)
    
    # 交易记录
    _render_trades(results)


def _render_backtest_metrics(results: dict):
    """渲染回测指标"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ret = results['total_return'] * 100
        color = 'normal' if ret >= 0 else 'inverse'
        st.metric("总收益率", f"{ret:.2f}%", delta_color=color)
    
    with col2:
        st.metric("年化收益", f"{results['annualized_return']*100:.2f}%")
    
    with col3:
        st.metric("最大回撤", f"{results['max_drawdown']*100:.2f}%")
    
    with col4:
        st.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("胜率", f"{results['win_rate']*100:.1f}%")
    
    with col2:
        st.metric("交易次数", results.get('total_trades', 0))


def _render_equity_curve(results: dict):
    """渲染权益曲线"""
    st.subheader("💰 权益曲线")
    equity_df = pd.DataFrame(results['equity_curve'])
    
    if equity_df.empty:
        st.info("无权益曲线数据")
        return
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df['date'],
        y=equity_df['equity'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#667eea')
    ))
    fig.update_layout(
        height=300,
        template='plotly_dark',
        xaxis_title='日期',
        yaxis_title='资金'
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_trades(results: dict):
    """渲染交易记录"""
    if not results['trades']:
        return
    
    with st.expander("📋 查看交易记录"):
        trades_df = pd.DataFrame(results['trades'])
        trades_df = trades_df.rename(columns={
            'date': '日期', 'type': '类型', 'price': '价格',
            'shares': '股数', 'amount': '金额', 'commission': '手续费',
            'profit': '盈亏'
        })
        st.dataframe(trades_df, use_container_width=True)
