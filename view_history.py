# -*- coding: utf-8 -*-
"""查看分析历史记录"""
import sys
import os
sys.path.insert(0, '.')
os.system('chcp 65001 > nul')

from datetime import datetime

# 股票代码（可通过命令行参数传入）
code = sys.argv[1] if len(sys.argv) > 1 else '000592'

print(f"\n{'='*50}")
print(f"分析历史: {code}")
print(f"{'='*50}")

try:
    from src.data.services.db_service import db_service
    
    history = db_service.get_analysis_history(code, days=30)
    
    if not history:
        print("\n暂无分析历史记录")
    else:
        print(f"\n共 {len(history)} 条记录:\n")
        
        for i, record in enumerate(history, 1):
            date_str = record['time'].strftime('%Y-%m-%d %H:%M')
            signal = record['signal']
            confidence = record['confidence']
            price = record['price']
            
            # 信号颜色标记
            if signal == 'BUY':
                signal_mark = "[买入]"
            elif signal == 'SELL':
                signal_mark = "[卖出]"
            else:
                signal_mark = "[持有]"
            
            print(f"{i}. {date_str} | {signal_mark} {confidence:.0f}% | 价格: {price:.2f}")
            
            # 显示AI摘要（前100字）
            ai_response = record.get('ai_response', '')
            if ai_response:
                # 提取核心研判
                if '**核心研判**' in ai_response:
                    start = ai_response.find('**核心研判**')
                    end = ai_response.find('\n', start + 20)
                    if end > start:
                        summary = ai_response[start:end].replace('**核心研判**:', '').strip()
                        print(f"   {summary[:60]}")
            print()
        
        # 统计信号分布
        buy_count = sum(1 for r in history if r['signal'] == 'BUY')
        sell_count = sum(1 for r in history if r['signal'] == 'SELL')
        hold_count = sum(1 for r in history if r['signal'] == 'HOLD')
        
        print(f"{'='*50}")
        print(f"信号统计: 买入{buy_count}次 | 卖出{sell_count}次 | 持有{hold_count}次")
        
except Exception as e:
    print(f"获取历史失败: {e}")
