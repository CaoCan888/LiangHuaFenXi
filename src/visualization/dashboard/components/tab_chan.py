# -*- coding: utf-8 -*-
"""
缠论分析组件
"""
import streamlit as st
import pandas as pd

from src.strategy.signals.chan_strategy import chan_analyzer


def render_chan_tab(df: pd.DataFrame):
    """
    渲染缠论分析Tab
    
    Args:
        df: 股票数据DataFrame
    """
    st.subheader("📐 缠论分析")
    
    chan_result = chan_analyzer.analyze(df)
    
    # 基本统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("分型数", chan_result['fx_count'])
    
    with col2:
        st.metric("笔数", chan_result['bi_count'])
    
    with col3:
        st.metric("中枢数", chan_result.get('zs_count', 0))
    
    with col4:
        if chan_result['latest_fx']:
            fx_mark = chan_result['latest_fx'].mark.value
            color = '🔴' if '顶' in fx_mark else '🟢'
            st.metric("最新分型", f"{color} {fx_mark}")
        else:
            st.metric("最新分型", "无")
    
    # 买卖点判断
    bs = chan_analyzer.get_bs_point(df)
    
    if bs['signal'] == 1:
        st.success(f"🟢 **买入信号**: {bs['signal_type']}")
    elif bs['signal'] == -1:
        st.error(f"🔴 **卖出信号**: {bs['signal_type']}")
    else:
        st.info("⚪ 暂无明确买卖点信号")
    
    # 中枢信息
    if bs.get('latest_zs'):
        st.markdown("**📊 当前中枢**")
        zs = bs['latest_zs']
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("中枢高点(ZG)", f"¥{zs['zg']:.2f}")
        with col2:
            st.metric("中枢低点(ZD)", f"¥{zs['zd']:.2f}")
        with col3:
            st.metric("包含笔数", zs['bi_count'])
    
    # 笔列表
    if chan_result['bi_list']:
        st.subheader("📊 最近5笔")
        bi_data = []
        for bi in chan_result['bi_list'][-5:]:
            bi_data.append({
                '开始': bi.start_dt,
                '结束': bi.end_dt,
                '方向': '↑' if bi.direction.value == 'up' else '↓',
                '高点': bi.high,
                '低点': bi.low,
                '力度': f"{bi.power*100:.1f}%"
            })
        st.dataframe(pd.DataFrame(bi_data), use_container_width=True)
