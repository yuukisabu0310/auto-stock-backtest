#!/usr/bin/env python3
"""
改善提案テストスクリプト
生成された改善提案をテスト実行し、結果を評価します。
"""

import os
import sys
import json
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history, ImprovementMode
from src.ai_improver import ai_improver
from scripts.run_backtest_enhanced import EnhancedBacktestRunner

logger = get_logger("test_improvements")

class ImprovementTester:
    """改善提案テストクラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.backtest_runner = EnhancedBacktestRunner()
        
    def test_improvements(self, 
                         mode: str,
                         branch_name: str = None,
                         proposals_file: str = "improvement_proposals.json") -> List[Dict[str, Any]]:
        """改善提案をテスト実行"""
        
        logger.info(f"改善提案テスト開始 - モード: {mode}")
        
        # 改善提案を読み込み
        proposals = self._load_proposals(proposals_file)
        if not proposals:
            logger.warning("改善提案が見つかりませんでした")
            return []
        
        test_results = []
        
        for i, proposal in enumerate(proposals, 1):
            strategy_name = proposal['strategy_name']
            description = proposal['description']
            new_params = proposal['new_params']
            
            logger.info(f"テスト {i}/{len(proposals)}: {strategy_name} - {description}")
            
            try:
                # 改善提案をテスト実行
                result = self._test_single_proposal(proposal, mode, branch_name)
                test_results.append(result)
                
                logger.info(f"テスト完了: {strategy_name} - 改善スコア: {result.get('improvement_score', 0):.4f}")
                
            except Exception as e:
                logger.error(f"テスト失敗: {strategy_name} - {e}")
                result = {
                    'proposal': proposal,
                    'success': False,
                    'error': str(e),
                    'improvement_score': 0
                }
                test_results.append(result)
        
        # 結果を保存
        self._save_test_results(test_results)
        
        logger.info(f"改善提案テスト完了: {len(test_results)}件")
        return test_results
    
    def _load_proposals(self, proposals_file: str) -> List[Dict[str, Any]]:
        """改善提案を読み込み"""
        try:
            with open(proposals_file, 'r', encoding='utf-8') as f:
                proposals = json.load(f)
            logger.info(f"改善提案を読み込み: {len(proposals)}件")
            return proposals
        except FileNotFoundError:
            logger.error(f"改善提案ファイルが見つかりません: {proposals_file}")
            return []
        except Exception as e:
            logger.error(f"改善提案読み込みエラー: {e}")
            return []
    
    def _test_single_proposal(self, 
                             proposal: Dict[str, Any], 
                             mode: str,
                             branch_name: str = None) -> Dict[str, Any]:
        """単一の改善提案をテスト"""
        
        strategy_name = proposal['strategy_name']
        new_params = proposal['new_params']
        current_params = proposal['current_params']
        current_performance = proposal['current_performance']
        
        # 一時的な設定ファイルを作成
        temp_config = self._create_temp_config(strategy_name, new_params)
        
        try:
            # 新しいパラメータでバックテストを実行
            new_performance = self._run_backtest_with_params(strategy_name, new_params)
            
            if not new_performance:
                raise ValueError("バックテスト結果が取得できませんでした")
            
            # 改善提案を評価
            evaluation = ai_improver.evaluate_improvement_proposal(
                strategy_name=strategy_name,
                old_params=current_params,
                new_params=new_params,
                old_metrics=current_performance,
                new_metrics=new_performance
            )
            
            # 改善履歴に記録
            improvement_id = self._record_improvement(proposal, evaluation, mode, branch_name)
            
            result = {
                'proposal': proposal,
                'success': True,
                'new_performance': new_performance,
                'evaluation': evaluation,
                'improvement_id': improvement_id,
                'improvement_score': evaluation['improvement_score'],
                'improvement_level': evaluation['improvement_level']
            }
            
            return result
            
        finally:
            # 一時ファイルを削除
            if temp_config and temp_config.exists():
                temp_config.unlink()
    
    def _create_temp_config(self, strategy_name: str, new_params: Dict[str, Any]) -> Path:
        """一時的な設定ファイルを作成"""
        try:
            # 現在の設定を読み込み
            config_path = Path("config.yaml")
            if not config_path.exists():
                raise FileNotFoundError("config.yamlが見つかりません")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                import yaml
                config_data = yaml.safe_load(f)
            
            # 戦略パラメータを更新
            if 'strategies' in config_data and strategy_name in config_data['strategies']:
                config_data['strategies'][strategy_name].update(new_params)
            
            # 一時ファイルを作成
            temp_config = Path(tempfile.mktemp(suffix='.yaml'))
            with open(temp_config, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            return temp_config
            
        except Exception as e:
            logger.error(f"一時設定ファイル作成エラー: {e}")
            return None
    
    def _run_backtest_with_params(self, strategy_name: str, new_params: Dict[str, Any]) -> Dict[str, float]:
        """新しいパラメータでバックテストを実行"""
        try:
            # 一時的な設定でバックテストを実行
            # 実際の実装では、設定を動的に変更してバックテストを実行
            # ここでは簡略化のため、モック的な結果を返す
            
            # TODO: 実際のバックテスト実行ロジックを実装
            # 現在は、既存のバックテスト結果から推定値を計算
            
            # モック的な改善結果を生成
            mock_improvement = self._generate_mock_improvement(strategy_name, new_params)
            
            return mock_improvement
            
        except Exception as e:
            logger.error(f"バックテスト実行エラー: {e}")
            return {}
    
    def _generate_mock_improvement(self, strategy_name: str, new_params: Dict[str, Any]) -> Dict[str, float]:
        """モック的な改善結果を生成（開発用）"""
        # 実際の実装では、この部分を削除して実際のバックテスト結果を使用
        
        import random
        
        # ベースラインのパフォーマンス
        baseline = {
            'sharpe_ratio': 0.8,
            'sortino_ratio': 1.2,
            'calmar_ratio': 0.5,
            'max_drawdown': 0.15,
            'win_rate': 0.55,
            'profit_factor': 1.3,
            'total_return': 0.25
        }
        
        # パラメータ変更に基づいて改善を模擬
        improvement_factor = 1.0
        
        # SMA期間の変更による改善
        if 'sma_period' in new_params:
            old_period = 20  # 仮の元の値
            new_period = new_params['sma_period']
            if new_period < old_period:
                improvement_factor *= 1.1  # 短期化で改善
            elif new_period > old_period:
                improvement_factor *= 1.05  # 長期化で改善
        
        # ストップロスの変更による改善
        if 'stop_loss' in new_params:
            old_stop = 0.05  # 仮の元の値
            new_stop = new_params['stop_loss']
            if new_stop < old_stop:
                improvement_factor *= 1.15  # 厳格化で改善
        
        # ランダムな変動を追加
        random_factor = 0.9 + random.random() * 0.2  # 0.9-1.1の範囲
        
        final_factor = improvement_factor * random_factor
        
        # 改善されたパフォーマンスを計算
        improved = {}
        for key, value in baseline.items():
            if key == 'max_drawdown':
                # ドローダウンは小さい方が良い
                improved[key] = value / final_factor
            else:
                # その他は大きい方が良い
                improved[key] = value * final_factor
        
        return improved
    
    def _record_improvement(self, 
                          proposal: Dict[str, Any],
                          evaluation: Dict[str, Any],
                          mode: str,
                          branch_name: str = None) -> str:
        """改善履歴に記録"""
        
        improvement_mode = ImprovementMode.VERIFICATION if mode == 'verification' else ImprovementMode.ADOPTION
        
        improvement_id = improvement_history.add_improvement(
            mode=improvement_mode,
            strategy_name=proposal['strategy_name'],
            old_params=proposal['current_params'],
            new_params=proposal['new_params'],
            performance_metrics=evaluation.get('comparison', {}),
            improvement_score=evaluation['improvement_score'],
            description=proposal['description'],
            branch_name=branch_name or 'main',
            commit_hash='test-commit'  # 実際の実装ではGitコミットハッシュを使用
        )
        
        return improvement_id
    
    def _save_test_results(self, test_results: List[Dict[str, Any]], 
                          output_file: str = "test_results.json"):
        """テスト結果を保存"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"テスト結果を保存: {output_file}")
        except Exception as e:
            logger.error(f"テスト結果保存エラー: {e}")
    
    def print_test_summary(self, test_results: List[Dict[str, Any]]):
        """テスト結果のサマリーを表示"""
        if not test_results:
            print("テスト結果はありません")
            return
        
        successful_tests = [r for r in test_results if r.get('success', False)]
        failed_tests = [r for r in test_results if not r.get('success', False)]
        
        print(f"\n=== 改善提案テスト結果 ===")
        print(f"総テスト数: {len(test_results)}")
        print(f"成功: {len(successful_tests)}")
        print(f"失敗: {len(failed_tests)}")
        
        if successful_tests:
            print(f"\n--- 成功した改善提案 ---")
            for i, result in enumerate(successful_tests, 1):
                proposal = result['proposal']
                evaluation = result['evaluation']
                
                print(f"\n{i}. {proposal['strategy_name']}")
                print(f"   説明: {proposal['description']}")
                print(f"   改善スコア: {evaluation['improvement_score']:.4f}")
                print(f"   改善レベル: {evaluation['improvement_level']}")
                print(f"   推奨: {evaluation['recommendation']}")
        
        if failed_tests:
            print(f"\n--- 失敗した改善提案 ---")
            for i, result in enumerate(failed_tests, 1):
                proposal = result['proposal']
                error = result.get('error', '不明なエラー')
                
                print(f"\n{i}. {proposal['strategy_name']}")
                print(f"   説明: {proposal['description']}")
                print(f"   エラー: {error}")

def main():
    parser = argparse.ArgumentParser(description='改善提案テスト実行')
    parser.add_argument('--mode', choices=['verification', 'adoption'], 
                       default='verification', help='実行モード')
    parser.add_argument('--branch-name', type=str, help='ブランチ名')
    parser.add_argument('--proposals', type=str, default='improvement_proposals.json',
                       help='改善提案ファイル名')
    parser.add_argument('--output', type=str, default='test_results.json',
                       help='出力ファイル名')
    
    args = parser.parse_args()
    
    try:
        tester = ImprovementTester()
        
        # 改善提案をテスト
        test_results = tester.test_improvements(
            mode=args.mode,
            branch_name=args.branch_name,
            proposals_file=args.proposals
        )
        
        # 結果を保存
        if test_results:
            tester._save_test_results(test_results, args.output)
            tester.print_test_summary(test_results)
        else:
            logger.info("テスト結果がありませんでした")
        
        # 成功したテストの数を返す
        successful_count = len([r for r in test_results if r.get('success', False)])
        sys.exit(0 if successful_count > 0 else 1)
        
    except Exception as e:
        logger.error(f"改善提案テストエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
