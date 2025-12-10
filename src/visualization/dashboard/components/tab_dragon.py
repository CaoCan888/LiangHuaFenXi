# -*- coding: utf-8 -*-
"""
龙虎榜分析组件
"""
import streamlit as st
import pandas as pd
from datetime import datetime


def render_dragon_tab(code: str):
    """
    渲染龙虎榜Tab
    
    Args:
        code: 股票代码
    """
    st.subheader("🐉 龙虎榜分析")
    
    try:
        import akshare as ak
    except ImportError:
        st.error("❌ akshare未安装，请运行: pip install akshare")
        return
    
    stock_code_clean = code.split('.')[-1] if '.' in code else code
    
    col1, col2 = st.columns(2)
    
    with col1:
        _render_stock_lhb_history(ak, stock_code_clean)
    
    with col2:
        _render_today_lhb(ak)
    
    # 人气榜
    st.divider()
    _render_hot_rank(ak)


def _render_stock_lhb_history(ak, stock_code: str):
    """渲染个股龙虎榜历史"""
    st.markdown("**📊 个股龙虎榜历史**")
    try:
        lhb_df = ak.stock_lhb_stock_detail_em(symbol=stock_code)
        if lhb_df is not None and not lhb_df.empty:
            display_cols = [col for col in lhb_df.columns 
                          if any(x in col for x in ['日期', '收盘', '涨跌', '净买', '原因'])][:5]
            if not display_cols:
                display_cols = list(lhb_df.columns[:5])
            st.dataframe(lhb_df[display_cols].head(10), use_container_width=True)
            
            # 统计净买入
            net_cols = [c for c in lhb_df.columns if '净买' in c]
            if net_cols:
                net_buy = lhb_df[net_cols[0]].sum()
                st.info(f"📈 近期龙虎榜净买入: **{net_buy/10000:.2f}亿**")
        else:
            st.info("💡 该股票近期无龙虎榜记录")
    except Exception as e:
        st.info("💡 该股票近期无龙虎榜记录")


def _render_today_lhb(ak):
    """渲染今日龙虎榜"""
    st.markdown("**🔥 今日龙虎榜热股**")
    try:
        today = datetime.now().strftime('%Y%m%d')
        today_lhb = ak.stock_lhb_detail_em(start_date=today, end_date=today)
        
        if today_lhb is not None and not today_lhb.empty:
            display_cols = [col for col in today_lhb.columns 
                          if any(x in col for x in ['代码', '名称', '涨跌', '净买', '原因'])][:5]
            if not display_cols:
                display_cols = list(today_lhb.columns[:5])
            st.dataframe(today_lhb[display_cols].head(15), use_container_width=True)
        else:
            st.info("⏳ 今日龙虎榜尚未公布，通常17:30后更新")
    except Exception as e:
        st.info("⏳ 今日龙虎榜尚未公布，通常17:30后更新")


def _render_hot_rank(ak):
    """渲染人气榜"""
    st.markdown("**🌟 人气榜 Top 20**")
    try:
        hot_df = ak.stock_hot_rank_em()
        if hot_df is not None and not hot_df.empty:
            display_cols = [col for col in hot_df.columns 
                          if any(x in col for x in ['排名', '代码', '名称', '股票', '最新', '涨跌'])][:5]
            if not display_cols:
                display_cols = list(hot_df.columns[:5])
            st.dataframe(hot_df[display_cols].head(20), use_container_width=True)
    except Exception as e:
        st.info("暂无人气榜数据")
