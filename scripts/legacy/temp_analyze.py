# -*- coding: utf-8 -*-
"""临时分析脚本"""
import akshare as ak
import pandas as pd

code = '601933'
print(f'\n========== 601933 永辉超市 综合分析 ==========\n')

# 获取日K线数据
df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
df = df.tail(120)
df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover']

latest = df.iloc[-1]
prev = df.iloc[-2]

print(f'最新价: {latest["close"]:.2f} 元')
print(f'今日涨跌: {latest["pct_change"]:.2f}%')
print(f'成交量: {latest["volume"]/10000:.0f} 万手')
print(f'成交额: {latest["amount"]/100000000:.2f} 亿')
print(f'换手率: {latest["turnover"]:.2f}%')

# 计算均线
df['ma5'] = df['close'].rolling(5).mean()
df['ma10'] = df['close'].rolling(10).mean()
df['ma20'] = df['close'].rolling(20).mean()
df['ma60'] = df['close'].rolling(60).mean()

print(f'\n--- 均线系统 ---')
print(f'MA5: {df["ma5"].iloc[-1]:.2f}')
print(f'MA10: {df["ma10"].iloc[-1]:.2f}')
print(f'MA20: {df["ma20"].iloc[-1]:.2f}')
print(f'MA60: {df["ma60"].iloc[-1]:.2f}')

# 趋势判断
if latest['close'] > df['ma5'].iloc[-1] > df['ma10'].iloc[-1] > df['ma20'].iloc[-1]:
    trend = '多头排列 (强势)'
elif latest['close'] < df['ma5'].iloc[-1] < df['ma10'].iloc[-1]:
    trend = '空头排列 (弱势)'
else:
    trend = '震荡整理'
print(f'趋势: {trend}')

# 涨停检测
is_limit_up = latest['pct_change'] >= 9.5
print(f'\n--- 涨停分析 ---')
print(f'今日涨停: {"是" if is_limit_up else "否"}')

# 近期涨停次数
limit_days = df[df['pct_change'] >= 9.5]
print(f'近120日涨停次数: {len(limit_days)}次')

# 量能分析
vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
vol_ratio = latest['volume'] / vol_ma5
print(f'\n--- 量能分析 ---')
print(f'量比: {vol_ratio:.2f}')
if vol_ratio > 2:
    vol_status = '放量 (资金活跃)'
elif vol_ratio < 0.5:
    vol_status = '缩量 (观望)'
else:
    vol_status = '量能正常'
print(f'状态: {vol_status}')

# 近期表现
pct_5d = (latest['close'] / df.iloc[-6]['close'] - 1) * 100
pct_20d = (latest['close'] / df.iloc[-21]['close'] - 1) * 100
print(f'\n--- 近期表现 ---')
print(f'近5日涨幅: {pct_5d:+.2f}%')
print(f'近20日涨幅: {pct_20d:+.2f}%')

# 操作建议
print(f'\n--- 操作建议 ---')
if is_limit_up:
    advice = '今日涨停，建议等待回调后再介入'
elif latest['close'] > df['ma20'].iloc[-1] and vol_ratio > 1.5:
    advice = '站上20日均线且放量，可关注'
elif latest['close'] < df['ma20'].iloc[-1]:
    advice = '在20日均线下方，观望为主'
else:
    advice = '震荡格局，轻仓参与'
print(advice)
