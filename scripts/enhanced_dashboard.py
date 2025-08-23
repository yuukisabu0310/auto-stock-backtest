#!/usr/bin/env python3
"""
Enhanced Dashboard Data Collection Script
詳細な分析データを収集してダッシュボード用のJSONファイルを生成
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import glob

ROOT = Path("reports")

def load_strategy_data(strategy_name: str) -> Dict[str, Any]:
    """戦略の詳細データを読み込み"""
    strategy_dir = ROOT / strategy_name
    if not strategy_dir.exists():
        return {}
    
    data = {
        'name': strategy_name,
        'summary': {},
        'ticker_performance': {},
        'rolling_performance': [],
        'trade_analysis': {},
        'risk_metrics': {}
    }
    
    # サマリーファイルを読み込み
    summary_file = strategy_dir / "_all_summary.csv"
    if summary_file.exists():
        df = pd.read_csv(summary_file)
        if not df.empty:
            data['summary'] = {
                'total_return': float(df.get('avg_return_%', [0]).iloc[0]) if 'avg_return_%' in df.columns else 0.0,
                'sharpe_ratio': float(df.get('avg_sharpe', [0]).iloc[0]) if 'avg_sharpe' in df.columns else 0.0,
                'max_drawdown': float(df.get('avg_max_dd_%', [0]).iloc[0]) if 'avg_max_dd_%' in df.columns else 0.0,
                'win_rate': float(df.get('Win Rate [%]', [50]).iloc[0]) if 'Win Rate [%]' in df.columns else 50.0,
                'profit_factor': float(df.get('Profit Factor', [1.0]).iloc[0]) if 'Profit Factor' in df.columns else 1.0,
                'total_trades': int(df.get('trades_sum', [0]).iloc[0]) if 'trades_sum' in df.columns else 0,
                'sample_size': len(df)
            }
    
    # 個別銘柄のパフォーマンスを読み込み
    csv_files = glob.glob(str(strategy_dir / "*_OOS_walkforward_result.csv"))
    ticker_data = {}
    
    for csv_file in csv_files:
        try:
            ticker = Path(csv_file).stem.split('_')[0]
            df = pd.read_csv(csv_file)
            
            if not df.empty:
                # より正確なデータ抽出
                total_return = float(df.get('Total Return [%]', [0]).iloc[0]) if 'Total Return [%]' in df.columns else 0.0
                sharpe_ratio = float(df.get('Sharpe Ratio', [0]).iloc[0]) if 'Sharpe Ratio' in df.columns else 0.0
                max_drawdown = float(df.get('Max. Drawdown [%]', [0]).iloc[0]) if 'Max. Drawdown [%]' in df.columns else 0.0
                win_rate = float(df.get('Win Rate [%]', [50]).iloc[0]) if 'Win Rate [%]' in df.columns else 50.0
                total_trades = int(df.get('Total Trades', [0]).iloc[0]) if 'Total Trades' in df.columns else 0
                
                ticker_data[ticker] = {
                    'total_return': total_return,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate,
                    'total_trades': total_trades,
                    'avg_trade_return': float(df.get('Avg. Trade Return [%]', [0]).iloc[0]) if 'Avg. Trade Return [%]' in df.columns else 0.0,
                    'best_trade': float(df.get('Best Trade [%]', [0]).iloc[0]) if 'Best Trade [%]' in df.columns else 0.0,
                    'worst_trade': float(df.get('Worst Trade [%]', [0]).iloc[0]) if 'Worst Trade [%]' in df.columns else 0.0,
                    'avg_holding_period': float(df.get('Avg. Holding Period', [0]).iloc[0]) if 'Avg. Holding Period' in df.columns else 0.0
                }
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
            continue
    
    data['ticker_performance'] = ticker_data
    
    # リスク指標を計算
    if ticker_data:
        returns = [t['total_return'] for t in ticker_data.values()]
        data['risk_metrics'] = {
            'volatility': float(np.std(returns)) if len(returns) > 1 else 0.0,
            'min_return': float(min(returns)) if returns else 0.0,
            'max_return': float(max(returns)) if returns else 0.0,
            'avg_return': float(np.mean(returns)) if returns else 0.0,
            'positive_count': int(sum(1 for r in returns if r > 0)),
            'negative_count': int(sum(1 for r in returns if r < 0)),
            'success_rate': float(sum(1 for r in returns if r > 0) / len(returns) * 100) if returns else 0.0
        }
    
    return data

def calculate_portfolio_metrics(strategies_data: Dict[str, Any]) -> Dict[str, Any]:
    """ポートフォリオ分析の指標を計算"""
    if not strategies_data:
        return {}
    
    # 各戦略のリターンを取得
    strategy_returns = {}
    for strategy_name, data in strategies_data.items():
        if 'summary' in data and 'total_return' in data['summary']:
            strategy_returns[strategy_name] = data['summary']['total_return']
    
    if not strategy_returns:
        return {}
    
    # 相関行列を計算（簡易版）
    returns_list = list(strategy_returns.values())
    correlation_matrix = {}
    
    for i, (strategy1, return1) in enumerate(strategy_returns.items()):
        correlation_matrix[strategy1] = {}
        for j, (strategy2, return2) in enumerate(strategy_returns.items()):
            if i == j:
                correlation_matrix[strategy1][strategy2] = 1.0
            else:
                # 簡易相関（実際の時系列データがないため）
                correlation_matrix[strategy1][strategy2] = 0.5
    
    # ポートフォリオ指標
    avg_return = float(np.mean(returns_list))
    portfolio_volatility = float(np.std(returns_list)) if len(returns_list) > 1 else 0.0
    sharpe_ratio = float(avg_return / portfolio_volatility) if portfolio_volatility > 0 else 0.0
    
    return {
        'correlation_matrix': correlation_matrix,
        'portfolio_return': avg_return,
        'portfolio_volatility': portfolio_volatility,
        'portfolio_sharpe': sharpe_ratio,
        'strategy_count': len(strategy_returns),
        'diversification_score': float(1 - (portfolio_volatility / max(returns_list))) if max(returns_list) > 0 else 0.0
    }

def generate_enhanced_dashboard_data():
    """詳細なダッシュボードデータを生成"""
    print("Enhanced dashboard data generation started...")
    
    # 全戦略のデータを収集
    strategies_data = {}
    strategy_dirs = [d for d in ROOT.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    for strategy_dir in strategy_dirs:
        strategy_name = strategy_dir.name
        print(f"Loading data for strategy: {strategy_name}")
        strategies_data[strategy_name] = load_strategy_data(strategy_name)
    
    # ポートフォリオ分析
    portfolio_metrics = calculate_portfolio_metrics(strategies_data)
    
    # 戦略ランキング
    strategy_rankings = []
    for strategy_name, data in strategies_data.items():
        if 'summary' in data:
            summary = data['summary']
            # 個別銘柄のトレード数を合計
            ticker_trades = sum([t.get('total_trades', 0) for t in data.get('ticker_performance', {}).values()])
            
            strategy_rankings.append({
                'name': strategy_name,
                'total_return': summary.get('total_return', 0),
                'sharpe_ratio': summary.get('sharpe_ratio', 0),
                'max_drawdown': summary.get('max_drawdown', 0),
                'win_rate': summary.get('win_rate', 0),
                'total_trades': ticker_trades,  # 個別銘柄の合計
                'sample_size': summary.get('sample_size', 0)
            })
    
    # リターンでソート
    strategy_rankings.sort(key=lambda x: x['total_return'], reverse=True)
    
    # ヒートマップデータ
    heatmap_data = []
    for strategy_name, data in strategies_data.items():
        for ticker, performance in data.get('ticker_performance', {}).items():
            heatmap_data.append({
                'strategy': strategy_name,
                'ticker': ticker,
                'return': performance.get('total_return', 0),
                'sharpe': performance.get('sharpe_ratio', 0),
                'drawdown': performance.get('max_drawdown', 0)
            })
    
    # 全戦略のリストを取得（設定ファイルから）
    all_strategies = [
        'FixedSma', 'SmaCross', 'MovingAverageBreakout', 'DonchianChannel', 
        'MACD', 'RSIMomentum', 'RSIExtreme', 'BollingerBands', 
        'Squeeze', 'VolumeBreakout', 'OBV', 'TrendFollowing'
    ]
    
    # 実際にデータがある戦略と全戦略を区別
    active_strategies = list(strategies_data.keys())
    total_tickers = len(set([h['ticker'] for h in heatmap_data]))
    total_trades = sum([s.get('total_trades', 0) for s in strategy_rankings])
    
    # 最終的なデータ構造
    dashboard_data = {
        'generated_at': datetime.now().isoformat(),
        'strategies': strategies_data,
        'portfolio_metrics': portfolio_metrics,
        'strategy_rankings': strategy_rankings,
        'heatmap_data': heatmap_data,
        'summary_stats': {
            'total_strategies': len(all_strategies),  # 全戦略数
            'active_strategies': len(active_strategies),  # アクティブな戦略数
            'total_tickers': total_tickers,
            'total_trades': total_trades,
            'avg_return': float(np.mean([s['total_return'] for s in strategy_rankings])) if strategy_rankings else 0.0,
            'best_strategy': strategy_rankings[0]['name'] if strategy_rankings else None,
            'worst_strategy': strategy_rankings[-1]['name'] if strategy_rankings else None
        }
    }
    
    # JSONファイルに保存
    output_file = ROOT / "enhanced_dashboard_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    
    print(f"Enhanced dashboard data saved to: {output_file}")
    return dashboard_data

if __name__ == "__main__":
    generate_enhanced_dashboard_data()
