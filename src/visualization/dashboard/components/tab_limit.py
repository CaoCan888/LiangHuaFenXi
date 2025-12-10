# -*- coding: utf-8 -*-
"""
打板策略分析组件
"""
import streamlit as st
import pandas as pd

from src.strategy.signals.limit_chase import limit_chase_strategy
from src.strategy.signals.comprehensive_strategy import technical_scorer
from src.strategy.signals.trading_advisor import trading_advisor


def render_limit_tab(df: pd.DataFrame):
    """
    渲染打板策略Tab
    
    Args:
        df: 股票数据DataFrame
    """
    st.subheader("🔥 打板策略分析")
    
    df_limit = limit_chase_strategy.generate_signals(df.copy())
    limit_latest = df_limit.iloc[-1]
    
    # 获取技术评分用于建议
    scores = technical_scorer.calculate_total_score(df)
    
    # 获取交易建议
    advice = trading_advisor.generate_advice(df_limit, scores)
    
    # 第一行：涨停状态
    _render_limit_status(limit_latest)
    
    # 涨停统计
    limit_streak = int(limit_latest.get('limit_streak', 0))
    if 'is_limit_up' in df_limit.columns:
        limit_count = len(df_limit[df_limit['is_limit_up'] == True])
    else:
        limit_count = 0
    st.info(f"📊 近{len(df)}日涨停次数: **{limit_count}**次 | 当前连板: **{limit_streak}**板")
    
    # 交易建议
    st.divider()
    _render_trading_advice(advice)
    
    # 涨停历史
    st.divider()
    _render_limit_history(df_limit)


def _render_limit_status(limit_latest: pd.Series):
    """渲染涨停状态"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        is_limit = limit_latest.get('is_limit_up', False)
        st.metric("今日涨停", "🔥 是" if is_limit else "否")
    
    with col2:
        limit_streak = int(limit_latest.get('limit_streak', 0))
        streak_names = {0: '无', 1: '首板', 2: '二连板', 3: '三连板', 
                       4: '四连板', 5: '五连板', 6: '六连板', 7: '七连板'}
        streak_text = streak_names.get(limit_streak, f'{limit_streak}连板')
        color = '🔥' if limit_streak >= 3 else ('✅' if limit_streak >= 1 else '')
        st.metric("连板状态", f"{color} {streak_text}")
    
    with col3:
        volume_ratio = limit_latest.get('volume_ratio', 1)
        st.metric("量比", f"{volume_ratio:.2f}")
    
    with col4:
        signal = limit_latest.get('signal', 0)
        signal_type = limit_latest.get('signal_type', '')
        if signal == 1:
            st.markdown(f'<span class="signal-buy">信号: {signal_type}</span>', 
                       unsafe_allow_html=True)
        else:
            st.metric("信号", "暂无")


def _render_trading_advice(advice: dict):
    """渲染交易建议"""
    st.subheader("💡 小白操作指南")
    
    action_colors = {
        'BUY': ('#11998e', '#38ef7d'),
        'SELL': ('#ff416c', '#ff4b2b'),
        'HOLD': ('#f7971e', '#ffd200')
    }
    c1, c2 = action_colors.get(advice['action'], ('#667eea', '#764ba2'))
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {c1} 0%, {c2} 100%); 
                padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem;">
        <h2 style="color: white; margin: 0; text-align: center;">
            {trading_advisor.get_action_emoji(advice['action'])}
        </h2>
        <p style="color: white; text-align: center; font-size: 1.1rem; margin: 0.5rem 0;">
            置信度: {advice['confidence']}% | 策略: {advice['strategy']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📌 操作理由**")
        for r in advice.get('reasons', []):
            st.markdown(f"• {r}")
        
        if advice.get('stop_loss'):
            st.markdown(f"**🛑 止损价:** ¥{advice['stop_loss']:.2f}")
        if advice.get('take_profit'):
            st.markdown(f"**🎯 止盈价:** ¥{advice['take_profit']:.2f}")
    
    with col2:
        st.markdown("**⚠️ 风险提示**")
        for r in advice.get('risks', []):
            st.warning(r)
        
        if advice.get('t_plus_0'):
            t = advice['t_plus_0']
            st.markdown("**📈 做T建议**")
            st.markdown(f"""
            - 类型: **{t['type']}**
            - 进场: {t['entry']}
            - 时机: {t['exit_time']}
            - 备注: {t['note']}
            """)


def _render_limit_history(df_limit: pd.DataFrame):
    """渲染涨停历史"""
    if 'is_limit_up' not in df_limit.columns:
        return
    
    limit_days = df_limit[df_limit['is_limit_up'] == True]
    if limit_days.empty:
        return
    
    st.subheader("📅 涨停历史")
    limit_display = limit_days[['open', 'high', 'low', 'close', 'volume']].tail(10).copy()
    limit_display.columns = ['开盘', '最高', '最低', '收盘', '成交量']
    st.dataframe(limit_display, use_container_width=True)
