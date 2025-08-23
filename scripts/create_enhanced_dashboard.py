#!/usr/bin/env python3
"""
Enhanced Dashboard HTML Generator
スタイリッシュで直感的なダッシュボードを生成
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

ROOT = Path("reports")

def format_number(value: float, decimals: int = 2) -> str:
    """数値をフォーマット"""
    if value is None or value != value:  # NaN check
        return "N/A"
    return f"{value:.{decimals}f}"

def get_color_class(value: float, metric_type: str = "return") -> str:
    """値に基づいて色クラスを返す"""
    if value is None or value != value:
        return "neutral"
    
    if metric_type == "return":
        if value > 0:
            return "positive"
        elif value < 0:
            return "negative"
        else:
            return "neutral"
    elif metric_type == "sharpe":
        if value > 1:
            return "positive"
        elif value > 0:
            return "neutral"
        else:
            return "negative"
    elif metric_type == "drawdown":
        if value > -10:
            return "positive"
        elif value > -20:
            return "neutral"
        else:
            return "negative"
    else:
        return "neutral"

def generate_enhanced_dashboard():
    """新しいダッシュボードを生成"""
    
    # データを読み込み
    data_file = ROOT / "enhanced_dashboard_data.json"
    if not data_file.exists():
        print("Enhanced dashboard data not found. Please run enhanced_dashboard.py first.")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    strategies = data.get('strategies', {})
    portfolio_metrics = data.get('portfolio_metrics', {})
    strategy_rankings = data.get('strategy_rankings', [])
    heatmap_data = data.get('heatmap_data', [])
    summary_stats = data.get('summary_stats', {})
    
    # HTMLテンプレート
    html_template = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Enhanced Auto Stock Backtest Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card h3 {{
            color: #2c3e50;
            font-size: 1.1em;
            margin-bottom: 15px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #3498db; }}
        
        .content-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        
        .main-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .sidebar {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #ecf0f1;
            display: flex;
            align-items: center;
        }}
        
        .section h2::before {{
            content: '';
            width: 4px;
            height: 25px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            margin-right: 15px;
            border-radius: 2px;
        }}
        
        .strategy-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }}
        
        .strategy-card {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #3498db;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .strategy-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }}
        
        .strategy-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }}
        
        .strategy-card h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.3em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .strategy-rank {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        
        .metric-item {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }}
        
        .metric-label {{
            color: #7f8c8d;
            font-size: 0.85em;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .metric-value {{
            font-weight: 700;
            font-size: 1.2em;
        }}
        
        .metric-item {{
            position: relative;
        }}
        
        .tooltip {{
            position: relative;
            display: inline-block;
        }}
        
        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 250px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -125px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.8em;
            line-height: 1.4;
        }}
        
        .tooltip:hover .tooltiptext {{
            visibility: visible;
            opacity: 1;
        }}
        
        .tooltip .tooltiptext::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }}
        
        .help-icon {{
            color: #667eea;
            cursor: help;
            margin-left: 5px;
            font-size: 0.8em;
        }}
        
        .heatmap-container {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .heatmap-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        
        .heatmap-cell {{
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 0.9em;
            font-weight: 600;
            color: white;
            position: relative;
        }}
        
        .heatmap-cell.positive {{
            background: linear-gradient(135deg, #27ae60, #2ecc71);
        }}
        
        .heatmap-cell.negative {{
            background: linear-gradient(135deg, #e74c3c, #c0392b);
        }}
        
        .heatmap-cell.neutral {{
            background: linear-gradient(135deg, #3498db, #2980b9);
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            height: 400px;
        }}
        
        .ranking-list {{
            list-style: none;
        }}
        
        .ranking-item {{
            background: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease;
        }}
        
        .ranking-item:hover {{
            transform: translateX(5px);
        }}
        
        .ranking-position {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .ranking-info {{
            flex: 1;
            margin-left: 15px;
        }}
        
        .ranking-name {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .ranking-stats {{
            font-size: 0.85em;
            color: #7f8c8d;
        }}
        
        .footer {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .footer a {{
            color: #3498db;
            text-decoration: none;
            margin: 0 10px;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        @media (max-width: 768px) {{
            .content-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            }}
            
            .strategy-grid {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .tab-container {{
            margin-bottom: 30px;
        }}
        
        .tab-buttons {{
            display: flex;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 5px;
            margin-bottom: 20px;
        }}
        
        .tab-button {{
            flex: 1;
            padding: 12px 20px;
            border: none;
            background: transparent;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            color: #7f8c8d;
            transition: all 0.3s ease;
        }}
        
        .tab-button.active {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Auto Stock Backtest Dashboard</h1>
            <p>AI駆動の自動株式バックテストシステム - 詳細分析ダッシュボード</p>
            <p>最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📊 総戦略数</h3>
                <div class="stat-value neutral">{summary_stats.get('total_strategies', 0)}</div>
                <div class="stat-label">全戦略数（アクティブ: {summary_stats.get('active_strategies', 0)}）</div>
            </div>
            <div class="stat-card">
                <h3>📈 平均リターン</h3>
                <div class="stat-value {get_color_class(summary_stats.get('avg_return', 0), 'return')}">{format_number(summary_stats.get('avg_return', 0))}%</div>
                <div class="stat-label">全戦略の平均</div>
            </div>
            <div class="stat-card">
                <h3>🏆 最高戦略</h3>
                <div class="stat-value positive">{summary_stats.get('best_strategy', 'N/A')}</div>
                <div class="stat-label">リターン最高</div>
            </div>
            <div class="stat-card">
                <h3>📊 銘柄数</h3>
                <div class="stat-value neutral">{summary_stats.get('total_tickers', 0)}</div>
                <div class="stat-label">テスト対象銘柄</div>
            </div>
        </div>
        
        <div class="content-grid">
            <div class="main-content">
                <div class="tab-container">
                    <div class="tab-buttons">
                        <button class="tab-button active" onclick="showTab('strategies')">戦略詳細</button>
                        <button class="tab-button" onclick="showTab('heatmap')">ヒートマップ</button>
                        <button class="tab-button" onclick="showTab('portfolio')">ポートフォリオ</button>
                    </div>
                    
                    <div id="strategies" class="tab-content active">
                        <div class="section">
                            <h2>📈 戦略パフォーマンス詳細</h2>
                            <div class="strategy-grid">
    """
    
    # 戦略カードを生成
    for i, ranking in enumerate(strategy_rankings[:10]):  # 上位10戦略のみ表示
        strategy_name = ranking['name']
        strategy_data = strategies.get(strategy_name, {})
        summary = strategy_data.get('summary', {})
        
        html_template += f"""
                                <div class="strategy-card">
                                    <h3>
                                        {strategy_name}
                                        <span class="strategy-rank">#{i+1}</span>
                                    </h3>
                                    <div class="metrics-grid">
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                総リターン
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">期間中の総収益率。プラスは利益、マイナスは損失を示します。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value {get_color_class(ranking['total_return'], 'return')}">{format_number(ranking['total_return'])}%</div>
                                        </div>
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                シャープレシオ
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">リスク調整後収益率。1.0以上が良好、2.0以上が優秀とされます。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value {get_color_class(ranking['sharpe_ratio'], 'sharpe')}">{format_number(ranking['sharpe_ratio'])}</div>
                                        </div>
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                最大DD
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">最大ドローダウン。ピークから最大の下落幅を示します。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value {get_color_class(ranking['max_drawdown'], 'drawdown')}">{format_number(ranking['max_drawdown'])}%</div>
                                        </div>
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                勝率
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">利益が出たトレードの割合。50%以上が良好とされます。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value {get_color_class(ranking['win_rate'] - 50, 'return')}">{format_number(ranking['win_rate'])}%</div>
                                        </div>
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                トレード数
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">期間中に実行された総トレード数。サンプルサイズの指標です。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value neutral">{ranking['total_trades']}</div>
                                        </div>
                                        <div class="metric-item">
                                            <div class="metric-label">
                                                サンプル数
                                                <span class="tooltip">
                                                    <span class="help-icon">?</span>
                                                    <span class="tooltiptext">テスト対象の銘柄数。統計的信頼性の指標です。</span>
                                                </span>
                                            </div>
                                            <div class="metric-value neutral">{ranking['sample_size']}</div>
                                        </div>
                                    </div>
                                </div>
        """
    
    html_template += """
                            </div>
                        </div>
                    </div>
                    
                    <div id="heatmap" class="tab-content">
                        <div class="section">
                            <h2>🔥 戦略×銘柄ヒートマップ</h2>
                            <div class="heatmap-container">
                                <div class="heatmap-grid">
    """
    
    # ヒートマップを生成（上位20件のみ）
    for item in heatmap_data[:20]:
        color_class = get_color_class(item['return'], 'return')
        html_template += f"""
                                    <div class="heatmap-cell {color_class}">
                                        <div style="font-size: 0.8em;">{item['strategy']}</div>
                                        <div style="font-size: 0.7em;">{item['ticker']}</div>
                                        <div style="font-size: 0.9em; margin-top: 5px;">{format_number(item['return'])}%</div>
                                    </div>
        """
    
    html_template += """
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div id="portfolio" class="tab-content">
                        <div class="section">
                            <h2>📊 ポートフォリオ分析</h2>
                            <div class="chart-container">
                                <canvas id="portfolioChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="section">
                    <h2>🏆 戦略ランキング</h2>
                    <ul class="ranking-list">
    """
    
    # ランキングリストを生成
    for i, ranking in enumerate(strategy_rankings[:10]):
        html_template += f"""
                        <li class="ranking-item">
                            <div class="ranking-position">{i+1}</div>
                            <div class="ranking-info">
                                <div class="ranking-name">{ranking['name']}</div>
                                <div class="ranking-stats">
                                    リターン: {format_number(ranking['total_return'])}% | 
                                    シャープ: {format_number(ranking['sharpe_ratio'])} | 
                                    DD: {format_number(ranking['max_drawdown'])}%
                                </div>
                            </div>
                        </li>
        """
    
    html_template += """
                    </ul>
                </div>
                
                <div class="section">
                    <h2>📈 ポートフォリオ指標</h2>
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <div class="metric-label">
                                ポートフォリオリターン
                                <span class="tooltip">
                                    <span class="help-icon">?</span>
                                    <span class="tooltiptext">全戦略を組み合わせた場合の平均リターン。分散投資の効果を示します。</span>
                                </span>
                            </div>
                            <div class="metric-value {get_color_class(portfolio_metrics.get('portfolio_return', 0), 'return')}">{format_number(portfolio_metrics.get('portfolio_return', 0))}%</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">
                                ポートフォリオボラティリティ
                                <span class="tooltip">
                                    <span class="help-icon">?</span>
                                    <span class="tooltiptext">全戦略を組み合わせた場合のリスク（変動性）。低いほど安定です。</span>
                                </span>
                            </div>
                            <div class="metric-value neutral">{format_number(portfolio_metrics.get('portfolio_volatility', 0))}%</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">
                                ポートフォリオシャープ
                                <span class="tooltip">
                                    <span class="help-icon">?</span>
                                    <span class="tooltiptext">ポートフォリオ全体のリスク調整後収益率。1.0以上が良好です。</span>
                                </span>
                            </div>
                            <div class="metric-value {get_color_class(portfolio_metrics.get('portfolio_sharpe', 0), 'sharpe')}">{format_number(portfolio_metrics.get('portfolio_sharpe', 0))}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">
                                分散効果スコア
                                <span class="tooltip">
                                    <span class="help-icon">?</span>
                                    <span class="tooltiptext">戦略間の相関が低いほど高くなるスコア。高いほど分散効果が期待できます。</span>
                                </span>
                            </div>
                            <div class="metric-value {get_color_class(portfolio_metrics.get('diversification_score', 0), 'return')}">{format_number(portfolio_metrics.get('diversification_score', 0))}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🚀 Enhanced Auto Stock Backtest Dashboard | 
            <a href="files.html">ファイル一覧</a> | 
            <a href="improvement_summary.html">改善履歴</a></p>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {{
            // タブボタンのアクティブ状態を更新
            document.querySelectorAll('.tab-button').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            // タブコンテンツの表示を更新
            document.querySelectorAll('.tab-content').forEach(content => {{
                content.classList.remove('active');
            }});
            document.getElementById(tabName).classList.add('active');
        }}
        
        // ポートフォリオチャート
        const ctx = document.getElementById('portfolioChart').getContext('2d');
        new Chart(ctx, {{
            type: 'radar',
            data: {{
                labels: {[f'"{s["name"]}"' for s in strategy_rankings[:8]]},
                datasets: [{{
                    label: '総リターン (%)',
                    data: {[s['total_return'] for s in strategy_rankings[:8]]},
                    borderColor: 'rgba(102, 126, 234, 1)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(102, 126, 234, 1)'
                }}, {{
                    label: 'シャープレシオ',
                    data: {[s['sharpe_ratio'] * 10 for s in strategy_rankings[:8]]},
                    borderColor: 'rgba(118, 75, 162, 1)',
                    backgroundColor: 'rgba(118, 75, 162, 0.2)',
                    pointBackgroundColor: 'rgba(118, 75, 162, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(118, 75, 162, 1)'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }},
                    title: {{
                        display: true,
                        text: '戦略パフォーマンス比較'
                    }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 20
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    
    # HTMLファイルを保存
    output_file = ROOT / "enhanced_index.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Enhanced dashboard saved to: {output_file}")

if __name__ == "__main__":
    generate_enhanced_dashboard()
