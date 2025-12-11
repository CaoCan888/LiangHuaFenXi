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
    # P1新增: 用户持仓信息
    user_cost: float = 0.0       # 用户持仓成本
    user_shares: int = 0         # 用户持仓股数
    # P2新增: 增强数据
    bid_volumes: list = field(default_factory=list)   # 买1-5挂单量
    ask_volumes: list = field(default_factory=list)   # 卖1-5挂单量
    news_titles: list = field(default_factory=list)   # 近期新闻标题
    market_regime: str = "中性"   # 市场状态


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
        
        # 用户持仓信息
        position_text = ""
        if ctx.user_cost > 0:
            pnl_pct = (ctx.price / ctx.user_cost - 1) * 100
            position_text = f"""
## 3. 用户持仓
- 持仓成本: {ctx.user_cost:.2f}
- 持仓数量: {ctx.user_shares}股
- 当前盈亏: {pnl_pct:+.2f}%
- 状态: {'盈利中' if pnl_pct > 0 else '亏损中' if pnl_pct < 0 else '持平'}
"""
        
        # 盘口数据
        l2_text = ""
        if ctx.bid_volumes and ctx.ask_volumes:
            bid_total = sum(ctx.bid_volumes)
            ask_total = sum(ctx.ask_volumes)
            ratio = bid_total / ask_total if ask_total > 0 else 1
            l2_text = f"""
## 4. 五档盘口
- 卖盘挂单: {ask_total}手 (卖1-5)
- 买盘挂单: {bid_total}手 (买1-5)
- 买卖比: {ratio:.2f} ({'买盘强' if ratio > 1.2 else '卖盘强' if ratio < 0.8 else '均衡'})
"""
        
        # 新闻标题
        news_text = ""
        if ctx.news_titles:
            titles = ctx.news_titles[:3]  # 最多3条
            news_text = f"""
## 5. 近期新闻
{chr(10).join(['- ' + t for t in titles])}
"""
        
        # 市场状态
        regime_text = f"\n## 6. 市场环境: {ctx.market_regime}" if ctx.market_regime != "中性" else ""
        
        prompt = f"""你是一位专业的A股短线交易员。请分析以下数据并给出建议。

**重要**: A股实行T+1，今天买入明天才能卖出。

## 1. 实时盘面
- 股票: {ctx.name} ({ctx.code})
- 现价: {ctx.price:.2f} ({ctx.change_pct:+.2f}%)
- 最高/最低/昨收: {ctx.high}/{ctx.low}/{ctx.pre_close}
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
{position_text}
{l2_text}
{news_text}
{regime_text}

## 请严格按以下JSON格式输出 (只输出JSON，不要其他文字):

```json
{{
  "verdict": "BUY或SELL或HOLD",
  "confidence": 0到100的整数,
  "core_logic": "一句话核心判断理由",
  "today_action": "今日操作建议",
  "tomorrow_predict": "明日走势预判",
  "stop_loss": 止损价格数字,
  "take_profit": 止盈价格数字,
  "position_size": "轻仓30%或半仓50%或重仓70%",
  "risk_warning": "主要风险提示"
}}
```

要求：verdict必须是BUY/SELL/HOLD之一，stop_loss和take_profit必须是具体数字。"""
        
        return prompt
    
    def parse_ai_response(self, response: str) -> dict:
        """解析AI的JSON响应"""
        import json
        import re
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试找到 { 开头的JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # 解析失败，返回默认结构
        return {
            "verdict": "HOLD",
            "confidence": 50,
            "core_logic": "AI响应解析失败",
            "today_action": response[:100] if response else "无数据",
            "tomorrow_predict": "无法预测",
            "stop_loss": 0,
            "take_profit": 0,
            "position_size": "观望",
            "risk_warning": "AI响应格式异常",
            "_raw_response": response
        }
    
    def analyze_structured(self, context: StockContext) -> dict:
        """结构化分析 - 返回解析后的dict"""
        raw_response = self.analyze(context)
        return self.parse_ai_response(raw_response)


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
