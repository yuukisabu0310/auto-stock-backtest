# scripts/make_index.py
import os
import json
from pathlib import Path
from html import escape
from datetime import datetime
import pandas as pd

ROOT = Path("reports")
ROOT.mkdir(exist_ok=True, parents=True)

def load_improvement_history():
    """改善履歴を読み込み"""
    try:
        history_file = Path("data/improvement_history.json")
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # データがリストの場合は辞書形式に変換
                if isinstance(data, list):
                    return {"improvements": data, "summary": {}}
                # データが辞書の場合はそのまま返す
                elif isinstance(data, dict):
                    return data
                else:
                    return {"improvements": [], "summary": {}}
    except Exception:
        pass
    return {"improvements": [], "summary": {}}

def load_backtest_summary():
    """バックテスト結果のサマリーを読み込み"""
    summary = {}
    try:
        for strat_dir in ROOT.iterdir():
            if strat_dir.is_dir():
                summary_file = strat_dir / "_all_summary.csv"
                if summary_file.exists():
                    df = pd.read_csv(summary_file)
                    if not df.empty:
                        # 最新の結果を取得
                        latest = df.iloc[-1] if len(df) > 0 else df.iloc[0]
                        summary[strat_dir.name] = {
                            'total_return': latest.get('Total Return [%]', 0),
                            'sharpe_ratio': latest.get('Sharpe Ratio', 0),
                            'max_drawdown': latest.get('Max. Drawdown [%]', 0),
                            'win_rate': latest.get('Win Rate [%]', 0),
                            'profit_factor': latest.get('Profit Factor', 0)
                        }
    except Exception:
        pass
    return summary

def generate_dashboard():
    """統合ダッシュボードを生成"""
    
    # データ読み込み
    history = load_improvement_history()
    backtest_summary = load_backtest_summary()
    
    # 改善履歴の統計
    improvements = history.get("improvements", [])
    total_improvements = len(improvements)
    successful_improvements = len([i for i in improvements if i.get('status') == 'adopted'])
    pending_improvements = len([i for i in improvements if i.get('status') == 'success'])
    
    # 最新の改善
    recent_improvements = improvements[-5:] if improvements else []
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Auto Stock Backtest Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2.5em;
                color: #2c3e50;
                margin-bottom: 10px;
                font-weight: 700;
            }}
            
            .header p {{
                color: #7f8c8d;
                font-size: 1.1em;
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
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-card h3 {{
                color: #2c3e50;
                font-size: 1.2em;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .stat-value {{
                font-size: 2.5em;
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
                margin-bottom: 30px;
            }}
            
            .section h2 {{
                color: #2c3e50;
                font-size: 1.5em;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ecf0f1;
            }}
            
            .strategy-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            
            .strategy-card {{
                background: #f8f9fa;
                border-radius: 12px;
                padding: 20px;
                border-left: 4px solid #3498db;
            }}
            
            .strategy-card h3 {{
                color: #2c3e50;
                margin-bottom: 15px;
                font-size: 1.2em;
            }}
            
            .metric-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                padding: 5px 0;
            }}
            
            .metric-label {{
                color: #7f8c8d;
                font-size: 0.9em;
            }}
            
            .metric-value {{
                font-weight: 600;
                font-size: 0.9em;
            }}
            
            .improvement-list {{
                list-style: none;
            }}
            
            .improvement-item {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
                border-left: 4px solid #27ae60;
            }}
            
            .improvement-item h4 {{
                color: #2c3e50;
                margin-bottom: 8px;
                font-size: 1em;
            }}
            
            .improvement-meta {{
                color: #7f8c8d;
                font-size: 0.8em;
                margin-bottom: 5px;
            }}
            
            .status-badge {{
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.7em;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-adopted {{ background: #d5f4e6; color: #27ae60; }}
            .status-success {{ background: #d6eaf8; color: #3498db; }}
            .status-failed {{ background: #fadbd8; color: #e74c3c; }}
            
            .chart-container {{
                position: relative;
                height: 300px;
                margin: 20px 0;
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
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Auto Stock Backtest Dashboard</h1>
                <p>AI駆動の自動株式バックテストシステム - リアルタイム改善サイクル</p>
                <p>最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📊 総改善回数</h3>
                    <div class="stat-value neutral">{total_improvements}</div>
                    <div class="stat-label">AI改善提案の総数</div>
                </div>
                <div class="stat-card">
                    <h3>✅ 採用済み改善</h3>
                    <div class="stat-value positive">{successful_improvements}</div>
                    <div class="stat-label">本番環境で採用された改善</div>
                </div>
                <div class="stat-card">
                    <h3>⏳ 検証待ち</h3>
                    <div class="stat-value neutral">{pending_improvements}</div>
                    <div class="stat-label">検証成功・レビュー待ち</div>
                </div>
                <div class="stat-card">
                    <h3>📈 戦略数</h3>
                    <div class="stat-value neutral">{len(backtest_summary)}</div>
                    <div class="stat-label">アクティブな戦略</div>
                </div>
            </div>
            
            <div class="content-grid">
                <div class="main-content">
                    <div class="section">
                        <h2>📈 戦略パフォーマンス</h2>
                        <div class="strategy-grid">
    """
    
    # 戦略パフォーマンスカード
    for strategy_name, metrics in backtest_summary.items():
        total_return = metrics.get('total_return', 0)
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        max_drawdown = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        
        return_color = "positive" if total_return > 0 else "negative"
        sharpe_color = "positive" if sharpe_ratio > 1 else "neutral"
        drawdown_color = "negative" if max_drawdown < -10 else "neutral"
        
        html_content += f"""
                            <div class="strategy-card">
                                <h3>{strategy_name}</h3>
                                <div class="metric-row">
                                    <span class="metric-label">総リターン</span>
                                    <span class="metric-value {return_color}">{total_return:.2f}%</span>
                                </div>
                                <div class="metric-row">
                                    <span class="metric-label">シャープレシオ</span>
                                    <span class="metric-value {sharpe_color}">{sharpe_ratio:.2f}</span>
                                </div>
                                <div class="metric-row">
                                    <span class="metric-label">最大ドローダウン</span>
                                    <span class="metric-value {drawdown_color}">{max_drawdown:.2f}%</span>
                                </div>
                                <div class="metric-row">
                                    <span class="metric-label">勝率</span>
                                    <span class="metric-value neutral">{win_rate:.1f}%</span>
                                </div>
                                <div class="metric-row">
                                    <span class="metric-label">プロフィットファクター</span>
                                    <span class="metric-value neutral">{profit_factor:.2f}</span>
                                </div>
                            </div>
        """
    
    html_content += """
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📊 パフォーマンス推移</h2>
                        <div class="chart-container">
                            <canvas id="performanceChart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="sidebar">
                    <div class="section">
                        <h2>🤖 最新の改善</h2>
                        <ul class="improvement-list">
    """
    
    # 最新の改善履歴
    for improvement in recent_improvements:
        strategy_name = improvement.get('strategy_name', 'Unknown')
        status = improvement.get('status', 'unknown')
        score = improvement.get('improvement_score', 0)
        timestamp = improvement.get('timestamp', '')
        
        status_class = f"status-{status}"
        status_display = {
            'adopted': '採用済み',
            'success': '検証成功',
            'failed': '失敗',
            'pending': '保留'
        }.get(status, status)
        
        html_content += f"""
                            <li class="improvement-item">
                                <h4>{strategy_name}</h4>
                                <div class="improvement-meta">
                                    <span class="status-badge {status_class}">{status_display}</span>
                                    <span>スコア: {score:.2f}</span>
                                </div>
                                <div class="improvement-meta">{timestamp}</div>
                            </li>
        """
    
    html_content += """
                        </ul>
                    </div>
                    
                    <div class="section">
                        <h2>🔗 詳細レポート</h2>
                        <ul style="list-style: none; padding: 0;">
                            <li style="margin-bottom: 10px;">
                                <a href="improvement_history.html" style="color: #3498db; text-decoration: none;">
                                    📋 改善履歴詳細
                                </a>
                            </li>
                            <li style="margin-bottom: 10px;">
                                <a href="comparison_report.html" style="color: #3498db; text-decoration: none;">
                                    📊 比較レポート
                                </a>
                            </li>
                            <li style="margin-bottom: 10px;">
                                <a href="timeline_report.html" style="color: #3498db; text-decoration: none;">
                                    ⏰ タイムライン
                                </a>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>
                    <a href="https://github.com/your-username/auto-stock-backtest">GitHub</a> |
                    <a href="improvement_history.html">改善履歴</a> |
                    <a href="comparison_report.html">比較レポート</a> |
                    <a href="timeline_report.html">タイムライン</a>
                </p>
                <p style="margin-top: 10px; color: #7f8c8d; font-size: 0.9em;">
                    Auto Stock Backtest System - AI Improvement Loop
                </p>
            </div>
        </div>
        
        <script>
            // パフォーマンスチャート
            const ctx = document.getElementById('performanceChart').getContext('2d');
            const performanceData = {
                labels: {strategy_labels},
                datasets: [
                    {
                        label: '総リターン (%)',
                        data: {return_data},
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'シャープレシオ',
                        data: {sharpe_data},
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            };
            
            new Chart(ctx, {{
                type: 'line',
                data: performanceData,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        intersect: false,
                        mode: 'index'
                    }},
                    scales: {{
                        y: {{
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {{
                                display: true,
                                text: '総リターン (%)'
                            }}
                        }},
                        y1: {{
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {{
                                display: true,
                                text: 'シャープレシオ'
                            }},
                            grid: {{
                                drawOnChartArea: false
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    # チャートデータの準備
    strategy_labels = list(backtest_summary.keys())
    return_data = [backtest_summary[s].get('total_return', 0) for s in strategy_labels]
    sharpe_data = [backtest_summary[s].get('sharpe_ratio', 0) for s in strategy_labels]
    
    # データをJSON形式で埋め込み
    html_content = html_content.replace('{strategy_labels}', json.dumps(strategy_labels))
    html_content = html_content.replace('{return_data}', json.dumps(return_data))
    html_content = html_content.replace('{sharpe_data}', json.dumps(sharpe_data))
    
    return html_content

def build():
    """メインのビルド関数"""
    # 統合ダッシュボードを生成
    dashboard_html = generate_dashboard()
    (ROOT / "index.html").write_text(dashboard_html, encoding="utf-8")
    print("reports/index.html generated (Unified Dashboard)")
    
    # 従来のファイルリストも生成（後方互換性のため）
    generate_file_list()

def generate_file_list():
    """従来のファイルリストを生成"""
    parts = []
    parts.append("<!doctype html><html><head>")
    parts.append("<meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    parts.append("<title>Backtest Reports - File List</title>")
    parts.append("<style>body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:16px;line-height:1.5} h1{font-size:20px} h2{font-size:18px;margin-top:18px} ul{padding-left:18px} a{word-break:break-all}</style>")
    parts.append("</head><body>")
    parts.append("<h1>Backtest Reports - File List</h1>")
    parts.append('<p><a href="index.html">← ダッシュボードに戻る</a></p>')

    # 戦略ごとのディレクトリ
    for strat_dir in sorted([p for p in ROOT.iterdir() if p.is_dir()]):
        files = sorted(strat_dir.glob("*"))
        if not files:
            continue
        parts.append(f"<h2>{escape(strat_dir.name)}</h2><ul>")
        # まず概要ファイルを先に
        for name in ["_params.txt", "_all_summary.csv"]:
            fp = strat_dir / name
            if fp.exists():
                parts.append(li(fp))
        # そのほかのファイル
        for f in files:
            if f.name in ["_params.txt", "_all_summary.csv"]:
                continue
            parts.append(li(f))
        parts.append("</ul>")

    # ルート直下のログなど
    root_files = [p for p in ROOT.iterdir() if p.is_file()]
    if root_files:
        parts.append("<h2>Others</h2><ul>")
        for f in sorted(root_files):
            parts.append(li(f))
        parts.append("</ul>")

    parts.append("</body></html>")
    (ROOT / "files.html").write_text("\n".join(parts), encoding="utf-8")
    print("reports/files.html generated (File List)")

def li(path: Path) -> str:
    href = path.as_posix()
    return f"<li><a href='{escape(href)}'>{escape(path.name)}</a></li>"

if __name__ == "__main__":
    build()
