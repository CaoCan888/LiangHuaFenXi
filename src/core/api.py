# -*- coding: utf-8 -*-
"""
Flask API接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.engine import analysis_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


@app.route('/api/stock/<stock_code>', methods=['GET'])
def get_stock_data(stock_code: str):
    """获取股票数据"""
    days = request.args.get('days', 120, type=int)
    
    try:
        df = analysis_engine.fetch_data(stock_code, days)
        if df.empty:
            return jsonify({'error': '获取数据失败'}), 404
        
        data = df.to_dict(orient='records')
        return jsonify({'code': stock_code, 'data': data})
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/<stock_code>', methods=['GET'])
def analyze_stock(stock_code: str):
    """股票分析"""
    days = request.args.get('days', 120, type=int)
    strategy = request.args.get('strategy', 'combined')
    
    try:
        result = analysis_engine.full_analysis(stock_code, days, strategy)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'code': stock_code,
            'summary': result['summary'],
            'backtest': {
                'total_return': result['backtest']['total_return'],
                'sharpe_ratio': result['backtest']['sharpe_ratio'],
                'max_drawdown': result['backtest']['max_drawdown'],
                'win_rate': result['backtest']['win_rate']
            }
        })
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/backtest', methods=['POST'])
def backtest():
    """回测接口"""
    data = request.json
    stock_code = data.get('stock_code')
    strategy = data.get('strategy', 'combined')
    days = data.get('days', 120)
    initial_capital = data.get('initial_capital', 1000000)
    
    try:
        df = analysis_engine.fetch_data(stock_code, days)
        df = analysis_engine.analyze(df)
        
        if 'trade_date' in df.columns:
            df.set_index('trade_date', inplace=True)
        
        result = analysis_engine.run_backtest(df, strategy, initial_capital)
        
        return jsonify({
            'code': stock_code,
            'strategy': strategy,
            'result': {
                'total_return': result['total_return'],
                'annualized_return': result['annualized_return'],
                'max_drawdown': result['max_drawdown'],
                'sharpe_ratio': result['sharpe_ratio'],
                'win_rate': result['win_rate'],
                'total_trades': result['total_trades']
            }
        })
    except Exception as e:
        logger.error(f"回测错误: {e}")
        return jsonify({'error': str(e)}), 500


def run_api(host='0.0.0.0', port=5000, debug=False):
    """启动API服务"""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_api(debug=True)
