# -*- coding: utf-8 -*-
"""
交易建议生成器 - 为小白提供操作指南
增强版：使用ATR动态计算止损止盈
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


class TradingAdvisor:
    """交易建议生成器 (ATR动态止损版)"""
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """
        计算ATR (Average True Range) 平均真实波幅
        
        Args:
            df: 包含high, low, close的DataFrame
            period: ATR周期，默认14
            
        Returns:
            ATR值 (绝对价格)
        """
        if len(df) < period + 1:
            # 数据不足时使用简化计算
            return (df['high'] - df['low']).mean()
        
        # 计算True Range
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) else (df['high'] - df['low']).mean()
    
    def calculate_dynamic_stop_loss(self, df: pd.DataFrame, atr_multiplier: float = 2.0) -> float:
        """
        基于ATR计算动态止损价
        
        Args:
            df: K线数据
            atr_multiplier: ATR倍数，默认2倍（波动大的股票会更宽）
            
        Returns:
            止损价格
        """
        latest_close = df['close'].iloc[-1]
        atr = self.calculate_atr(df)
        stop_loss = latest_close - (atr * atr_multiplier)
        return max(stop_loss, latest_close * 0.90)  # 最低不超过10%止损
    
    def calculate_dynamic_take_profit(self, df: pd.DataFrame, atr_multiplier: float = 3.0) -> float:
        """
        基于ATR计算动态止盈价
        
        Args:
            df: K线数据
            atr_multiplier: ATR倍数，默认3倍（盈亏比1.5:1）
            
        Returns:
            止盈价格
        """
        latest_close = df['close'].iloc[-1]
        atr = self.calculate_atr(df)
        take_profit = latest_close + (atr * atr_multiplier)
        return take_profit
    
    def generate_advice(self, df: pd.DataFrame, scores: Dict = None, stock_code: str = "") -> Dict[str, Any]:
        """
        生成综合交易建议
        
        Args:
            df: K线数据 (需包含limit_streak, pct_change等)
            scores: 技术评分结果
            stock_code: 股票代码 (用于板块联动分析)
            
        Returns:
            交易建议字典
        """
        if len(df) < 5:
            return {'error': '数据不足'}
        
        latest = df.iloc[-1]
        advice = {
            'action': 'HOLD',  # BUY, SELL, HOLD
            'confidence': 0,   # 0-100
            'reasons': [],
            'risks': [],
            'strategy': '',
            't_plus_0': None,  # 做T建议
            'stop_loss': None,
            'take_profit': None,
            'sector_boost': 0.0,  # 板块联动加成
        }
        
        # 板块联动分析
        if stock_code:
            try:
                from src.strategy.signals.sector_analyzer import sector_analyzer
                sector_result = sector_analyzer.analyze(stock_code)
                advice['sector_boost'] = sector_result.limit_continuation_boost
                if sector_result.limit_continuation_boost > 0:
                    advice['reasons'].append(f"板块{sector_result.sector_strength}，连板加成+{sector_result.limit_continuation_boost*100:.0f}%")
            except Exception:
                pass
        
        # 获取关键指标
        is_limit_up = latest.get('is_limit_up', False)
        limit_streak = int(latest.get('limit_streak', 0))
        pct_change = latest.get('pct_change', 0)
        volume_ratio = latest.get('volume_ratio', 1)
        
        # 根据连板数生成建议
        if limit_streak >= 5:
            advice['action'] = 'SELL'
            advice['confidence'] = 85
            advice['reasons'].append(f'已连续{limit_streak}板，高位风险极大')
            advice['risks'].append('随时可能炸板，一旦跌停损失惨重')
            advice['strategy'] = '清仓观望'
            advice['t_plus_0'] = {
                'type': '高抛',
                'entry': '集合竞价高开冲高后',
                'exit_time': '10:00前',
                'note': '不追高，只做T抛售'
            }
        elif limit_streak == 4:
            advice['action'] = 'SELL'
            advice['confidence'] = 75
            advice['reasons'].append('四连板，接力风险很高')
            advice['risks'].append('炸板概率增加，资金出逃迹象')
            advice['strategy'] = '减仓为主，保留底仓做T'
            advice['t_plus_0'] = {
                'type': '高抛低吸',
                'entry': '早盘冲高时抛出50%',
                'exit_time': '尾盘回落时接回',
                'note': '设好止损'
            }
        elif limit_streak == 3:
            advice['action'] = 'HOLD'
            advice['confidence'] = 60
            advice['reasons'].append('三连板，观察资金态度')
            advice['risks'].append('分歧加大，注意量能变化')
            advice['strategy'] = '持股待涨，设置止盈止损'
            advice['stop_loss'] = self.calculate_dynamic_stop_loss(df, atr_multiplier=1.5)
            advice['take_profit'] = self.calculate_dynamic_take_profit(df, atr_multiplier=2.5)
            advice['t_plus_0'] = {
                'type': '高抛低吸',
                'entry': '分时高点卖出1/3',
                'exit_time': '回踩均线接回',
                'note': '保持仓位灵活'
            }
        elif limit_streak == 2:
            advice['action'] = 'HOLD'
            advice['confidence'] = 55
            advice['reasons'].append('二连板，关注是否能走出三板')
            advice['risks'].append('明日分歧，可能开板')
            advice['strategy'] = '持股，明日竞价决策'
            advice['stop_loss'] = self.calculate_dynamic_stop_loss(df, atr_multiplier=2.0)
            advice['take_profit'] = self.calculate_dynamic_take_profit(df, atr_multiplier=3.0)
            advice['t_plus_0'] = {
                'type': '做T',
                'entry': '早盘冲高卖出部分',
                'exit_time': '回落低吸',
                'note': '降低成本'
            }
        elif limit_streak == 1:
            advice['action'] = 'HOLD'
            advice['confidence'] = 50
            advice['reasons'].append('首板，关注封单量和板块效应')
            advice['risks'].append('可能一日游，次日低开')
            advice['strategy'] = '观察次日竞价，低开减仓'
            advice['stop_loss'] = self.calculate_dynamic_stop_loss(df, atr_multiplier=2.5)
            advice['t_plus_0'] = {
                'type': '不做T',
                'entry': '观察',
                'exit_time': '-',
                'note': '等待确认'
            }
        elif is_limit_up == False and pct_change and pct_change > 0.05:
            advice['action'] = 'HOLD'
            advice['confidence'] = 45
            advice['reasons'].append('大涨但未涨停，有上攻意愿')
            advice['strategy'] = '观望，等待涨停确认'
        else:
            # 根据技术评分给建议
            if scores and scores.get('total_score', 50) >= 70:
                advice['action'] = 'BUY'
                advice['confidence'] = 60
                advice['reasons'].append(f'技术评分高: {scores["total_score"]:.0f}分')
                advice['strategy'] = '轻仓试探'
                advice['stop_loss'] = self.calculate_dynamic_stop_loss(df, atr_multiplier=2.0)
                advice['take_profit'] = self.calculate_dynamic_take_profit(df, atr_multiplier=3.0)
            elif scores and scores.get('total_score', 50) <= 40:
                advice['action'] = 'SELL'
                advice['confidence'] = 55
                advice['reasons'].append(f'技术评分低: {scores["total_score"]:.0f}分')
                advice['strategy'] = '回避观望'
            else:
                advice['action'] = 'HOLD'
                advice['confidence'] = 40
                advice['reasons'].append('暂无明确信号')
                advice['strategy'] = '观望等待'
        
        # 添加量能分析
        if volume_ratio and volume_ratio > 3:
            advice['reasons'].append(f'放量明显(量比{volume_ratio:.1f})')
        elif volume_ratio and volume_ratio < 0.5:
            advice['risks'].append('缩量，追高需谨慎')
        
        return advice
    
    def get_action_emoji(self, action: str) -> str:
        """获取操作对应的表情"""
        return {
            'BUY': '🟢 买入',
            'SELL': '🔴 卖出/减仓',
            'HOLD': '🟡 持有/观望'
        }.get(action, '⚪ 未知')
    
    def format_advice(self, advice: Dict) -> str:
        """格式化建议为文本"""
        lines = []
        lines.append(f"【操作建议】{self.get_action_emoji(advice['action'])}")
        lines.append(f"置信度: {advice['confidence']}%")
        lines.append(f"策略: {advice['strategy']}")
        
        if advice['reasons']:
            lines.append("理由:")
            for r in advice['reasons']:
                lines.append(f"  • {r}")
        
        if advice['risks']:
            lines.append("风险提示:")
            for r in advice['risks']:
                lines.append(f"  ⚠️ {r}")
        
        if advice['stop_loss']:
            lines.append(f"止损价: ¥{advice['stop_loss']:.2f}")
        
        if advice['take_profit']:
            lines.append(f"止盈价: ¥{advice['take_profit']:.2f}")
        
        if advice['t_plus_0']:
            t = advice['t_plus_0']
            lines.append(f"做T建议: {t['type']}")
            lines.append(f"  进场: {t['entry']}")
            lines.append(f"  时机: {t['exit_time']}")
            lines.append(f"  备注: {t['note']}")
        
        return '\n'.join(lines)


# 创建全局实例
trading_advisor = TradingAdvisor()
