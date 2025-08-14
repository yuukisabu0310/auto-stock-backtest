#!/usr/bin/env python3
"""
改善レポート生成スクリプト
改善結果の詳細レポートを生成します。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history

logger = get_logger("generate_improvement_reports")

class ImprovementReportGenerator:
    """改善レポート生成クラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
    def generate_all_reports(self, 
                              evaluation_results_file: str = "evaluation_results.json",
                              test_results_file: str = "test_results.json"):
        """全ての改善レポートを生成"""
        
        logger.info("改善レポート生成開始")
        
        # 評価結果を読み込み
        evaluation = self._load_evaluation_results(evaluation_results_file)
        test_results = self._load_test_results(test_results_file)
        
        # 各種レポートを生成
        self._generate_summary_report(evaluation, test_results)
        self._generate_detailed_report(evaluation, test_results)
        self._generate_comparison_report(evaluation, test_results)
        self._generate_timeline_report()
        
        logger.info("改善レポート生成完了")
    
    def _load_evaluation_results(self, evaluation_results_file: str) -> Dict[str, Any]:
        """評価結果を読み込み"""
        try:
            if Path(evaluation_results_file).exists():
                with open(evaluation_results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"評価結果読み込みエラー: {e}")
        return {}
    
    def _load_test_results(self, test_results_file: str) -> List[Dict[str, Any]]:
        """テスト結果を読み込み"""
        try:
            if Path(test_results_file).exists():
                with open(test_results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"テスト結果読み込みエラー: {e}")
        return []
    
    def _generate_summary_report(self, evaluation: Dict[str, Any], test_results: List[Dict[str, Any]]):
        """サマリーレポートを生成"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI改善サマリーレポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 5px; }}
                .success {{ color: #27ae60; }}
                .failure {{ color: #e74c3c; }}
                .neutral {{ color: #7f8c8d; }}
                .chart {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 AI改善サマリーレポート</h1>
                <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>実行サマリー</h2>
                <div class="metric">
                    <strong>総テスト数:</strong> {evaluation.get('total_tests', 0)}
                </div>
                <div class="metric success">
                    <strong>成功:</strong> {evaluation.get('successful_improvements', 0)}
                </div>
                <div class="metric failure">
                    <strong>失敗:</strong> {evaluation.get('failed_improvements', 0)}
                </div>
                <div class="metric">
                    <strong>成功率:</strong> {evaluation.get('success_rate', 0):.1%}
                </div>
            </div>
            
            <div class="summary">
                <h2>戦略別結果</h2>
                {self._generate_strategy_summary_html(evaluation)}
            </div>
            
            <div class="summary">
                <h2>推奨事項</h2>
                {self._generate_recommendations_html(evaluation)}
            </div>
            
            <div class="summary">
                <h2>改善履歴サマリー</h2>
                {self._generate_history_summary_html()}
            </div>
        </body>
        </html>
        """
        
        output_file = self.reports_dir / "improvement_summary.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"サマリーレポートを生成: {output_file}")
    
    def _generate_detailed_report(self, evaluation: Dict[str, Any], test_results: List[Dict[str, Any]]):
        """詳細レポートを生成"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI改善詳細レポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .improvement {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .success {{ border-left: 5px solid #27ae60; }}
                .failure {{ border-left: 5px solid #e74c3c; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 10px 0; }}
                .metric {{ background: #f8f9fa; padding: 10px; border-radius: 3px; }}
                .improved {{ background: #d4edda; }}
                .degraded {{ background: #f8d7da; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 AI改善詳細レポート</h1>
                <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>成功した改善</h2>
            {self._generate_successful_improvements_html(evaluation)}
            
            <h2>失敗した改善</h2>
            {self._generate_failed_improvements_html(evaluation)}
            
            <h2>全テスト結果</h2>
            {self._generate_all_test_results_html(test_results)}
        </body>
        </html>
        """
        
        output_file = self.reports_dir / "improvement_detailed.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"詳細レポートを生成: {output_file}")
    
    def _generate_comparison_report(self, evaluation: Dict[str, Any], test_results: List[Dict[str, Any]]):
        """比較レポートを生成"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI改善比較レポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .comparison {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .before-after {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .before {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .after {{ background: #e8f5e8; padding: 15px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; }}
                .improvement {{ color: #27ae60; font-weight: bold; }}
                .degradation {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 AI改善比較レポート</h1>
                <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            {self._generate_comparison_details_html(evaluation)}
        </body>
        </html>
        """
        
        output_file = self.reports_dir / "improvement_comparison.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"比較レポートを生成: {output_file}")
    
    def _generate_timeline_report(self):
        """タイムラインレポートを生成"""
        
        summary = improvement_history.get_improvement_summary()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI改善タイムラインレポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .timeline {{ margin: 20px 0; }}
                .timeline-item {{ margin: 10px 0; padding: 10px; border-left: 3px solid #3498db; background: #f8f9fa; }}
                .adopted {{ border-left-color: #27ae60; }}
                .failed {{ border-left-color: #e74c3c; }}
                .pending {{ border-left-color: #f39c12; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 AI改善タイムラインレポート</h1>
                <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="timeline">
                {self._generate_timeline_items_html()}
            </div>
        </body>
        </html>
        """
        
        output_file = self.reports_dir / "improvement_timeline.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"タイムラインレポートを生成: {output_file}")
    
    def _generate_strategy_summary_html(self, evaluation: Dict[str, Any]) -> str:
        """戦略別サマリーのHTML生成"""
        html = ""
        
        # 戦略別の統計を集計
        strategy_stats = {}
        for detail in evaluation.get('successful_details', []):
            strategy = detail['strategy_name']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'success': 0, 'failure': 0, 'total_score': 0}
            strategy_stats[strategy]['success'] += 1
            strategy_stats[strategy]['total_score'] += detail['improvement_score']
        
        for detail in evaluation.get('failed_details', []):
            strategy = detail['strategy_name']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'success': 0, 'failure': 0, 'total_score': 0}
            strategy_stats[strategy]['failure'] += 1
        
        for strategy, stats in strategy_stats.items():
            total = stats['success'] + stats['failure']
            avg_score = stats['total_score'] / stats['success'] if stats['success'] > 0 else 0
            html += f"""
            <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
                <h3>{strategy}</h3>
                <p>成功: {stats['success']} | 失敗: {stats['failure']} | 平均スコア: {avg_score:.4f}</p>
            </div>
            """
        
        return html
    
    def _generate_recommendations_html(self, evaluation: Dict[str, Any]) -> str:
        """推奨事項のHTML生成"""
        html = ""
        
        for recommendation in evaluation.get('recommendations', []):
            html += f"<p>• {recommendation}</p>"
        
        return html
    
    def _generate_history_summary_html(self) -> str:
        """改善履歴サマリーのHTML生成"""
        try:
            summary = improvement_history.get_improvement_summary()
            
            html = f"""
            <p>総改善回数: {summary['total']}</p>
            <p>対象戦略数: {len(summary['strategies'])}</p>
            """
            
            if summary['recent_improvements']:
                html += "<h3>最近の改善</h3>"
                for record in summary['recent_improvements'][:5]:
                    status_display = record['status']
                    if record['status'] == 'success':
                        status_display = '検証成功'
                    elif record['status'] == 'adopted':
                        status_display = '採用済み'
                    elif record['status'] == 'failed':
                        status_display = '失敗'
                    elif record['status'] == 'pending':
                        status_display = '保留'
                    
                    html += f"<p>• {record['strategy']} - {status_display} (スコア: {record['score']:.4f})</p>"
            
            return html
        except Exception as e:
            logger.error(f"履歴サマリー生成エラー: {e}")
            return "<p>履歴サマリーの生成に失敗しました。</p>"
    
    def _generate_successful_improvements_html(self, evaluation: Dict[str, Any]) -> str:
        """成功した改善のHTML生成"""
        html = ""
        
        for detail in evaluation.get('successful_details', []):
            html += f"""
            <div class="improvement success">
                <h3>{detail['strategy_name']}</h3>
                <p><strong>説明:</strong> {detail['description']}</p>
                <p><strong>改善スコア:</strong> {detail['improvement_score']:.4f}</p>
                <p><strong>改善レベル:</strong> {detail['improvement_level']}</p>
                <p><strong>推奨:</strong> {detail['recommendation']}</p>
                <p><strong>リスク評価:</strong> {detail['risk_assessment']}</p>
                
                <div class="metrics">
                    <div class="metric improved">
                        <strong>改善メトリクス:</strong><br>
                        {', '.join(detail['improved_metrics']) if detail['improved_metrics'] else 'なし'}
                    </div>
                    <div class="metric degraded">
                        <strong>悪化メトリクス:</strong><br>
                        {', '.join(detail['degraded_metrics']) if detail['degraded_metrics'] else 'なし'}
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _generate_failed_improvements_html(self, evaluation: Dict[str, Any]) -> str:
        """失敗した改善のHTML生成"""
        html = ""
        
        for detail in evaluation.get('failed_details', []):
            html += f"""
            <div class="improvement failure">
                <h3>{detail['strategy_name']}</h3>
                <p><strong>説明:</strong> {detail['description']}</p>
                <p><strong>改善スコア:</strong> {detail['improvement_score']:.4f}</p>
                <p><strong>改善レベル:</strong> {detail['improvement_level']}</p>
                <p><strong>推奨:</strong> {detail['recommendation']}</p>
            </div>
            """
        
        return html
    
    def _generate_all_test_results_html(self, test_results: List[Dict[str, Any]]) -> str:
        """全テスト結果のHTML生成"""
        html = ""
        
        for i, result in enumerate(test_results, 1):
            proposal = result.get('proposal', {})
            success = result.get('success', False)
            status_class = 'success' if success else 'failure'
            
            html += f"""
            <div class="improvement {status_class}">
                <h4>テスト {i}: {proposal.get('strategy_name', '')}</h4>
                <p><strong>説明:</strong> {proposal.get('description', '')}</p>
                <p><strong>成功:</strong> {'はい' if success else 'いいえ'}</p>
                <p><strong>改善スコア:</strong> {result.get('improvement_score', 0):.4f}</p>
            </div>
            """
        
        return html
    
    def _generate_comparison_details_html(self, evaluation: Dict[str, Any]) -> str:
        """比較詳細のHTML生成"""
        html = ""
        
        for detail in evaluation.get('successful_details', []):
            html += f"""
            <div class="comparison">
                <h3>{detail['strategy_name']}</h3>
                <div class="before-after">
                    <div class="before">
                        <h4>改善前</h4>
                        <p>パラメータ: {detail.get('old_params', 'N/A')}</p>
                    </div>
                    <div class="after">
                        <h4>改善後</h4>
                        <p>パラメータ: {detail.get('new_params', 'N/A')}</p>
                        <p class="improvement">改善スコア: {detail['improvement_score']:.4f}</p>
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _generate_timeline_items_html(self) -> str:
        """タイムラインアイテムのHTML生成"""
        html = ""
        
        # 改善履歴を時系列順にソート
        history = improvement_history.history
        sorted_history = sorted(history, key=lambda x: x.timestamp, reverse=True)
        
        for record in sorted_history[:20]:  # 最新20件
            status_class = record.status
            html += f"""
            <div class="timeline-item {status_class}">
                <h4>{record.strategy_name} - {record.id}</h4>
                <p><strong>日時:</strong> {record.timestamp}</p>
                <p><strong>ステータス:</strong> {record.status}</p>
                <p><strong>説明:</strong> {record.description}</p>
                <p><strong>スコア:</strong> {record.improvement_score:.4f}</p>
            </div>
            """
        
        return html

def main():
    parser = argparse.ArgumentParser(description='改善レポート生成')
    parser.add_argument('--evaluation-results', type=str, default='evaluation_results.json',
                        help='評価結果ファイル名')
    parser.add_argument('--test-results', type=str, default='test_results.json',
                        help='テスト結果ファイル名')
    
    args = parser.parse_args()
    
    try:
        generator = ImprovementReportGenerator()
        generator.generate_all_reports(
            evaluation_results_file=args.evaluation_results,
            test_results_file=args.test_results
        )
        logger.info("改善レポート生成完了")
        
    except Exception as e:
        logger.error(f"改善レポート生成エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
