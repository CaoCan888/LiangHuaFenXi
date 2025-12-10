# -*- coding: utf-8 -*-
"""
技术评分组件
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.strategy.signals.comprehensive_strategy import technical_scorer, czsc_bar_signals


def render_score_tab(df: pd.DataFrame):
    """
    渲染技术评分Tab
    
    Args:
        df: 股票数据DataFrame
    """
    st.subheader("🎯 技术评分系统")
    
    scores = technical_scorer.calculate_total_score(df)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        _render_total_score(scores)
    
    with col2:
        _render_score_breakdown(scores)
    
    # CZSC经典策略信号
    st.subheader("📊 CZSC经典策略信号")
    _render_czsc_signals(df)


def _render_total_score(scores: dict):
    """渲染总分"""
    total = scores.get('total_score', 0)
    color = '#11998e' if total >= 70 else ('#ffd700' if total >= 50 else '#ff4b2b')
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {color} 0%, {color}aa 100%); 
                padding: 2rem; border-radius: 20px; text-align: center;">
        <h1 style="color: white; font-size: 4rem; margin: 0;">{total:.0f}</h1>
        <h3 style="color: white; margin: 0;">{scores.get('rating', '未知')}</h3>
    </div>
    """, unsafe_allow_html=True)


def _render_score_breakdown(scores: dict):
    """渲染分项评分"""
    score_data = pd.DataFrame({
        '指标': ['均线系统', 'MACD', 'RSI', '量能', '趋势', '形态'],
        '评分': [
            scores.get('ma_score', 0), scores.get('macd_score', 0), scores.get('rsi_score', 0),
            scores.get('volume_score', 0), scores.get('trend_score', 0), scores.get('pattern_score', 0)
        ]
    })
    
    fig = go.Figure(go.Bar(
        x=score_data['评分'],
        y=score_data['指标'],
        orientation='h',
        marker=dict(
            color=score_data['评分'],
            colorscale='RdYlGn',
            cmin=0, cmax=100
        ),
        text=score_data['评分'].round(1),
        textposition='inside'
    ))
    fig.update_layout(
        height=300,
        xaxis_range=[0, 100],
        template='plotly_dark'
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_czsc_signals(df: pd.DataFrame):
    """渲染CZSC策略信号"""
    col1, col2, col3, col4 = st.columns(4)
    
    df_r = czsc_bar_signals.r_breaker(df.copy())
    r_signal = df_r.iloc[-1].get('r_signal', 0)
    r_type = df_r.iloc[-1].get('r_type', '无信号')
    
    df_dt = czsc_bar_signals.dual_thrust(df.copy())
    dt_signal = df_dt.iloc[-1].get('dt_signal', 0)
    
    df_tnr = czsc_bar_signals.tnr_trend(df.copy())
    tnr = df_tnr.iloc[-1].get('tnr', 0)
    
    with col1:
        color = '🟢' if r_signal == 1 else ('🔴' if r_signal == -1 else '⚪')
        st.metric("R-Breaker", f"{color} {r_type}")
    
    with col2:
        dt_text = '突破做多' if dt_signal == 1 else ('突破做空' if dt_signal == -1 else '无信号')
        color = '🟢' if dt_signal == 1 else ('🔴' if dt_signal == -1 else '⚪')
        st.metric("Dual Thrust", f"{color} {dt_text}")
    
    with col3:
        tnr_text = '强趋势' if tnr > 0.5 else ('弱趋势' if tnr > 0.3 else '震荡')
        st.metric("TNR趋势", f"{tnr:.2f} ({tnr_text})")
    
    with col4:
        df_sf = czsc_bar_signals.shuang_fei_zt(df.copy())
        sf = df_sf.iloc[-1].get('shuangfei', False)
        st.metric("双飞涨停", "🔥 触发" if sf else "⚪ 无")
