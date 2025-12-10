# -*- coding: utf-8 -*-
"""
AI智能分析服务
使用Groq API（默认）进行股票综合分析
"""
from dataclasses import dataclass, field
from typing import Optional, Dict

# 从配置文件读取Groq设置
try:
    from config.settings import Settings
    GROQ_API_KEY = Settings.groq.api_key
    GROQ_MODEL = Settings.groq.model
    GROQ_MAX_TOKENS = Settings.groq.max_tokens
except ImportError:
    GROQ_API_KEY = ""
    GROQ_MODEL = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS = 1024


@dataclass
class StockContext:
    """股票上下文数据"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    high: float
    low: float
    open_price: float
    pre_close: float
    signals: list
    patterns: list
    pressure: str
    fund_flow: str
    ma_position: str
    # 技术指标
    indicators: Dict[str, str] = field(default_factory=dict)
    recent_trend: str = "无数据"
    # 新增: 历史数据分析
    historical_summary: str = ""  # 5日/20日趋势摘要
    support_level: float = 0.0   # 支撑位
    resistance_level: float = 0.0  # 压力位
    volume_ratio: float = 1.0    # 量比
    macd_signal: str = ""        # MACD信号 (金叉/死叉)
    rsi_value: float = 50.0      # RSI数值


class AIAnalyzer:
    """Groq AI分析器"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化Groq客户端"""
        if not GROQ_API_KEY:
            print("警告: 未配置Groq API Key")
            return
            
        try:
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            print("请安装groq库: pip install groq")
        except Exception as e:
            print(f"Groq初始化失败: {e}")
    
    def analyze(self, context: StockContext) -> str:
        """对股票进行综合AI分析"""
        if not self.client:
            return "⚠️ AI服务未配置，请检查config/settings.py中的Groq API Key"
        
        prompt = self._build_prompt(context)
        
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=GROQ_MAX_TOKENS
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ AI分析请求失败: {str(e)}"
    
    def analyze_stream(self, context: StockContext):
        """
        流式AI分析 - 返回生成器，逐字输出
        
        用法 (Streamlit):
            for chunk in ai_analyzer.analyze_stream(context):
                placeholder.markdown(accumulated_text + chunk)
        """
        if not self.client:
            yield "⚠️ AI服务未配置"
            return
        
        prompt = self._build_prompt(context)
        
        try:
            stream = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=GROQ_MAX_TOKENS,
                stream=True  # 启用流式输出
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"⚠️ AI分析请求失败: {str(e)}"
    
    def _build_prompt(self, ctx: StockContext) -> str:
        """构建分析提示词"""
        signals_text = "、".join(ctx.signals) if ctx.signals else "无"
        patterns_text = "、".join(ctx.patterns) if ctx.patterns else "无"
        
        # 格式化技术指标
        tech_text = ""
        if ctx.indicators:
            tech_lines = [f"- {k}: {v}" for k, v in ctx.indicators.items()]
            tech_text = "\n".join(tech_lines)
        
        # 构建历史数据部分
        hist_text = ""
        if ctx.historical_summary:
            hist_text = f"- 历史趋势: {ctx.historical_summary}"
        if ctx.macd_signal:
            hist_text += f"\n- MACD: {ctx.macd_signal}"
        if ctx.rsi_value != 50.0:
            rsi_status = "超买" if ctx.rsi_value > 70 else "超卖" if ctx.rsi_value < 30 else "中性"
            hist_text += f"\n- RSI(14): {ctx.rsi_value:.1f} ({rsi_status})"
        if ctx.volume_ratio != 1.0:
            hist_text += f"\n- 量比: {ctx.volume_ratio:.2f}"
        
        # 支撑压力位
        level_text = ""
        if ctx.support_level > 0:
            level_text = f"\n- 支撑位: {ctx.support_level:.2f}"
        if ctx.resistance_level > 0:
            level_text += f"\n- 压力位: {ctx.resistance_level:.2f}"
        
        prompt = f"""你是一位专业的A股短线交易员。请结合【实时盘口】、【技术指标】和【历史趋势】，给出实战操作建议。

## 1. 实时盘面
- 股票: {ctx.name} ({ctx.code})
- 现价: {ctx.price:.2f} ({ctx.change_pct:+.2f}%)
- 状态: 最高{ctx.high}/最低{ctx.low}/昨收{ctx.pre_close}
- 成交: {(ctx.volume/10000):.0f}万手 / {(ctx.amount/100000000):.1f}亿
- 资金: {ctx.fund_flow}
- 压力: {ctx.pressure}

## 2. 技术信号
- 触发信号: {signals_text}
- 分时形态: {patterns_text}
{tech_text}
- 均线位置: {ctx.ma_position}
- 近期趋势: {ctx.recent_trend}
{hist_text}
{level_text}

## 请输出分析报告 (严格按此格式):

**核心研判**: [Strong/Weak/Neutral] 一句话定性

**逻辑支撑**:
1. [技术面依据]
2. [资金面依据]
3. [形态依据]

**交易策略**:
- 开盘策略: [竞价高开/低开应对]
- 盘中策略: [做T/加仓/减仓时机]
- 尾盘策略: [持有/离场条件]

**仓位建议**: [轻仓XX%/半仓/重仓]

**风控点位**: 
- 止损: XX.XX
- 止盈: XX.XX

要求：站在短线交易员角度，给出可执行的操作建议，中文回答，250字以内。"""
        
        return prompt


# 全局实例
ai_analyzer = AIAnalyzer()


def analyze_stock(
    code: str,
    name: str,
    price: float,
    change_pct: float,
    volume: float = 0,
    amount: float = 0,
    high: float = 0,
    low: float = 0,
    open_price: float = 0,
    pre_close: float = 0,
    signals: list = None,
    patterns: list = None,
    pressure: str = "均衡",
    fund_flow: str = "无数据",
    ma_position: str = "无数据",
    indicators: dict = None,
    recent_trend: str = "无数据",
    # 新增历史数据参数
    historical_summary: str = "",
    support_level: float = 0.0,
    resistance_level: float = 0.0,
    volume_ratio: float = 1.0,
    macd_signal: str = "",
    rsi_value: float = 50.0
) -> str:
    """便捷函数：分析股票"""
    context = StockContext(
        code=code,
        name=name,
        price=price,
        change_pct=change_pct,
        volume=volume,
        amount=amount,
        high=high,
        low=low,
        open_price=open_price,
        pre_close=pre_close,
        signals=signals or [],
        patterns=patterns or [],
        pressure=pressure,
        fund_flow=fund_flow,
        ma_position=ma_position,
        indicators=indicators or {},
        recent_trend=recent_trend,
        historical_summary=historical_summary,
        support_level=support_level,
        resistance_level=resistance_level,
        volume_ratio=volume_ratio,
        macd_signal=macd_signal,
        rsi_value=rsi_value
    )
    return ai_analyzer.analyze(context)
