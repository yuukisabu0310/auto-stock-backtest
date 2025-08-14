#!/usr/bin/env python3
"""
AI改善ループ Slack通知スクリプト
改善結果と評価内容をSlackに通知します。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history

logger = get_logger("notify_ai_improvement")

class AIImprovementNotifier:
    """AI改善通知クラス"""
    
    def __init__(self):
        self.slack_config = config.get_notifications_config()
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.channel = os.getenv('SLACK_CHANNEL')
        
    def notify_improvement_results(self, 
                                 execution_mode: str,
                                 proposal_count: int = 0,
                                 successful_improvements: int = 0,
                                 test_results_file: str = "test_results.json",
                                 proposals_file: str = "improvement_proposals.json"):
        """改善結果をSlackに通知"""
        
        logger.info(f"AI改善結果通知開始 - モード: {execution_mode}")
        
        # テスト結果を読み込み
        test_results = self._load_test_results(test_results_file)
        proposals = self._load_proposals(proposals_file)
        
        # 通知メッセージを構築
        message = self._build_notification_message(
            execution_mode=execution_mode,
            proposal_count=proposal_count,
            successful_improvements=successful_improvements,
            test_results=test_results,
            proposals=proposals
        )
        
        # Slackに送信
        success = self._send_slack_message(message)
        
        if success:
            logger.info("AI改善結果通知完了")
        else:
            logger.error("AI改善結果通知失敗")
        
        return success
    
    def _load_test_results(self, test_results_file: str) -> List[Dict[str, Any]]:
        """テスト結果を読み込み"""
        try:
            if Path(test_results_file).exists():
                with open(test_results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"テスト結果読み込みエラー: {e}")
        return []
    
    def _load_proposals(self, proposals_file: str) -> List[Dict[str, Any]]:
        """改善提案を読み込み"""
        try:
            if Path(proposals_file).exists():
                with open(proposals_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"改善提案読み込みエラー: {e}")
        return []
    
    def _build_notification_message(self,
                                  execution_mode: str,
                                  proposal_count: int,
                                  successful_improvements: int,
                                  test_results: List[Dict[str, Any]],
                                  proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """通知メッセージを構築"""
        
        # 基本情報
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 実行モードに応じたアイコンとタイトル
        if execution_mode == 'verification':
            icon = "🔍"
            title = "AI改善検証完了"
            color = "#36a64f"  # 緑
        else:
            icon = "🚀"
            title = "AI改善採用完了"
            color = "#ff6b6b"  # 赤
        
        # 成功した改善の詳細
        successful_details = self._build_successful_improvements_details(test_results)
        
        # 失敗した改善の詳細
        failed_details = self._build_failed_improvements_details(test_results)
        
        # 改善履歴サマリー
        history_summary = self._build_history_summary()
        
        # Slackメッセージを構築
        message = {
            "text": f"{icon} {title}",
            "attachments": [
                {
                    "color": color,
                    "title": f"{icon} AI改善ループ実行結果",
                    "title_link": "https://github.com/your-repo/actions",
                    "fields": [
                        {
                            "title": "実行日時",
                            "value": timestamp,
                            "short": True
                        },
                        {
                            "title": "実行モード",
                            "value": execution_mode.upper(),
                            "short": True
                        },
                        {
                            "title": "改善提案数",
                            "value": str(proposal_count),
                            "short": True
                        },
                        {
                            "title": "成功した改善",
                            "value": str(successful_improvements),
                            "short": True
                        }
                    ],
                    "footer": "Auto Stock Backtest Bot",
                    "footer_icon": "https://github.com/favicon.ico",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        # 成功した改善の詳細を追加
        if successful_details:
            message["attachments"].append({
                "color": "#36a64f",
                "title": "✅ 成功した改善提案",
                "text": successful_details,
                "mrkdwn_in": ["text"]
            })
        
        # 失敗した改善の詳細を追加
        if failed_details:
            message["attachments"].append({
                "color": "#ff6b6b",
                "title": "❌ 失敗した改善提案",
                "text": failed_details,
                "mrkdwn_in": ["text"]
            })
        
        # 改善履歴サマリーを追加
        if history_summary:
            message["attachments"].append({
                "color": "#4a90e2",
                "title": "📊 改善履歴サマリー",
                "text": history_summary,
                "mrkdwn_in": ["text"]
            })
        
        return message
    
    def _build_successful_improvements_details(self, test_results: List[Dict[str, Any]]) -> str:
        """成功した改善の詳細を構築"""
        successful_results = [r for r in test_results if r.get('success', False)]
        
        if not successful_results:
            return "成功した改善はありませんでした。"
        
        details = []
        for i, result in enumerate(successful_results[:5], 1):  # 最大5件まで
            proposal = result['proposal']
            evaluation = result['evaluation']
            
            strategy_name = proposal['strategy_name']
            description = proposal['description']
            improvement_score = evaluation['improvement_score']
            improvement_level = evaluation['improvement_level']
            recommendation = evaluation['recommendation']
            
            details.append(
                f"*{i}. {strategy_name}*\n"
                f"• 説明: {description}\n"
                f"• 改善スコア: {improvement_score:.4f}\n"
                f"• 改善レベル: {improvement_level}\n"
                f"• 推奨: {recommendation}\n"
            )
        
        if len(successful_results) > 5:
            details.append(f"\n... 他 {len(successful_results) - 5}件の改善")
        
        return "\n".join(details)
    
    def _build_failed_improvements_details(self, test_results: List[Dict[str, Any]]) -> str:
        """失敗した改善の詳細を構築"""
        failed_results = [r for r in test_results if not r.get('success', False)]
        
        if not failed_results:
            return "失敗した改善はありませんでした。"
        
        details = []
        for i, result in enumerate(failed_results[:3], 1):  # 最大3件まで
            proposal = result['proposal']
            error = result.get('error', '不明なエラー')
            
            strategy_name = proposal['strategy_name']
            description = proposal['description']
            
            details.append(
                f"*{i}. {strategy_name}*\n"
                f"• 説明: {description}\n"
                f"• エラー: {error}\n"
            )
        
        if len(failed_results) > 3:
            details.append(f"\n... 他 {len(failed_results) - 3}件の失敗")
        
        return "\n".join(details)
    
    def _build_history_summary(self) -> str:
        """改善履歴サマリーを構築"""
        try:
            summary = improvement_history.get_improvement_summary()
            
            if not summary or summary['total'] == 0:
                return "改善履歴はありません。"
            
            details = [
                f"*総改善回数*: {summary['total']}回",
                f"*対象戦略数*: {len(summary['strategies'])}戦略"
            ]
            
            # 戦略別の統計
            for strategy, stats in summary['strategies'].items():
                details.append(
                    f"\n*{strategy}*:\n"
                    f"• 総改善: {stats['total']}回\n"
                    f"• 採用: {stats['adopted']}回\n"
                    f"• 失敗: {stats['failed']}回\n"
                    f"• 最高スコア: {stats['best_score']:.4f}"
                )
            
            # 最近の改善
            if summary['recent_improvements']:
                details.append("\n*最近の改善*:")
                for improvement in summary['recent_improvements'][:3]:
                    status_icon = "✅" if improvement['status'] == 'adopted' else "⏳"
                    details.append(
                        f"• {status_icon} {improvement['strategy']} "
                        f"(スコア: {improvement['score']:.4f})"
                    )
            
            return "\n".join(details)
            
        except Exception as e:
            logger.error(f"履歴サマリー構築エラー: {e}")
            return "履歴サマリーの取得に失敗しました。"
    
    def _send_slack_message(self, message: Dict[str, Any]) -> bool:
        """Slackにメッセージを送信"""
        try:
            if not self.webhook_url or self.webhook_url == "${SLACK_WEBHOOK_URL}":
                logger.info("SLACK_WEBHOOK_URLが設定されていないため、Slack通知をスキップします")
                self._print_message_content(message)
                return True  # エラーではなく正常終了として扱う
            
            # テスト用Webhook URLの場合はコンソール出力
            if "TEST/WEBHOOK/URL" in self.webhook_url:
                logger.info("テスト用Webhook URLのため、Slack通知をスキップしてコンソールに出力します")
                self._print_message_content(message)
                return True
            
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack通知送信成功")
                return True
            else:
                logger.error(f"Slack通知送信失敗: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack通知送信エラー: {e}")
            return False
    
    def _print_message_content(self, message: Dict[str, Any]):
        """メッセージ内容をコンソールに出力"""
        print("=== Slack通知内容 ===")
        print(f"チャンネル: {self.channel}")
        print(f"タイトル: {message.get('text', 'No title')}")
        
        if 'attachments' in message:
            for i, attachment in enumerate(message['attachments'], 1):
                print(f"\n--- 添付 {i} ---")
                print(f"タイトル: {attachment.get('title', 'No title')}")
                print(f"色: {attachment.get('color', 'No color')}")
                
                if 'fields' in attachment:
                    print("フィールド:")
                    for field in attachment['fields']:
                        print(f"  {field.get('title', 'No title')}: {field.get('value', 'No value')}")
                
                if 'text' in attachment:
                    print(f"内容: {attachment['text']}")
        
        print("===================")
    
    def send_detailed_report(self, test_results_file: str = "test_results.json"):
        """詳細レポートを送信"""
        try:
            test_results = self._load_test_results(test_results_file)
            if not test_results:
                logger.warning("詳細レポートの対象データがありません")
                return False
            
            # 詳細レポートメッセージを構築
            detailed_message = self._build_detailed_report_message(test_results)
            
            # Slackに送信
            return self._send_slack_message(detailed_message)
            
        except Exception as e:
            logger.error(f"詳細レポート送信エラー: {e}")
            return False
    
    def _build_detailed_report_message(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """詳細レポートメッセージを構築"""
        
        successful_results = [r for r in test_results if r.get('success', False)]
        failed_results = [r for r in test_results if not r.get('success', False)]
        
        # 統計情報
        total_tests = len(test_results)
        success_rate = len(successful_results) / total_tests if total_tests > 0 else 0
        
        # 平均改善スコア
        if successful_results:
            avg_improvement_score = sum(r.get('improvement_score', 0) for r in successful_results) / len(successful_results)
        else:
            avg_improvement_score = 0
        
        message = {
            "text": "📊 AI改善詳細レポート",
            "attachments": [
                {
                    "color": "#4a90e2",
                    "title": "📈 改善統計",
                    "fields": [
                        {
                            "title": "総テスト数",
                            "value": str(total_tests),
                            "short": True
                        },
                        {
                            "title": "成功率",
                            "value": f"{success_rate:.1%}",
                            "short": True
                        },
                        {
                            "title": "平均改善スコア",
                            "value": f"{avg_improvement_score:.4f}",
                            "short": True
                        },
                        {
                            "title": "最高改善スコア",
                            "value": f"{max((r.get('improvement_score', 0) for r in successful_results), default=0):.4f}",
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        # 戦略別の詳細
        strategy_details = self._build_strategy_details(test_results)
        if strategy_details:
            message["attachments"].append({
                "color": "#36a64f",
                "title": "🎯 戦略別改善結果",
                "text": strategy_details,
                "mrkdwn_in": ["text"]
            })
        
        # パラメータ変更の詳細
        param_details = self._build_parameter_details(test_results)
        if param_details:
            message["attachments"].append({
                "color": "#ff9500",
                "title": "⚙️ パラメータ変更詳細",
                "text": param_details,
                "mrkdwn_in": ["text"]
            })
        
        return message
    
    def _build_strategy_details(self, test_results: List[Dict[str, Any]]) -> str:
        """戦略別の詳細を構築"""
        strategy_stats = {}
        
        for result in test_results:
            strategy_name = result['proposal']['strategy_name']
            if strategy_name not in strategy_stats:
                strategy_stats[strategy_name] = {
                    'total': 0,
                    'success': 0,
                    'scores': []
                }
            
            strategy_stats[strategy_name]['total'] += 1
            if result.get('success', False):
                strategy_stats[strategy_name]['success'] += 1
                strategy_stats[strategy_name]['scores'].append(result.get('improvement_score', 0))
        
        details = []
        for strategy, stats in strategy_stats.items():
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            
            details.append(
                f"*{strategy}*:\n"
                f"• テスト数: {stats['total']}\n"
                f"• 成功率: {success_rate:.1%}\n"
                f"• 平均スコア: {avg_score:.4f}\n"
            )
        
        return "\n".join(details)
    
    def _build_parameter_details(self, test_results: List[Dict[str, Any]]) -> str:
        """パラメータ変更の詳細を構築"""
        param_changes = {}
        
        for result in test_results:
            if not result.get('success', False):
                continue
                
            proposal = result['proposal']
            current_params = proposal['current_params']
            new_params = proposal['new_params']
            
            for key, new_value in new_params.items():
                if key in current_params and current_params[key] != new_value:
                    if key not in param_changes:
                        param_changes[key] = {
                            'changes': [],
                            'avg_improvement': 0
                        }
                    
                    old_value = current_params[key]
                    improvement_score = result.get('improvement_score', 0)
                    
                    param_changes[key]['changes'].append({
                        'old': old_value,
                        'new': new_value,
                        'improvement': improvement_score
                    })
        
        # 平均改善スコアを計算
        for param, data in param_changes.items():
            if data['changes']:
                data['avg_improvement'] = sum(c['improvement'] for c in data['changes']) / len(data['changes'])
        
        # 改善スコア順にソート
        sorted_params = sorted(param_changes.items(), key=lambda x: x[1]['avg_improvement'], reverse=True)
        
        details = []
        for param, data in sorted_params[:5]:  # 上位5件まで
            details.append(
                f"*{param}*:\n"
                f"• 平均改善スコア: {data['avg_improvement']:.4f}\n"
                f"• 変更回数: {len(data['changes'])}回\n"
            )
            
            # 具体的な変更例
            for change in data['changes'][:2]:  # 最大2例まで
                details.append(
                    f"  - {change['old']} → {change['new']} "
                    f"(改善: {change['improvement']:.4f})\n"
                )
        
        return "\n".join(details) if details else "パラメータ変更の詳細はありません。"

def main():
    parser = argparse.ArgumentParser(description='AI改善結果 Slack通知')
    parser.add_argument('--execution-mode', type=str, default='verification',
                       choices=['verification', 'adoption'], help='実行モード')
    parser.add_argument('--proposal-count', type=int, default=0, help='改善提案数')
    parser.add_argument('--successful-improvements', type=int, default=0, help='成功した改善数')
    parser.add_argument('--test-results', type=str, default='test_results.json',
                       help='テスト結果ファイル')
    parser.add_argument('--proposals', type=str, default='improvement_proposals.json',
                       help='改善提案ファイル')
    parser.add_argument('--detailed', action='store_true', help='詳細レポート送信')
    
    args = parser.parse_args()
    
    try:
        notifier = AIImprovementNotifier()
        
        if args.detailed:
            # 詳細レポート送信
            success = notifier.send_detailed_report(args.test_results)
        else:
            # 通常の結果通知
            success = notifier.notify_improvement_results(
                execution_mode=args.execution_mode,
                proposal_count=args.proposal_count,
                successful_improvements=args.successful_improvements,
                test_results_file=args.test_results,
                proposals_file=args.proposals
            )
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"AI改善通知エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
