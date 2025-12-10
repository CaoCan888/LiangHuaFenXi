# -*- coding: utf-8 -*-
"""
实时资金与持仓分析组件
简化版 - 解决autorefresh和布局问题
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


def render_realtime_tab(df: pd.DataFrame, code: str, user_shares: int, user_cost: float, latest: pd.Series):
    """渲染实时资金Tab"""
    
    # 导入依赖
    try:
        import akshare as ak
        from src.data.collectors.realtime_service import get_realtime_quote, get_intraday_data
        from src.strategy.signals.realtime_strategy import realtime_strategy
        from src.strategy.signals.intraday_pattern import analyze_intraday_patterns, intraday_analyzer
        from src.strategy.signals.big_order_tracker import get_buy_sell_pressure
    except ImportError as e:
        st.error(f"模块加载失败: {e}")
        return

    stock_code_clean = code.split('.')[-1] if '.' in code else code
    quote = get_realtime_quote(stock_code_clean)
    
    if not quote:
        st.warning("⏳ 正在获取实时行情...")
        return
    
    # 初始化信号流水表
    _init_signal_timeline(stock_code_clean)

    # 手动刷新按钮
    col_title, col_refresh = st.columns([8, 2])
    with col_title:
        st.subheader("💰 实时资金分析")
    with col_refresh:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    # 1. 顶部看板
    _render_top_dashboard(quote)
    
    st.divider()

    # 2. 分时图 + 五档盘口
    col_chart, col_book = st.columns([2, 1])
    
    with col_chart:
        _render_intraday_chart(stock_code_clean, quote)
        
    with col_book:
        _render_order_book(quote)
        
    st.divider()
    
    # 3. 实时信号 + 信号流水表
    col_signal, col_timeline = st.columns([1, 1])
    
    with col_signal:
        _render_realtime_signals(stock_code_clean, df, quote)
        
    with col_timeline:
        _render_signal_timeline_table()
        
    st.divider()
    
    # 4. 信号聚合面板
    _render_signal_aggregation(stock_code_clean, df, quote)
    
    st.divider()
    
    # 5. AI智能分析
    _render_ai_analysis(stock_code_clean, quote, df)
    
    st.divider()
    
    # 5. 持仓分析（如果有）
    if user_shares > 0 and user_cost > 0:
        _render_position_analysis(user_shares, user_cost, quote.price)
        st.divider()
    
    # 6. 资金流向（折叠）
    with st.expander("💹 主力资金动向"):
        _render_fund_flow(ak, stock_code_clean)
    
    # 7. 分析历史（折叠）
    with st.expander("📜 分析历史记录"):
        _render_analysis_history(stock_code_clean)

def _render_ai_analysis(code: str, quote, df: pd.DataFrame):
    """渲染AI智能分析区域"""
    st.markdown("### 🤖 AI智能分析 (Groq)")
    
    # 初始化session state
    if 'ai_analysis_result' not in st.session_state:
        st.session_state.ai_analysis_result = None
    if 'ai_analysis_code' not in st.session_state:
        st.session_state.ai_analysis_code = None
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🧠 AI分析", use_container_width=True, type="primary"):
            with st.spinner("AI正在分析..."):
                try:
                    from src.strategy.ai_analyzer import analyze_stock
                    from src.strategy.signals.intraday_pattern import analyze_intraday_patterns
                    from src.strategy.signals.big_order_tracker import get_buy_sell_pressure
                    from src.data.collectors.realtime_service import get_intraday_data
                    
                    # 准备数据
                    intraday_df = get_intraday_data(code, datalen=48)
                    patterns = []
                    if not intraday_df.empty:
                        pt_signals = analyze_intraday_patterns(intraday_df, quote.pre_close)
                        patterns = [s.pattern.value for s in pt_signals]
                    
                    pressure = get_buy_sell_pressure(code)
                    pressure_text = pressure.pressure if pressure else "均衡"
                    
                    # 获取信号
                    signals = [item['类型'] for item in st.session_state.get('signal_timeline', [])[:5]]
                    
                    # 均线位置
                    ma_pos = "无数据"
                    if df is not None and 'ma5' in df.columns:
                        ma5 = df['ma5'].iloc[-1]
                        ma20 = df['ma20'].iloc[-1] if 'ma20' in df.columns else ma5
                        if quote.price > ma5 > ma20:
                            ma_pos = "多头排列，价格在均线上方"
                        elif quote.price < ma5 < ma20:
                            ma_pos = "空头排列，价格在均线下方"
                        else:
                            ma_pos = "均线交织"
                    
                    
                    # 准备技术指标与趋势分析
                    indicators = {}
                    recent_trend = "无数据"
                    
                    if df is not None and not df.empty:
                        # 1. 计算指标 (MACD, RSI, KDJ) - 假设df已包含或简单计算
                        # 均线偏离度
                        ma5 = df['ma5'].iloc[-1] if 'ma5' in df.columns else 0
                        ma20 = df['ma20'].iloc[-1] if 'ma20' in df.columns else 0
                        indicators["MA趋向"] = "多头排列" if ma5 > ma20 else ("空头排列" if ma5 < ma20 else "纠缠")
                        
                        # 量比分析
                        vol_rss = df['volume'].rolling(5).mean()
                        if len(vol_rss) > 0 and vol_rss.iloc[-1] > 0:
                            vol_ratio = df['volume'].iloc[-1] / vol_rss.iloc[-1]
                            indicators["量能状态"] = f"量比{vol_ratio:.2f} ({'放量' if vol_ratio > 1.5 else '缩量' if vol_ratio < 0.8 else '平量'})"
                        
                        # 近期涨跌
                        if len(df) >= 3:
                            pct_3d = (df['close'].iloc[-1] / df['close'].iloc[-3] - 1) * 100
                            recent_trend = f"3日涨跌{pct_3d:+.2f}%"
                            if abs(pct_3d) > 5:
                                recent_trend += " (短期波动大)"
                        
                        # 简单MACD模拟 (如果有columns则用)
                        if 'diff' in df.columns and 'dea' in df.columns:
                            diff = df['diff'].iloc[-1]
                            dea = df['dea'].iloc[-1]
                            indicators["MACD"] = "金叉" if diff > dea else "死叉"
                        
                        # RSI (简化计算)
                        if len(df) > 14:
                            delta = df['close'].diff()
                            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                            rs = gain / loss
                            rsi = 100 - (100 / (1 + rs)).iloc[-1]
                            indicators["RSI(14)"] = f"{rsi:.1f} ({'超买' if rsi>80 else '超卖' if rsi<20 else '中性'})"

                    # 使用流式AI分析
                    from src.strategy.ai_analyzer import ai_analyzer, StockContext
                    
                    context = StockContext(
                        code=code,
                        name=quote.name,
                        price=quote.price,
                        change_pct=quote.change_pct,
                        volume=quote.volume,
                        amount=quote.amount,
                        high=quote.high,
                        low=quote.low,
                        open_price=quote.open,
                        pre_close=quote.pre_close,
                        signals=signals,
                        patterns=patterns,
                        pressure=pressure_text,
                        fund_flow="详见下方资金流向",
                        ma_position=ma_pos,
                        indicators=indicators,
                        recent_trend=recent_trend
                    )
                    
                    # 流式输出显示
                    result_placeholder = st.empty()
                    accumulated_text = ""
                    
                    for chunk in ai_analyzer.analyze_stream(context):
                        accumulated_text += chunk
                        result_placeholder.markdown(accumulated_text + "▌")
                    
                    # 移除光标
                    result_placeholder.markdown(accumulated_text)
                    
                    st.session_state.ai_analysis_result = accumulated_text
                    st.session_state.ai_analysis_code = code
                    
                except Exception as e:
                    st.session_state.ai_analysis_result = f"分析失败: {str(e)}"
    
    with col1:
        # 显示结果（非流式时使用缓存）
        if st.session_state.ai_analysis_result and st.session_state.ai_analysis_code == code:
            if not st.session_state.get('_streaming_active'):
                st.markdown(st.session_state.ai_analysis_result)
        else:
            st.caption("点击按钮，让AI为您分析当前股票走势...")


def _init_signal_timeline(code: str):
    """初始化信号流水表"""
    if 'signal_timeline' not in st.session_state:
        st.session_state.signal_timeline = []
    if 'timeline_code' not in st.session_state:
        st.session_state.timeline_code = code
    elif st.session_state.timeline_code != code:
        st.session_state.signal_timeline = []
        st.session_state.timeline_code = code


def _add_signal(signal_type: str, message: str, direction: str = "hold"):
    """添加信号到流水表（限制10条，避免无限增长）"""
    timeline = st.session_state.signal_timeline
    now = datetime.now().strftime('%H:%M:%S')
    
    # 避免重复添加相同信号
    if timeline and timeline[0]['类型'] == signal_type and timeline[0]['信号'] == message:
        return
    
    direction_map = {'buy': '🟢买', 'sell': '🔴卖', 'hold': '⚪观望'}
    
    timeline.insert(0, {
        '时间': now,
        '方向': direction_map.get(direction, '⚪'),
        '类型': signal_type,
        '信号': message
    })
    
    # 只保留最近10条
    st.session_state.signal_timeline = timeline[:10]


def _render_realtime_signals(code: str, df: pd.DataFrame, quote):
    """渲染实时信号区域"""
    st.markdown("### 📡 实时信号")
    
    from src.strategy.signals.realtime_strategy import realtime_strategy
    from src.strategy.signals.intraday_pattern import analyze_intraday_patterns, intraday_analyzer
    from src.strategy.signals.big_order_tracker import get_buy_sell_pressure
    from src.data.collectors.realtime_service import get_intraday_data
    
    # 设置均线数据（安全处理）
    try:
        if df is not None and not df.empty and 'ma5' in df.columns and 'ma10' in df.columns and 'ma20' in df.columns:
            realtime_strategy.set_ma_data(code, df['ma5'].iloc[-1], df['ma10'].iloc[-1], df['ma20'].iloc[-1])
    except Exception:
        pass
    
    # 获取实时信号
    try:
        avg_volume = df['volume'].rolling(5).mean().iloc[-1] if df is not None and 'volume' in df.columns else None
    except Exception:
        avg_volume = None
    rt_signals = realtime_strategy.generate_signals(code, avg_volume)
    
    # 获取分时形态
    intraday_df = get_intraday_data(code, datalen=48)
    pt_signals = analyze_intraday_patterns(intraday_df, quote.pre_close) if not intraday_df.empty else []
    
    # 获取买卖压力
    pressure = get_buy_sell_pressure(code)
    
    # 添加到流水表
    for s in rt_signals:
        _add_signal(s.signal_type.value, s.message, 'buy' if s.confidence > 70 else 'hold')
    for s in pt_signals:
        _add_signal(s.pattern.value, s.message, s.direction)
    
    # 显示交易建议
    advice = intraday_analyzer.get_trading_advice(pt_signals)
    action_map = {'buy': '🟢 建议买入', 'sell': '🔴 建议卖出', 'hold': '⏸️ 建议观望'}
    st.info(f"**{action_map.get(advice['action'], '⏸️ 观望')}** (置信度 {advice['confidence']}%)")
    
    # 显示买卖压力
    if pressure:
        pressure_text = {'buy_strong': '🟢 买盘强势', 'sell_strong': '🔴 卖盘强势', 'balanced': '⚖️ 多空均衡'}
        st.caption(f"买卖压力: {pressure_text.get(pressure.pressure, '均衡')} ({pressure.bid_ratio:.0%})")
    
    # 显示当前触发的信号
    all_signals = rt_signals + pt_signals
    if all_signals:
        for s in all_signals[:3]:
            if hasattr(s, 'signal_type'):
                st.success(f"**{s.signal_type.value}**: {s.message}")
            else:
                st.success(f"**{s.pattern.value}**: {s.message}")
    else:
        st.caption("暂无明显信号")


def _render_signal_timeline_table():
    """渲染信号流水表"""
    st.markdown("### 📝 信号流水")
    
    timeline = st.session_state.signal_timeline
    
    if not timeline:
        st.caption("等待信号触发...")
        return
    
    timeline_df = pd.DataFrame(timeline)
    st.dataframe(
        timeline_df,
        use_container_width=True,
        hide_index=True,
        height=200
    )


def _render_top_dashboard(quote):
    """顶部实时看板"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    color = "normal" if quote.change_pct >= 0 else "inverse"
    
    with col1:
        st.metric("实时价格", f"¥{quote.price:.2f}", f"{quote.change_pct:+.2f}%", delta_color=color)
    with col2:
        st.metric("今开", f"¥{quote.open:.2f}")
    with col3:
        st.metric("最高/最低", f"{quote.high:.2f} / {quote.low:.2f}")
    with col4:
        st.metric("成交量", f"{quote.volume/10000:.0f}万手")
    with col5:
        st.metric("成交额", f"{quote.amount/100000000:.2f}亿")


def _render_order_book(quote):
    """渲染五档盘口"""
    st.markdown("### 📊 五档盘口")
    
    # 构建数据
    data = []
    for i in range(4, -1, -1):
        if quote.ask_prices[i] > 0:
            data.append({"档位": f"卖{i+1}", "价格": quote.ask_prices[i], "量(手)": quote.ask_volumes[i], "方向": "卖"})
    
    data.append({"档位": "—", "价格": quote.price, "量(手)": 0, "方向": "现价"})
    
    for i in range(5):
        if quote.bid_prices[i] > 0:
            data.append({"档位": f"买{i+1}", "价格": quote.bid_prices[i], "量(手)": quote.bid_volumes[i], "方向": "买"})
    
    book_df = pd.DataFrame(data)
    
    # 使用dataframe显示（简单可靠）
    st.dataframe(
        book_df[["档位", "价格", "量(手)"]],
        use_container_width=True,
        hide_index=True,
        height=300
    )
    
    # 买卖力量
    total_bid = sum(quote.bid_volumes)
    total_ask = sum(quote.ask_volumes)
    total = total_bid + total_ask
    
    if total > 0:
        bid_pct = total_bid / total
        st.progress(bid_pct, text=f"买盘 {bid_pct:.0%} vs 卖盘 {1-bid_pct:.0%}")


def _render_intraday_chart(code: str, quote):
    """分时图"""
    st.markdown("### 📈 分时走势")
    
    from src.data.collectors.realtime_service import get_intraday_data
    
    df = get_intraday_data(code, datalen=48)
    
    if df.empty:
        st.info("分时数据加载中...")
        return

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                      vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    time_col = 'time' if 'time' in df.columns else df.columns[0]
    
    # 价格线
    fig.add_trace(go.Scatter(x=df[time_col], y=df['close'], mode='lines', name='价格',
                            line=dict(color='#1E90FF', width=2)), row=1, col=1)
    
    # 均价线
    avg_price = df['close'].expanding().mean()
    fig.add_trace(go.Scatter(x=df[time_col], y=avg_price, mode='lines', name='均价',
                            line=dict(color='#FFD700', width=1, dash='dash')), row=1, col=1)
    
    # 昨收参考线
    fig.add_hline(y=quote.pre_close, line_dash="dot", line_color="gray", opacity=0.5, row=1, col=1)
    
    # 成交量
    colors = ['#FF4136' if c >= o else '#2ECC40' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(x=df[time_col], y=df['volume'], marker_color=colors, name='成交量'), row=2, col=1)
    
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, xaxis_rangeslider_visible=False)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def _render_position_analysis(user_shares: int, user_cost: float, latest_price: float):
    """渲染用户持仓分析"""
    st.markdown("### 📊 我的持仓")
    
    current_value = user_shares * latest_price
    cost_value = user_shares * user_cost
    profit = current_value - cost_value
    profit_pct = (latest_price / user_cost - 1) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("持仓股数", f"{user_shares:,}股")
    with col2:
        st.metric("买入成本", f"¥{user_cost:.2f}")
    with col3:
        st.metric("当前市值", f"¥{current_value:,.2f}")
    with col4:
        delta_color = "normal" if profit >= 0 else "inverse"
        st.metric("盈亏", f"¥{profit:,.2f}", f"{profit_pct:+.2f}%", delta_color=delta_color)


def _render_fund_flow(ak, stock_code_clean: str):
    """渲染主力资金流向"""
    if not ak:
        st.error("❌ akshare未安装")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📈 个股资金流向（近5日）**")
        try:
            market = "sh" if stock_code_clean.startswith('6') else "sz"
            fund_df = ak.stock_individual_fund_flow(stock=stock_code_clean, market=market)
            if fund_df is not None and not fund_df.empty:
                fund_df_recent = fund_df.tail(5).iloc[::-1]
                display_cols = [col for col in fund_df_recent.columns 
                              if any(x in col for x in ['日期', '主力', '涨跌'])][:6]
                if not display_cols:
                    display_cols = list(fund_df_recent.columns[:6])
                st.dataframe(fund_df_recent[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info("暂无资金流向数据")
        except Exception as e:
            st.info("资金流向数据获取中...")
    
    with col2:
        st.markdown("**🏦 北向资金动向**")
        try:
            north_df = ak.stock_hsgt_north_net_flow_in_em(symbol="北向")
            if north_df is not None and not north_df.empty:
                display_cols = [col for col in north_df.columns 
                              if any(x in col for x in ['日期', '净流入', '当日'])][:3]
                if not display_cols:
                    display_cols = list(north_df.columns[:3])
                st.dataframe(north_df[display_cols].head(5), use_container_width=True, hide_index=True)
        except Exception as e:
            st.info("北向资金数据获取中...")


def _render_signal_aggregation(code: str, df: pd.DataFrame, quote):
    """渲染信号聚合面板"""
    st.markdown("### 📊 多策略信号聚合")
    
    try:
        from src.strategy.signals.signal_aggregator import SignalAggregator
        from src.strategy.signals.intraday_pattern import analyze_intraday_patterns
        from src.data.collectors.realtime_service import get_intraday_data
        
        # 获取分时数据
        intraday_df = get_intraday_data(code)
        
        aggregator = SignalAggregator()
        
        # 1. 分时形态信号
        if not intraday_df.empty:
            signals = analyze_intraday_patterns(intraday_df, quote.pre_close)
            for s in signals:
                signal_type = 'BUY' if s.direction == 'buy' else 'SELL' if s.direction == 'sell' else 'HOLD'
                aggregator.add_signal(
                    strategy_name='intraday_pattern',
                    signal=signal_type,
                    confidence=s.confidence * s.match_quality,
                    reasons=[s.message]
                )
        
        # 2. 涨跌幅信号
        if quote.change_pct > 5:
            aggregator.add_signal('momentum', 'BUY', 70, [f'涨幅强劲 +{quote.change_pct:.1f}%'])
        elif quote.change_pct < -5:
            aggregator.add_signal('momentum', 'SELL', 70, [f'跌幅较大 {quote.change_pct:.1f}%'])
        else:
            aggregator.add_signal('momentum', 'HOLD', 50, ['涨跌幅一般'])
        
        # 3. 量能信号
        if hasattr(quote, 'volume_ratio') and quote.volume_ratio:
            if quote.volume_ratio > 2:
                aggregator.add_signal('volume', 'BUY', 65, [f'放量明显 量比{quote.volume_ratio:.1f}'])
            elif quote.volume_ratio < 0.5:
                aggregator.add_signal('volume', 'HOLD', 55, ['缩量观望'])
        
        # 聚合结果
        result = aggregator.aggregate()
        
        # 显示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            emoji = "🟢" if result.final_signal.value == "BUY" else "🔴" if result.final_signal.value == "SELL" else "🟡"
            st.metric(
                "综合决策",
                f"{emoji} {result.final_signal.value}",
                f"置信度 {result.confidence:.0f}%"
            )
        
        with col2:
            st.metric("买入信号", f"{result.buy_score:.0f}", delta=None)
            st.metric("卖出信号", f"{result.sell_score:.0f}", delta=None)
        
        with col3:
            st.metric("持有信号", f"{result.hold_score:.0f}", delta=None)
            st.caption(result.summary)
        
        # 信号来源详情
        with st.expander("📋 信号来源详情"):
            for sig in result.contributing_signals:
                emoji = "🟢" if sig.signal.value == "BUY" else "🔴" if sig.signal.value == "SELL" else "🟡"
                st.markdown(f"{emoji} **{sig.strategy_name}**: {sig.signal.value} ({sig.confidence:.0f}%)")
                for reason in sig.reasons[:2]:
                    st.caption(f"  └─ {reason}")
                    
    except Exception as e:
        st.warning(f"信号聚合计算失败: {e}")


def _render_analysis_history(code: str):
    """渲染分析历史记录"""
    try:
        from src.data.services.db_service import db_service
        
        history = db_service.get_analysis_history(code, days=30)
        
        if not history:
            st.info("暂无分析历史记录，进行AI分析后将自动保存")
            return
        
        st.markdown(f"**近30天共 {len(history)} 条分析记录**")
        
        # 统计
        buy_count = sum(1 for r in history if r['signal'] == 'BUY')
        sell_count = sum(1 for r in history if r['signal'] == 'SELL')
        hold_count = sum(1 for r in history if r['signal'] == 'HOLD')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("买入信号", f"{buy_count}次", delta=None)
        with col2:
            st.metric("卖出信号", f"{sell_count}次", delta=None)
        with col3:
            st.metric("持有信号", f"{hold_count}次", delta=None)
        
        # 历史表格
        history_data = []
        for r in history[:10]:  # 最近10条
            history_data.append({
                "时间": r['time'].strftime('%m-%d %H:%M'),
                "信号": r['signal'],
                "置信度": f"{r['confidence']:.0f}%",
                "价格": f"{r['price']:.2f}"
            })
        
        if history_data:
            import pandas as pd
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.warning(f"获取分析历史失败: {e}")
