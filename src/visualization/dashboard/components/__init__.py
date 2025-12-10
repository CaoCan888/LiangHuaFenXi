# -*- coding: utf-8 -*-
"""
组件包初始化
"""
from .tab_realtime import render_realtime_tab
from .tab_chart import render_chart_tab
from .tab_score import render_score_tab
from .tab_limit import render_limit_tab
from .tab_chan import render_chan_tab
from .tab_dragon import render_dragon_tab
from .tab_backtest import render_backtest_tab

__all__ = [
    'render_realtime_tab',
    'render_chart_tab', 
    'render_score_tab',
    'render_limit_tab',
    'render_chan_tab',
    'render_dragon_tab',
    'render_backtest_tab'
]
