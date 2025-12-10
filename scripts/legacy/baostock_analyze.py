# -*- coding: utf-8 -*-
"""使用Baostock+新浪实时行情分析股票"""
import baostock as bs
import pandas as pd
import requests
import sys

def get_realtime_quote(code):
    """获取新浪实时行情"""
    if code.startswith('6'):
        symbol = f'sh{code}'
    else:
        symbol = f'sz{code}'
    
    url = f'http://hq.sinajs.cn/list={symbol}'
    headers = {'Referer': 'http://finance.sina.com.cn'}
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.text.split('"')[1].split(',')
        
        if len(data) < 32:
            return None
        
        return {
            'name': data[0],
            'open': float(data[1]),
            'pre_close': float(data[2]),
            'price': float(data[3]),
            'high': float(data[4]),
            'low': float(data[5]),
            'volume': float(data[8]) / 100,  # 手
            'amount': float(data[9]),  # 元
            'date': data[30],
            'time': data[31]
        }
    except:
        return None


def analyze_stock(code):
    """分析股票"""
    # 获取实时行情
    realtime = get_realtime_quote(code)
    
    print(f'\n{"="*50}')
    print(f'  {code} 综合分析')
    print(f'{"="*50}\n')
    
    if realtime:
        print(f'【实时行情】 {realtime["date"]} {realtime["time"]}')
        print(f'  股票名称: {realtime["name"]}')
        print(f'  最新价: {realtime["price"]:.2f} 元')
        
        change = (realtime["price"] / realtime["pre_close"] - 1) * 100
        print(f'  涨跌幅: {change:+.2f}%')
        print(f'  今开: {realtime["open"]:.2f}')
        print(f'  最高: {realtime["high"]:.2f}')
        print(f'  最低: {realtime["low"]:.2f}')
        print(f'  成交量: {realtime["volume"]/10000:.0f} 万手')
        print(f'  成交额: {realtime["amount"]/100000000:.2f} 亿')
    else:
        print('【实时行情】获取失败')
    
    # 获取历史数据
    lg = bs.login()
    
    if code.startswith('6'):
        full_code = f'sh.{code}'
    else:
        full_code = f'sz.{code}'
    
    rs = bs.query_history_k_data_plus(
        full_code,
        'date,open,high,low,close,volume,amount,pctChg,turn',
        start_date='2024-06-01',
        end_date='2025-12-31',
        frequency='d',
        adjustflag='2'
    )
    
    df = rs.get_data()
    bs.logout()
    
    if df.empty:
        print('\n历史数据获取失败')
        return
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'pctChg', 'turn']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna().tail(120)
    latest = df.iloc[-1]
    
    print(f'\n【历史数据】截至 {latest["date"]}')
    
    # 均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    print(f'\n【均线系统】')
    print(f'  MA5:  {df["ma5"].iloc[-1]:.2f}')
    print(f'  MA10: {df["ma10"].iloc[-1]:.2f}')
    print(f'  MA20: {df["ma20"].iloc[-1]:.2f}')
    if not pd.isna(df['ma60'].iloc[-1]):
        print(f'  MA60: {df["ma60"].iloc[-1]:.2f}')
    
    # 趋势
    if latest['close'] > df['ma5'].iloc[-1] > df['ma10'].iloc[-1] > df['ma20'].iloc[-1]:
        trend = '🔥 多头排列 (强势)'
    elif latest['close'] < df['ma5'].iloc[-1] < df['ma10'].iloc[-1]:
        trend = '❄️ 空头排列 (弱势)'
    else:
        trend = '⚖️ 震荡整理'
    print(f'  趋势: {trend}')
    
    # 涨停分析
    limit_days = len(df[df['pctChg'] >= 9.5])
    print(f'\n【涨停分析】')
    print(f'  近期涨停次数: {limit_days}次')
    
    # 近期表现
    pct_5d = (latest['close'] / df.iloc[-6]['close'] - 1) * 100 if len(df) > 5 else 0
    pct_20d = (latest['close'] / df.iloc[-21]['close'] - 1) * 100 if len(df) > 20 else 0
    print(f'\n【近期表现】')
    print(f'  近5日: {pct_5d:+.2f}%')
    print(f'  近20日: {pct_20d:+.2f}%')
    
    # 操作建议
    print(f'\n【操作建议】')
    if realtime:
        curr_price = realtime['price']
        change = (curr_price / realtime['pre_close'] - 1) * 100
        
        if change >= 9.5:
            print('  🔥 今日涨停，建议等待回调后再介入')
        elif change <= -9.5:
            print('  ⚠️ 今日跌停，风险极高，回避')
        elif curr_price > df['ma20'].iloc[-1]:
            print('  ✅ 站上20日均线，可关注')
        elif curr_price < df['ma20'].iloc[-1]:
            print('  ⏸️ 在20日均线下方，观望为主')
        else:
            print('  📊 震荡格局，轻仓参与')
    
    print(f'\n{"="*50}\n')


if __name__ == '__main__':
    code = sys.argv[1] if len(sys.argv) > 1 else '000592'
    analyze_stock(code)
