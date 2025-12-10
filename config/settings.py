# -*- coding: utf-8 -*-
"""
Stock Analysis System - Configuration Settings
系统配置文件 (安全增强版：使用环境变量)
"""

import os
from dataclasses import dataclass
from typing import Optional

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果未安装dotenv，则使用默认值


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = os.getenv("DB_HOST", "47.116.3.95")
    port: int = int(os.getenv("DB_PORT", "3306"))
    username: str = os.getenv("DB_USER", "Afenxi")
    password: str = os.getenv("DB_PASSWORD", "")
    database: str = os.getenv("DB_NAME", "stock_analysis")
    charset: str = "utf8mb4"
    
    @property
    def connection_string(self) -> str:
        """获取SQLAlchemy连接字符串"""
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


@dataclass
class ITickConfig:
    """iTick API配置"""
    api_token: str = os.getenv("ITICK_API_TOKEN", "")
    base_url: str = "https://api.itick.org"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class GroqConfig:
    """Groq AI配置"""
    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = "llama-3.1-8b-instant"
    max_tokens: int = 1024


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    log_dir: str = "logs"
    rotation: str = "10 MB"
    retention: str = "30 days"


@dataclass
class AlertConfig:
    """预警配置"""
    email_enabled: bool = False
    email_host: str = "smtp.qq.com"
    email_port: int = 465
    email_username: str = ""
    email_password: str = ""
    email_receivers: list = None
    
    def __post_init__(self):
        if self.email_receivers is None:
            self.email_receivers = []


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000.0  # 初始资金100万
    commission_rate: float = 0.0003  # 手续费率 0.03%
    slippage: float = 0.001  # 滑点 0.1%
    min_trade_unit: int = 100  # 最小交易单位（股）


class Settings:
    """系统设置"""
    
    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 数据目录
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    # 配置实例
    database = DatabaseConfig()
    itick = ITickConfig()
    groq = GroqConfig()
    log = LogConfig()
    alert = AlertConfig()
    backtest = BacktestConfig()
    
    # 技术指标默认参数
    INDICATOR_PARAMS = {
        "ma": {
            "short": 5,
            "medium": 20,
            "long": 60
        },
        "macd": {
            "fast": 12,
            "slow": 26,
            "signal": 9
        },
        "rsi": {
            "period": 14
        },
        "bollinger": {
            "period": 20,
            "std_dev": 2
        },
        "kdj": {
            "k_period": 9,
            "d_period": 3,
            "j_period": 3
        }
    }
    
    # 技术评分权重配置（可自定义调整）
    TECHNICAL_SCORE_WEIGHTS = {
        'ma_score': 0.20,      # 均线系统评分权重
        'macd_score': 0.15,    # MACD评分权重
        'rsi_score': 0.15,     # RSI评分权重
        'volume_score': 0.15,  # 量能评分权重
        'trend_score': 0.20,   # 趋势评分权重
        'pattern_score': 0.15  # 形态评分权重
    }
    
    # 涨跌幅限制配置
    LIMIT_THRESHOLDS = {
        'normal': 0.10,     # 普通A股 10%
        'gem': 0.20,        # 创业板 (30开头) 20%
        'star': 0.20,       # 科创板 (68开头) 20%
        'st': 0.05,         # ST股 5%
    }


# 创建全局配置实例
settings = Settings()
