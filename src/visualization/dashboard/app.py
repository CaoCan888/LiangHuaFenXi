# -*- coding: utf-8 -*-
"""
Streamlit仪表盘 - 模块化重构版
整合打板策略、缠论分析、CZSC经典策略、技术评分

重构说明：
- 原app.py: 930行 → 重构后: ~200行
- Tab逻辑已拆分到 components/ 目录
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 禁用日志
import logging
logging.disable(logging.WARNING)

from src.data.collectors import stock_collector
from src.data.processors import data_processor
from src.analysis import technical_analyzer

# 导入组件
from src.visualization.dashboard.components.tab_realtime import render_realtime_tab
from src.visualization.dashboard.components.tab_chart import render_chart_tab, create_candlestick_chart
from src.visualization.dashboard.components.tab_score import render_score_tab
from src.visualization.dashboard.components.tab_limit import render_limit_tab
from src.visualization.dashboard.components.tab_chan import render_chan_tab
from src.visualization.dashboard.components.tab_dragon import render_dragon_tab
from src.visualization.dashboard.components.tab_backtest import render_backtest_tab
from src.visualization.dashboard.components.tab_portfolio import render_portfolio_panel, render_watchlist_panel, render_win_rate_stats

st.set_page_config(
    page_title="AI股票分析系统", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .signal-buy {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        color: white;
        font-weight: bold;
    }
    .signal-sell {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """主函数"""
    st.markdown('<h1 class="main-header">📈 AI股票分析系统</h1>', unsafe_allow_html=True)
    
    # 侧边栏
    code, days, strategy, initial_capital, user_shares, user_cost, fetch_btn = render_sidebar()
    
    # 主区域
    if fetch_btn or st.session_state.get('data') is not None:
        df = fetch_and_process_data(code, days, fetch_btn)
        
        if df is not None and not df.empty:
            render_dashboard(df, code, strategy, initial_capital, user_shares, user_cost)
        else:
            st.error("❌ 获取数据失败，请检查股票代码或网络连接")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("🎯 参数设置")
        
        market = st.selectbox("市场", ["SH", "SZ", "HK", "US"], index=1)
        stock_code = st.text_input("股票代码", value="002682")
        full_code = f"{market}.{stock_code}"
        
        days = st.slider("数据天数", 30, 365, 120)
        
        st.divider()
        
        st.subheader("🔧 策略选择")
        strategy = st.selectbox(
            "回测策略", 
            ["combined", "limit_chase", "czsc", "comprehensive", "momentum", "intraday", "ma_cross", "macd"],
            format_func=lambda x: {
                "combined": "综合策略",
                "limit_chase": "🔥 打板策略",
                "czsc": "缠论策略",
                "comprehensive": "⭐ 大师策略",
                "momentum": "动量策略",
                "intraday": "📈 日内策略",
                "ma_cross": "均线交叉",
                "macd": "MACD策略"
            }.get(x, x)
        )
        
        initial_capital = st.number_input("初始资金", value=1000000, step=100000)
        
        st.divider()
        
        st.subheader("💼 我的持仓")
        user_shares = st.number_input("持仓股数", value=0, step=100, help="您持有的股票数量")
        user_cost = st.number_input("买入成本(元)", value=0.0, step=0.01, format="%.2f", help="您的平均买入价格")
        
        st.divider()
        
        fetch_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)
    
    return full_code, days, strategy, initial_capital, user_shares, user_cost, fetch_btn


def fetch_and_process_data(code: str, days: int, fetch_btn: bool) -> pd.DataFrame:
    """获取并处理数据"""
    if fetch_btn:
        with st.spinner("正在获取数据..."):
            # 带重试的数据获取
            for attempt in range(3):
                try:
                    df = stock_collector.get_daily_data(code, days=days)
                    if df is not None and not df.empty:
                        break
                except Exception as e:
                    if attempt == 2:
                        st.error(f"数据获取失败: {e}")
                        return None
            
            if df is not None and not df.empty:
                df = data_processor.clean_data(df)
                df = technical_analyzer.analyze(df)
                
                if 'trade_date' in df.columns:
                    df.set_index('trade_date', inplace=True)
                
                st.session_state['data'] = df
                st.session_state['code'] = code
                return df
    
    return st.session_state.get('data')


def render_dashboard(df: pd.DataFrame, code: str, strategy: str, 
                    initial_capital: float, user_shares: int, user_cost: float):
    """渲染主仪表盘"""
    latest = df.iloc[-1]
    
    # 核心指标
    render_key_metrics(df, latest)
    
    st.divider()
    
    # 分析标签页
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "💰 实时资金", "📊 K线图表", "🎯 技术评分", 
        "🔥 打板分析", "📐 缠论分析", "🐉 龙虎榜", "📈 回测结果", "💼 我的持仓"
    ])
    
    with tab1:
        render_realtime_tab(df, code, user_shares, user_cost, latest)
    
    with tab2:
        render_chart_tab(df, code)
    
    with tab3:
        render_score_tab(df)
    
    with tab4:
        render_limit_tab(df)
    
    with tab5:
        render_chan_tab(df)
    
    with tab6:
        render_dragon_tab(code)
    
    with tab7:
        render_backtest_tab(df, strategy, initial_capital)
    
    with tab8:
        # 获取股票名称
        stock_name = code.split('.')[-1]  # 简化处理
        current_price = latest['close']
        render_portfolio_panel(code, stock_name, current_price, user_shares, user_cost)
        render_watchlist_panel()
        render_win_rate_stats()
    
    # 底部原始数据
    with st.expander("📑 查看原始数据"):
        st.dataframe(df.tail(30), use_container_width=True)


def render_key_metrics(df: pd.DataFrame, latest: pd.Series):
    """渲染核心指标"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        change = (latest['close'] / df.iloc[-2]['close'] - 1) * 100 if len(df) > 1 else 0
        st.metric("📈 最新价", f"¥{latest['close']:.2f}", f"{change:+.2f}%")
    
    with col2:
        st.metric("📊 最高", f"¥{latest['high']:.2f}")
    
    with col3:
        st.metric("📉 最低", f"¥{latest['low']:.2f}")
    
    with col4:
        vol_ratio = latest['volume'] / df['volume'].rolling(20).mean().iloc[-1] if len(df) >= 20 else 1
        st.metric("📈 量比", f"{vol_ratio:.2f}")
    
    with col5:
        pct_20 = (latest['close'] / df.iloc[-20]['close'] - 1) * 100 if len(df) >= 20 else 0
        st.metric("📅 20日涨幅", f"{pct_20:+.2f}%")


if __name__ == "__main__":
    main()
