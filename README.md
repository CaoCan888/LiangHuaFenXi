# 股票分析系统 README

## 项目概述

基于Python的股票分析系统，支持数据获取、技术分析、基本面分析、可视化和策略回测。

## 快速开始

### 1. 安装依赖

```bash
cd d:\AI\lianghuafenxi
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python main.py initdb
```

### 3. 使用方式

**获取数据:**
```bash
python main.py fetch --stock HK.00700 --days 120
```

**技术分析:**
```bash
python main.py analyze --stock HK.00700
```

**策略回测:**
```bash
python main.py backtest --stock HK.00700 --strategy combined
```

**启动Web仪表盘:**
```bash
python main.py dashboard
```

**启动API服务:**
```bash
python main.py api
```

## 项目结构

```
stock_analysis_system/
├── config/              # 配置（iTick API、MySQL）
├── src/
│   ├── data/            # 数据层（收集、处理、存储）
│   ├── analysis/        # 分析（技术指标、基本面）
│   ├── strategy/        # 策略（信号、回测、组合）
│   ├── visualization/   # 可视化（图表、仪表盘）
│   ├── core/            # 核心（引擎、预警、API）
│   └── utils/           # 工具
├── tests/               # 测试
├── main.py              # CLI入口
└── requirements.txt     # 依赖
```

## 主要功能

- **数据获取**: iTick API获取港股/美股/A股K线数据
- **技术指标**: MA、MACD、RSI、布林带、KDJ、ATR等
- **K线形态**: 十字星、锤子线、吞没形态、早晨之星等
- **策略回测**: MA交叉、MACD、RSI等策略
- **可视化**: Plotly交互式图表、Streamlit仪表盘
- **API服务**: Flask REST API

## 配置说明

数据库和API配置在 `config/settings.py`:
- 数据库: 47.116.3.95:3306
- iTick API Token: 已配置
