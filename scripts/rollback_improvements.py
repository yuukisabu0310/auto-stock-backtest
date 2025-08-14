#!/usr/bin/env python3
"""
改善ロールバックスクリプト
失敗した改善をロールバックします。
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

logger = get_logger("rollback_improvements")

class ImprovementRollbacker:
    """改善ロールバッククラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        
    def rollback_failed_improvements(self, 
                                      evaluation_results_file: str = "evaluation_results.json",
                                      auto_rollback: bool = False) -> bool:
        """失敗した改善をロールバック"""
        
        logger.info("失敗した改善のロールバック開始")
        
        # 評価結果を読み込み
        evaluation = self._load_evaluation_results(evaluation_results_file)
        if not evaluation:
            logger.warning("評価結果が見つかりませんでした")
            return False
        
        # 失敗した改善を特定
        failed_improvements = evaluation.get('failed_details', [])
        if not failed_improvements:
            logger.info("ロールバック対象の失敗した改善がありません")
            return True
        
        rollback_count = 0
        
        for detail in failed_improvements:
            strategy_name = detail['strategy_name']
            
            if improvement_history.can_rollback(strategy_name):
                rollback_target = improvement_history.get_rollback_target(strategy_name)
                if rollback_target:
                    if self._execute_rollback(strategy_name, rollback_target):
                        rollback_count += 1
                        logger.info(f"ロールバック完了: {strategy_name} -> {rollback_target.id}")
                else:
                    logger.warning(f"ロールバック対象が見つかりません: {strategy_name}")
            else:
                logger.warning(f"ロールバックできません: {strategy_name}")
        
        logger.info(f"ロールバック完了: {rollback_count}戦略")
        return rollback_count > 0
    
    def rollback_specific_strategy(self, strategy_name: str) -> bool:
        """特定戦略のロールバック"""
        
        logger.info(f"戦略 '{strategy_name}' のロールバック開始")
        
        if not improvement_history.can_rollback(strategy_name):
            logger.warning(f"戦略 '{strategy_name}' のロールバックができません")
            return False
        
        rollback_target = improvement_history.get_rollback_target(strategy_name)
        if not rollback_target:
            logger.warning(f"ロールバック対象が見つかりません: {strategy_name}")
            return False
        
        success = self._execute_rollback(strategy_name, rollback_target)
        if success:
            logger.info(f"ロールバック完了: {strategy_name} -> {rollback_target.id}")
        else:
            logger.error(f"ロールバック失敗: {strategy_name}")
        
        return success
    
    def rollback_all_strategies(self) -> bool:
        """全戦略のロールバック"""
        
        logger.info("全戦略のロールバック開始")
        
        strategies = self.config.get('strategies', {})
        rollback_count = 0
        
        for strategy_name in strategies.keys():
            if improvement_history.can_rollback(strategy_name):
                rollback_target = improvement_history.get_rollback_target(strategy_name)
                if rollback_target:
                    if self._execute_rollback(strategy_name, rollback_target):
                        rollback_count += 1
                        logger.info(f"ロールバック完了: {strategy_name} -> {rollback_target.id}")
        
        logger.info(f"全戦略ロールバック完了: {rollback_count}戦略")
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
                
                return True
            else:
                logger.error(f"戦略 '{strategy_name}' の設定が見つかりません")
                return False
                
        except Exception as e:
            logger.error(f"ロールバック実行エラー: {e}")
            return False
    
    def print_rollback_status(self):
        """ロールバック可能な戦略の状況を表示"""
        summary = improvement_history.get_improvement_summary()
        
        print(f"\n=== ロールバック状況 ===")
        
        if not summary['strategies']:
            print("改善履歴がありません")
            return
        
        for strategy, stats in summary['strategies'].items():
            can_rollback = improvement_history.can_rollback(strategy)
            rollback_target = improvement_history.get_rollback_target(strategy) if can_rollback else None
            
            print(f"\n{strategy}:")
            print(f"  総改善回数: {stats['total']}")
            print(f"  採用: {stats['adopted']} | 失敗: {stats['failed']} | 保留: {stats['pending']}")
            print(f"  ロールバック可能: {'はい' if can_rollback else 'いいえ'}")
            
            if rollback_target:
                print(f"  ロールバック対象: {rollback_target.id} ({rollback_target.timestamp})")
                print(f"  対象スコア: {rollback_target.improvement_score:.4f}")

def main():
    parser = argparse.ArgumentParser(description='改善ロールバック')
    parser.add_argument('--failed-only', action='store_true', 
                        help='失敗した改善のみをロールバック')
    parser.add_argument('--strategy', type=str, help='特定戦略のロールバック')
    parser.add_argument('--all', action='store_true', 
                        help='全戦略のロールバック')
    parser.add_argument('--auto-rollback', action='store_true', 
                        help='自動ロールバック（失敗した改善のみ）')
    parser.add_argument('--evaluation-results', type=str, default='evaluation_results.json',
                        help='評価結果ファイル名')
    parser.add_argument('--status', action='store_true', 
                        help='ロールバック状況を表示')
    
    args = parser.parse_args()
    
    try:
        rollbacker = ImprovementRollbacker()
        
        if args.status:
            rollbacker.print_rollback_status()
            return
        
        if args.strategy:
            success = rollbacker.rollback_specific_strategy(args.strategy)
            sys.exit(0 if success else 1)
        
        if args.all:
            success = rollbacker.rollback_all_strategies()
            sys.exit(0 if success else 1)
        
        if args.failed_only or args.auto_rollback:
            success = rollbacker.rollback_failed_improvements(
                evaluation_results_file=args.evaluation_results,
                auto_rollback=args.auto_rollback
            )
            sys.exit(0 if success else 1)
        
        # デフォルト: 状況表示
        rollbacker.print_rollback_status()
        
    except Exception as e:
        logger.error(f"改善ロールバックエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
