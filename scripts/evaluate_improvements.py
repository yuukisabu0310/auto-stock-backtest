#!/usr/bin/env python3
"""
改善提案評価スクリプト
テスト結果を評価し、成功した改善を特定します。
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
from src.ai_improver import ai_improver

logger = get_logger("evaluate_improvements")

class ImprovementEvaluator:
    """改善提案評価クラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.improvement_config = self.config.get('ai_improvement', {})
        self.score_threshold = self.improvement_config.get('improvement_score_threshold', 0.05)
        
    def evaluate_improvements(self, 
                              mode: str,
                              branch_name: str = None,
                              test_results_file: str = "test_results.json") -> Dict[str, Any]:
        """改善提案を評価"""
        
        logger.info(f"改善提案評価開始 - モード: {mode}")
        
        # テスト結果を読み込み
        test_results = self._load_test_results(test_results_file)
        if not test_results:
            logger.warning("テスト結果が見つかりませんでした")
            return self._create_empty_evaluation()
        
        # 成功した改善を特定
        successful_improvements = []
        failed_improvements = []
        
        for result in test_results:
            if result.get('success', False):
                improvement_score = result.get('improvement_score', 0)
                
                if improvement_score >= self.score_threshold:
                    successful_improvements.append(result)
                    # 改善履歴のステータスを更新
                    improvement_id = result.get('improvement_id')
                    if improvement_id:
                        improvement_history.update_status(improvement_id, 'success')
                else:
                    failed_improvements.append(result)
                    # 改善履歴のステータスを更新
                    improvement_id = result.get('improvement_id')
                    if improvement_id:
                        improvement_history.update_status(improvement_id, 'failed')
            else:
                failed_improvements.append(result)
                # 改善履歴のステータスを更新
                improvement_id = result.get('improvement_id')
                if improvement_id:
                    improvement_history.update_status(improvement_id, 'failed')
        
        # 評価結果を構築
        evaluation = {
            'mode': mode,
            'branch_name': branch_name,
            'total_tests': len(test_results),
            'successful_improvements': len(successful_improvements),
            'failed_improvements': len(failed_improvements),
            'success_rate': len(successful_improvements) / len(test_results) if test_results else 0,
            'score_threshold': self.score_threshold,
            'successful_details': self._extract_improvement_details(successful_improvements),
            'failed_details': self._extract_improvement_details(failed_improvements),
            'recommendations': self._generate_recommendations(successful_improvements, failed_improvements)
        }
        
        # 評価結果を保存
        self._save_evaluation_results(evaluation)
        
        logger.info(f"改善提案評価完了: 成功 {len(successful_improvements)}件, 失敗 {len(failed_improvements)}件")
        return evaluation
    
    def _load_test_results(self, test_results_file: str) -> List[Dict[str, Any]]:
        """テスト結果を読み込み"""
        try:
            if Path(test_results_file).exists():
                with open(test_results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"テスト結果読み込みエラー: {e}")
        return []
    
    def _create_empty_evaluation(self) -> Dict[str, Any]:
        """空の評価結果を作成"""
        return {
            'mode': 'unknown',
            'branch_name': None,
            'total_tests': 0,
            'successful_improvements': 0,
            'failed_improvements': 0,
            'success_rate': 0,
            'score_threshold': self.score_threshold,
            'successful_details': [],
            'failed_details': [],
            'recommendations': []
        }
    
    def _extract_improvement_details(self, improvements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """改善詳細を抽出"""
        details = []
        
        for improvement in improvements:
            proposal = improvement.get('proposal', {})
            evaluation = improvement.get('evaluation', {})
            
            detail = {
                'strategy_name': proposal.get('strategy_name', ''),
                'description': proposal.get('description', ''),
                'improvement_score': improvement.get('improvement_score', 0),
                'improvement_level': evaluation.get('improvement_level', ''),
                'recommendation': evaluation.get('recommendation', ''),
                'risk_assessment': evaluation.get('risk_assessment', ''),
                'improved_metrics': evaluation.get('comparison', {}).get('improved_metrics', []),
                'degraded_metrics': evaluation.get('comparison', {}).get('degraded_metrics', [])
            }
            details.append(detail)
        
        return details
    
    def _generate_recommendations(self, 
                                  successful_improvements: List[Dict[str, Any]],
                                  failed_improvements: List[Dict[str, Any]]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        if successful_improvements:
            recommendations.append(f"{len(successful_improvements)}件の改善が成功しました")
            
            # 戦略別の成功数を集計
            strategy_success = {}
            for improvement in successful_improvements:
                strategy = improvement.get('proposal', {}).get('strategy_name', '')
                strategy_success[strategy] = strategy_success.get(strategy, 0) + 1
            
            for strategy, count in strategy_success.items():
                recommendations.append(f"- {strategy}: {count}件の改善")
        
        if failed_improvements:
            recommendations.append(f"{len(failed_improvements)}件の改善が失敗しました")
            
            # 失敗理由を分析
            failure_reasons = {}
            for improvement in failed_improvements:
                if not improvement.get('success', False):
                    error = improvement.get('error', '不明なエラー')
                    failure_reasons[error] = failure_reasons.get(error, 0) + 1
            
            for reason, count in failure_reasons.items():
                recommendations.append(f"- 失敗理由: {reason} ({count}件)")
        
        # 全体的な推奨事項
        if successful_improvements:
            avg_score = sum(i.get('improvement_score', 0) for i in successful_improvements) / len(successful_improvements)
            if avg_score > 0.2:
                recommendations.append("大幅な改善が確認されました - 採用を強く推奨します")
            elif avg_score > 0.1:
                recommendations.append("中程度の改善が確認されました - 採用を推奨します")
            else:
                recommendations.append("軽微な改善が確認されました - 慎重に検討してください")
        
        return recommendations
    
    def _save_evaluation_results(self, evaluation: Dict[str, Any], 
                                  output_file: str = "evaluation_results.json"):
        """評価結果を保存"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(evaluation, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"評価結果を保存: {output_file}")
        except Exception as e:
            logger.error(f"評価結果保存エラー: {e}")
    
    def print_evaluation_summary(self, evaluation: Dict[str, Any]):
        """評価結果のサマリーを表示"""
        print(f"\n=== 改善提案評価結果 ===")
        print(f"実行モード: {evaluation['mode']}")
        print(f"総テスト数: {evaluation['total_tests']}")
        print(f"成功: {evaluation['successful_improvements']}")
        print(f"失敗: {evaluation['failed_improvements']}")
        print(f"成功率: {evaluation['success_rate']:.1%}")
        print(f"スコア閾値: {evaluation['score_threshold']}")
        
        if evaluation['successful_details']:
            print(f"\n--- 成功した改善 ---")
            for i, detail in enumerate(evaluation['successful_details'], 1):
                print(f"\n{i}. {detail['strategy_name']}")
                print(f"   説明: {detail['description']}")
                print(f"   改善スコア: {detail['improvement_score']:.4f}")
                print(f"   改善レベル: {detail['improvement_level']}")
                print(f"   推奨: {detail['recommendation']}")
                print(f"   リスク評価: {detail['risk_assessment']}")
                
                if detail['improved_metrics']:
                    print(f"   改善メトリクス: {', '.join(detail['improved_metrics'])}")
                if detail['degraded_metrics']:
                    print(f"   悪化メトリクス: {', '.join(detail['degraded_metrics'])}")
        
        if evaluation['recommendations']:
            print(f"\n--- 推奨事項 ---")
            for recommendation in evaluation['recommendations']:
                print(f"- {recommendation}")

def main():
    parser = argparse.ArgumentParser(description='改善提案評価')
    parser.add_argument('--mode', choices=['verification', 'adoption'], 
                        default='verification', help='実行モード')
    parser.add_argument('--branch-name', type=str, help='ブランチ名')
    parser.add_argument('--test-results', type=str, default='test_results.json',
                        help='テスト結果ファイル名')
    parser.add_argument('--output', type=str, default='evaluation_results.json',
                        help='出力ファイル名')
    
    args = parser.parse_args()
    
    try:
        evaluator = ImprovementEvaluator()
        
        # 改善提案を評価
        evaluation = evaluator.evaluate_improvements(
            mode=args.mode,
            branch_name=args.branch_name,
            test_results_file=args.test_results
        )
        
        # 結果を保存
        evaluator._save_evaluation_results(evaluation, args.output)
        evaluator.print_evaluation_summary(evaluation)
        
        # 成功した改善の数を返す
        successful_count = evaluation['successful_improvements']
        sys.exit(0 if successful_count > 0 else 1)
        
    except Exception as e:
        logger.error(f"改善提案評価エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
