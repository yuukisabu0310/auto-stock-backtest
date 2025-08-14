#!/usr/bin/env python3
"""
改善履歴更新スクリプト
成功した改善を採用状態に更新し、履歴レポートを生成します。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history

logger = get_logger("update_improvement_history")

class ImprovementHistoryUpdater:
    """改善履歴更新クラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        
    def update_history_for_adoption(self, evaluation_results_file: str = "evaluation_results.json"):
        """採用のための改善履歴を更新"""
        
        logger.info("改善履歴の採用更新を開始")
        
        # 評価結果を読み込み
        evaluation = self._load_evaluation_results(evaluation_results_file)
        if not evaluation:
            logger.warning("評価結果が見つかりませんでした")
            return False
        
        # 成功した改善を採用状態に更新
        successful_count = 0
        for detail in evaluation.get('successful_details', []):
            # 最新の成功した改善記録を取得
            strategy_name = detail['strategy_name']
            latest_improvement = improvement_history.get_latest_improvement(strategy_name)
            
            if latest_improvement and latest_improvement.status == 'success':
                improvement_history.update_status(latest_improvement.id, 'adopted')
                successful_count += 1
                logger.info(f"改善を採用: {strategy_name} (ID: {latest_improvement.id})")
        
        # 改善履歴レポートを生成
        self._generate_improvement_reports()
        
        logger.info(f"改善履歴更新完了: {successful_count}件を採用")
        return successful_count > 0
    
    def rollback_improvements(self, strategy_name: str = None, auto_rollback: bool = False):
        """改善のロールバックを実行"""
        
        logger.info(f"改善ロールバック開始 - 戦略: {strategy_name or '全戦略'}")
        
        if strategy_name:
            # 特定戦略のロールバック
            if improvement_history.can_rollback(strategy_name):
                rollback_target = improvement_history.get_rollback_target(strategy_name)
                if rollback_target:
                    self._execute_rollback(strategy_name, rollback_target)
                    return True
            else:
                logger.warning(f"戦略 '{strategy_name}' のロールバックができません")
                return False
        else:
            # 全戦略のロールバック
            strategies = self.config.get('strategies', {})
            rollback_count = 0
            
            for strategy in strategies.keys():
                if improvement_history.can_rollback(strategy):
                    rollback_target = improvement_history.get_rollback_target(strategy)
                    if rollback_target:
                        if self._execute_rollback(strategy, rollback_target):
                            rollback_count += 1
            
            logger.info(f"ロールバック完了: {rollback_count}戦略")
            return rollback_count > 0
    
    def _load_evaluation_results(self, evaluation_results_file: str) -> Dict[str, Any]:
        """評価結果を読み込み"""
        try:
            if Path(evaluation_results_file).exists():
                with open(evaluation_results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"評価結果読み込みエラー: {e}")
        return {}
    
    def _execute_rollback(self, strategy_name: str, rollback_target) -> bool:
        """ロールバックを実行"""
        try:
            # 設定ファイルを更新
            config_path = Path("config.yaml")
            if not config_path.exists():
                logger.error("config.yamlが見つかりません")
                return False
            
            # 設定を読み込み
            with open(config_path, 'r', encoding='utf-8') as f:
                import yaml
                config_data = yaml.safe_load(f)
            
            # 戦略パラメータをロールバック
            if 'strategies' in config_data and strategy_name in config_data['strategies']:
                config_data['strategies'][strategy_name] = rollback_target.new_params
                
                # 設定を保存
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
                
                # 改善履歴を更新
                improvement_history.update_status(rollback_target.id, 'rolled_back')
                
                logger.info(f"ロールバック完了: {strategy_name} -> {rollback_target.id}")
                return True
            else:
                logger.error(f"戦略 '{strategy_name}' の設定が見つかりません")
                return False
                
        except Exception as e:
            logger.error(f"ロールバック実行エラー: {e}")
            return False
    
    def _generate_improvement_reports(self):
        """改善履歴レポートを生成"""
        try:
            # HTMLレポートを生成
            improvement_history.export_history_report()
            
            # サマリーレポートを生成
            summary = improvement_history.get_improvement_summary()
            
            summary_file = Path("reports/improvement_summary.json")
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info("改善履歴レポートを生成しました")
            
        except Exception as e:
            logger.error(f"レポート生成エラー: {e}")
    
    def print_history_summary(self):
        """改善履歴のサマリーを表示"""
        summary = improvement_history.get_improvement_summary()
        
        print(f"\n=== 改善履歴サマリー ===")
        print(f"総改善回数: {summary['total']}")
        print(f"対象戦略数: {len(summary['strategies'])}")
        
        if summary['strategies']:
            print(f"\n--- 戦略別統計 ---")
            for strategy, stats in summary['strategies'].items():
                print(f"\n{strategy}:")
                print(f"  総改善回数: {stats['total']}")
                print(f"  採用: {stats['adopted']} | 失敗: {stats['failed']} | 保留: {stats['pending']}")
                print(f"  最高スコア: {stats['best_score']:.4f}")
        
        if summary['recent_improvements']:
            print(f"\n--- 最近の改善 ---")
            for record in summary['recent_improvements'][:5]:  # 最新5件
                print(f"  {record['strategy']} - {record['status']} (スコア: {record['score']:.4f})")

def main():
    parser = argparse.ArgumentParser(description='改善履歴更新')
    parser.add_argument('--adopt-successful', action='store_true', 
                        help='成功した改善を採用状態に更新')
    parser.add_argument('--rollback', type=str, help='指定戦略のロールバック')
    parser.add_argument('--auto-rollback', action='store_true', 
                        help='全戦略の自動ロールバック')
    parser.add_argument('--evaluation-results', type=str, default='evaluation_results.json',
                        help='評価結果ファイル名')
    parser.add_argument('--show-summary', action='store_true', 
                        help='改善履歴サマリーを表示')
    
    args = parser.parse_args()
    
    try:
        updater = ImprovementHistoryUpdater()
        
        if args.show_summary:
            updater.print_history_summary()
            return
        
        if args.rollback:
            success = updater.rollback_improvements(strategy_name=args.rollback)
            sys.exit(0 if success else 1)
        
        if args.auto_rollback:
            success = updater.rollback_improvements(auto_rollback=True)
            sys.exit(0 if success else 1)
        
        if args.adopt_successful:
            success = updater.update_history_for_adoption(args.evaluation_results)
            sys.exit(0 if success else 1)
        
        # デフォルト: サマリー表示
        updater.print_history_summary()
        
    except Exception as e:
        logger.error(f"改善履歴更新エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
