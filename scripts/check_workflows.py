#!/usr/bin/env python3
"""
GitHubワークフロー実行状況チェックスクリプト
"""

import os
import sys
import time
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import ConfigManager
from src.logger import BacktestLogger

logger = BacktestLogger(__name__)

class WorkflowChecker:
    """GitHubワークフローの実行状況をチェックするクラス"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # GitHub API設定
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'your-username')
        self.repo_name = os.getenv('GITHUB_REPOSITORY_NAME', 'auto-stock-backtest')
        
        if not self.github_token:
            logger.error("GITHUB_TOKENが設定されていません")
            sys.exit(1)
        
        self.api_base = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 監視対象ワークフロー
        self.target_workflows = [
            'Daily Backtest',
            'AI Improvement Loop'
        ]
        
        # チェック設定
        self.max_wait_time = 30 * 60  # 30分
        self.check_interval = 30  # 30秒間隔
        self.max_retries = 3
    
    def get_workflow_id(self, workflow_name: str) -> Optional[int]:
        """ワークフローIDを取得"""
        try:
            url = f"{self.api_base}/actions/workflows"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            workflows = response.json()['workflows']
            for workflow in workflows:
                if workflow['name'] == workflow_name:
                    return workflow['id']
            
            logger.warning(f"ワークフロー '{workflow_name}' が見つかりません")
            return None
            
        except Exception as e:
            logger.error(f"ワークフローID取得エラー: {e}")
            return None
    
    def get_latest_workflow_run(self, workflow_id: int) -> Optional[Dict]:
        """最新のワークフロー実行を取得"""
        try:
            url = f"{self.api_base}/actions/workflows/{workflow_id}/runs"
            params = {
                'per_page': 1,
                'status': 'completed'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            runs = response.json()['workflow_runs']
            if runs:
                return runs[0]
            
            return None
            
        except Exception as e:
            logger.error(f"ワークフロー実行取得エラー: {e}")
            return None
    
    def get_workflow_status(self, workflow_id: int) -> Dict:
        """ワークフローの現在の状況を取得"""
        try:
            url = f"{self.api_base}/actions/workflows/{workflow_id}/runs"
            params = {'per_page': 5}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            runs = response.json()['workflow_runs']
            if not runs:
                return {'status': 'no_runs', 'message': '実行履歴がありません'}
            
            latest_run = runs[0]
            return {
                'id': latest_run['id'],
                'status': latest_run['status'],
                'conclusion': latest_run.get('conclusion'),
                'created_at': latest_run['created_at'],
                'updated_at': latest_run['updated_at'],
                'html_url': latest_run['html_url']
            }
            
        except Exception as e:
            logger.error(f"ワークフロー状況取得エラー: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def wait_for_workflow_completion(self, workflow_id: int, workflow_name: str) -> bool:
        """ワークフローの完了を待機"""
        logger.info(f"ワークフロー '{workflow_name}' の完了を待機中...")
        
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < self.max_wait_time:
            status = self.get_workflow_status(workflow_id)
            
            if status['status'] == 'error':
                logger.error(f"ワークフロー '{workflow_name}' エラー: {status['message']}")
                return False
            
            if status['status'] == 'no_runs':
                logger.warning(f"ワークフロー '{workflow_name}' の実行が見つかりません")
                return False
            
            current_status = f"{status['status']}"
            if status.get('conclusion'):
                current_status += f" ({status['conclusion']})"
            
            if current_status != last_status:
                logger.info(f"ワークフロー '{workflow_name}': {current_status}")
                last_status = current_status
            
            # 完了チェック
            if status['status'] == 'completed':
                if status.get('conclusion') == 'success':
                    logger.info(f"✅ ワークフロー '{workflow_name}' が正常完了しました")
                    return True
                else:
                    logger.error(f"❌ ワークフロー '{workflow_name}' が失敗しました: {status.get('conclusion')}")
                    return False
            
            # 実行中または待機中
            time.sleep(self.check_interval)
        
        logger.error(f"⏰ ワークフロー '{workflow_name}' の完了待機がタイムアウトしました")
        return False
    
    def check_all_workflows(self) -> Dict[str, bool]:
        """全ワークフローの状況をチェック"""
        results = {}
        
        logger.info("=== GitHubワークフロー実行状況チェック開始 ===")
        
        for workflow_name in self.target_workflows:
            logger.info(f"\n--- {workflow_name} チェック ---")
            
            # ワークフローID取得
            workflow_id = self.get_workflow_id(workflow_name)
            if not workflow_id:
                results[workflow_name] = False
                continue
            
            # 現在の状況確認
            status = self.get_workflow_status(workflow_id)
            logger.info(f"現在の状況: {status['status']}")
            
            if status['status'] == 'completed':
                if status.get('conclusion') == 'success':
                    logger.info(f"✅ {workflow_name} は既に正常完了済み")
                    results[workflow_name] = True
                else:
                    logger.error(f"❌ {workflow_name} は失敗済み")
                    results[workflow_name] = False
            elif status['status'] in ['in_progress', 'queued', 'waiting']:
                # 実行中の場合は完了を待機
                results[workflow_name] = self.wait_for_workflow_completion(workflow_id, workflow_name)
            else:
                logger.warning(f"⚠️ {workflow_name} の状況が不明: {status['status']}")
                results[workflow_name] = False
        
        return results
    
    def generate_summary_report(self, results: Dict[str, bool]) -> str:
        """結果サマリーレポートを生成"""
        report = "\n" + "="*50 + "\n"
        report += "GitHubワークフロー実行状況サマリー\n"
        report += "="*50 + "\n"
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        for workflow_name, success in results.items():
            status_icon = "✅" if success else "❌"
            status_text = "成功" if success else "失敗"
            report += f"{status_icon} {workflow_name}: {status_text}\n"
        
        report += f"\n総合結果: {success_count}/{total_count} 成功\n"
        
        if success_count == total_count:
            report += "🎉 全ワークフローが正常完了しました！\n"
        else:
            report += "⚠️ 一部のワークフローで問題が発生しました\n"
        
        report += "="*50 + "\n"
        return report
    
    def run(self) -> bool:
        """メイン実行"""
        try:
            results = self.check_all_workflows()
            summary = self.generate_summary_report(results)
            
            print(summary)
            logger.info(summary)
            
            # 全成功の場合のみTrueを返す
            return all(results.values())
            
        except Exception as e:
            logger.error(f"ワークフローチェック実行エラー: {e}")
            return False


def main():
    """メイン関数"""
    checker = WorkflowChecker()
    success = checker.run()
    
    if success:
        logger.info("全ワークフローが正常完了しました")
        sys.exit(0)
    else:
        logger.error("一部のワークフローで問題が発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
