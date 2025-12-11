# -*- coding: utf-8 -*-
"""
Dashboard组件 - 自选股和持仓管理面板
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def render_portfolio_panel(stock_code: str, stock_name: str, current_price: float, 
                           user_shares: int = 0, user_cost: float = 0):
    """
    渲染持仓盈亏面板
    
    Args:
        stock_code: 当前查看的股票代码
        stock_name: 股票名称
        current_price: 当前价格
        user_shares: 用户持仓股数
        user_cost: 用户持仓成本
    """
    with st.expander("💼 我的持仓盈亏", expanded=True):
        if user_shares > 0 and user_cost > 0:
            # 计算盈亏
            market_value = user_shares * current_price
            total_cost = user_shares * user_cost
            profit = market_value - total_cost
            profit_pct = (current_price / user_cost - 1) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("持仓数量", f"{user_shares:,}股")
            
            with col2:
                st.metric("成本价", f"¥{user_cost:.2f}")
            
            with col3:
                st.metric("市值", f"¥{market_value:,.0f}")
            
            with col4:
                # 盈亏颜色
                delta_color = "normal" if profit >= 0 else "inverse"
                st.metric(
                    "浮动盈亏",
                    f"¥{profit:,.0f}",
                    delta=f"{profit_pct:+.2f}%",
                    delta_color=delta_color
                )
            
            # 盈亏进度条
            if profit >= 0:
                st.progress(min(profit_pct / 20, 1.0))  # 20%为满进度
                st.success(f"📈 恭喜！当前盈利 {profit_pct:.2f}%")
            else:
                st.progress(min(abs(profit_pct) / 10, 1.0))  # 10%亏损为满
                if profit_pct > -5:
                    st.warning(f"⚠️ 轻度亏损 {profit_pct:.2f}%，关注止损位")
                else:
                    st.error(f"🔻 亏损较大 {profit_pct:.2f}%，建议评估是否止损")
            
            # 建议
            st.markdown("---")
            st.markdown("**📊 持仓建议**")
            if profit_pct > 10:
                st.info("💰 盈利超10%，可考虑分批止盈锁定利润")
            elif profit_pct > 5:
                st.info("📈 盈利良好，可设置移动止盈保护利润")
            elif profit_pct > 0:
                st.info("👀 小幅盈利，继续持有观察")
            elif profit_pct > -5:
                st.warning("⏳ 轻度浮亏，观察支撑位，不符预期及时止损")
            else:
                st.error("⚠️ 亏损较大，严格执行止损纪律")
        else:
            st.info("💡 在左侧边栏输入您的持仓信息，即可查看实时盈亏")


def render_watchlist_panel():
    """渲染自选股面板"""
    try:
        from src.data.services.portfolio_service import portfolio_service
        
        with st.expander("⭐ 我的自选股", expanded=False):
            # 获取自选股列表
            watchlist = portfolio_service.get_watchlist()
            
            if watchlist:
                # 转为DataFrame显示
                df = pd.DataFrame(watchlist)
                df = df[['code', 'name', 'group', 'added_at']]
                df.columns = ['代码', '名称', '分组', '添加时间']
                df['添加时间'] = pd.to_datetime(df['添加时间']).dt.strftime('%m-%d %H:%M')
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # 快速跳转
                st.markdown("**快速切换**")
                codes = [f"{w['name']}({w['code']})" for w in watchlist]
                selected = st.selectbox("选择股票", codes, label_visibility="collapsed")
                if selected:
                    # 提取代码
                    code = selected.split('(')[-1].rstrip(')')
                    st.info(f"💡 在左侧边栏输入代码 {code} 并点击分析")
            else:
                st.info("暂无自选股，使用 `portfolio_service.add_to_watchlist()` 添加")
                
            # 添加自选股表单
            with st.form("add_watchlist"):
                st.markdown("**添加自选股**")
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_code = st.text_input("股票代码", placeholder="如: 000592")
                with col2:
                    new_name = st.text_input("名称", placeholder="选填")
                
                if st.form_submit_button("➕ 添加"):
                    if new_code:
                        success = portfolio_service.add_to_watchlist(new_code, new_name)
                        if success:
                            st.success(f"已添加 {new_code}")
                            st.rerun()
                        else:
                            st.error("添加失败")
    except Exception as e:
        st.warning(f"自选股功能暂不可用: {e}")


def render_win_rate_stats():
    """渲染历史胜率统计面板"""
    try:
        from src.data.services.db_service import db_service
        
        with st.expander("📊 AI分析历史胜率", expanded=False):
            # 获取分析历史
            from src.data.models import AnalysisHistory
            from src.data.storage.db_manager import get_db_manager
            
            db = get_db_manager()
            session = db.get_session()
            
            try:
                # 统计最近30天的分析记录
                from datetime import timedelta
                thirty_days_ago = datetime.now() - timedelta(days=30)
                
                records = session.query(AnalysisHistory).filter(
                    AnalysisHistory.analysis_time >= thirty_days_ago
                ).order_by(AnalysisHistory.analysis_time.desc()).limit(100).all()
                
                if records:
                    # 信号统计
                    buy_count = sum(1 for r in records if r.signal_type == 'BUY')
                    sell_count = sum(1 for r in records if r.signal_type == 'SELL')
                    hold_count = sum(1 for r in records if r.signal_type == 'HOLD')
                    total = len(records)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("分析次数", total)
                    with col2:
                        st.metric("买入建议", buy_count, delta=f"{buy_count/total*100:.0f}%")
                    with col3:
                        st.metric("卖出建议", sell_count, delta=f"{sell_count/total*100:.0f}%")
                    with col4:
                        st.metric("观望建议", hold_count, delta=f"{hold_count/total*100:.0f}%")
                    
                    # 置信度分布
                    confidences = [r.signal_confidence for r in records if r.signal_confidence]
                    if confidences:
                        avg_conf = sum(confidences) / len(confidences)
                        st.markdown(f"**平均置信度**: {avg_conf:.1f}%")
                        
                        # 置信度直方图
                        conf_df = pd.DataFrame({'置信度': confidences})
                        st.bar_chart(conf_df['置信度'].value_counts().sort_index())
                    
                    st.caption("💡 提示: 历史分析不代表未来表现，仅供参考")
                else:
                    st.info("暂无分析记录，开始使用系统后将自动统计")
            finally:
                session.close()
                
    except Exception as e:
        st.warning(f"胜率统计暂不可用: {e}")
