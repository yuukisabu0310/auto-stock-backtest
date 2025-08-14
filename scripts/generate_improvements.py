#!/usr/bin/env python3
"""
AI改善提案生成スクリプト
現在のパフォーマンスを分析し、改善提案を生成します。
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
from src.improvement_history import improvement_history, ImprovementMode
from src.ai_improver import ai_improver
from src.strategy_base import StrategyFactory
from scripts.run_backtest_enhanced import EnhancedBacktestRunner

logger = get_logger("generate_improvements")

class ImprovementGenerator:
    """改善提案生成クラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.strategies_config = config.get_strategies_config()
        self.backtest_runner = EnhancedBacktestRunner()
        
    def generate_improvements(self, 
                            mode: str,
                            target_strategy: str = None,
                            force_improvement: bool = False) -> List[Dict[str, Any]]:
        """改善提案を生成"""
        
        logger.info(f"改善提案生成開始 - モード: {mode}, 対象戦略: {target_strategy or '全戦略'}")
        
        # 現在のパフォーマンスを取得
        current_performance = self._get_current_performance()
        
        if not current_performance:
            logger.warning("現在のパフォーマンスデータが取得できませんでした")
            return []
        
        all_proposals = []
        
        # 対象戦略を決定
        target_strategies = [target_strategy] if target_strategy else list(self.strategies_config.keys())
        
        for strategy_name in target_strategies:
            if strategy_name not in self.strategies_config:
                logger.warning(f"戦略 '{strategy_name}' が見つかりません")
                continue
            
            logger.info(f"戦略 '{strategy_name}' の改善提案を生成中...")
            
            # 現在のパラメータを取得
            current_params = self.strategies_config[strategy_name]
            
            # 現在のパフォーマンスメトリクスを取得
            strategy_performance = current_performance.get(strategy_name, {})
            
            if not strategy_performance:
                logger.warning(f"戦略 '{strategy_name}' のパフォーマンスデータがありません")
                continue
            
            # 改善提案を生成
            proposals = ai_improver.analyze_performance_and_propose_improvements(
                strategy_name=strategy_name,
                current_params=current_params,
                performance_metrics=strategy_performance
            )
            
            # 提案にメタデータを追加
            for proposal in proposals:
                proposal.update({
                    'strategy_name': strategy_name,
                    'current_params': current_params,
                    'current_performance': strategy_performance,
                    'mode': mode,
                    'force_improvement': force_improvement
                })
            
            all_proposals.extend(proposals)
            logger.info(f"戦略 '{strategy_name}' の改善提案: {len(proposals)}件")
        
        # 提案を優先度順にソート
        all_proposals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        logger.info(f"総改善提案数: {len(all_proposals)}件")
        return all_proposals
    
    def _get_current_performance(self) -> Dict[str, Dict[str, float]]:
        """現在のパフォーマンスを取得"""
        try:
            # 最新のバックテスト結果を読み込み
            reports_dir = Path("reports")
            if not reports_dir.exists():
                logger.warning("reportsディレクトリが存在しません")
                return {}
            
            performance_data = {}
            
            # 各戦略の最新結果を取得
            for strategy_name in self.strategies_config.keys():
                strategy_dir = reports_dir / strategy_name
                if not strategy_dir.exists():
                    continue
                
                # 最新の結果ファイルを探す
                result_files = list(strategy_dir.glob("*.csv"))
                if not result_files:
                    continue
                
                # 最新のファイルを読み込み
                latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
                try:
                    df = pd.read_csv(latest_file)
                    if not df.empty:
                        # 基本的なメトリクスを計算
                        metrics = self._calculate_basic_metrics(df)
                        performance_data[strategy_name] = metrics
                except Exception as e:
                    logger.error(f"ファイル読み込みエラー {latest_file}: {e}")
            
            return performance_data
            
        except Exception as e:
            logger.error(f"パフォーマンス取得エラー: {e}")
            return {}
    
    def _calculate_basic_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """基本的なメトリクスを計算"""
        metrics = {}
        
        try:
            # 基本的な統計量を計算
            if 'Return [%]' in df.columns:
                returns = df['Return [%]'] / 100
                metrics['total_return'] = returns.sum()
                metrics['volatility'] = returns.std() * (252 ** 0.5)  # 年率化
                
                if metrics['volatility'] > 0:
                    metrics['sharpe_ratio'] = (returns.mean() * 252) / metrics['volatility']
                else:
                    metrics['sharpe_ratio'] = 0
            
            if 'Trades' in df.columns:
                metrics['total_trades'] = df['Trades'].sum()
            
            if 'Win Rate [%]' in df.columns:
                metrics['win_rate'] = df['Win Rate [%]'].mean() / 100
            
            if 'Profit Factor' in df.columns:
                metrics['profit_factor'] = df['Profit Factor'].mean()
            
            if 'Max. Drawdown [%]' in df.columns:
                metrics['max_drawdown'] = df['Max. Drawdown [%]'].min() / 100
            
            # ソルティノレシオの計算
            if 'Return [%]' in df.columns and metrics.get('volatility', 0) > 0:
                negative_returns = returns[returns < 0]
                if len(negative_returns) > 0:
                    downside_deviation = negative_returns.std() * (252 ** 0.5)
                    if downside_deviation > 0:
                        metrics['sortino_ratio'] = (returns.mean() * 252) / downside_deviation
                    else:
                        metrics['sortino_ratio'] = 0
                else:
                    metrics['sortino_ratio'] = float('inf')
            
            # カルマーレシオの計算
            if metrics.get('total_return', 0) > 0 and abs(metrics.get('max_drawdown', 0)) > 0:
                metrics['calmar_ratio'] = metrics['total_return'] / abs(metrics['max_drawdown'])
            else:
                metrics['calmar_ratio'] = 0
                
        except Exception as e:
            logger.error(f"メトリクス計算エラー: {e}")
        
        return metrics
    
    def save_proposals(self, proposals: List[Dict[str, Any]], output_file: str = "improvement_proposals.json"):
        """改善提案をファイルに保存"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(proposals, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"改善提案を保存: {output_file}")
        except Exception as e:
            logger.error(f"提案保存エラー: {e}")
    
    def print_proposals_summary(self, proposals: List[Dict[str, Any]]):
        """改善提案のサマリーを表示"""
        if not proposals:
            print("改善提案はありません")
            return
        
        print(f"\n=== 改善提案サマリー ({len(proposals)}件) ===")
        
        for i, proposal in enumerate(proposals, 1):
            strategy_name = proposal['strategy_name']
            description = proposal['description']
            confidence = proposal.get('confidence', 0)
            expected_improvement = proposal.get('expected_improvement', '不明')
            
            print(f"\n{i}. {strategy_name}")
            print(f"   説明: {description}")
            print(f"   期待改善: {expected_improvement}")
            print(f"   信頼度: {confidence:.1%}")
            
            # パラメータ変更の詳細
            current_params = proposal['current_params']
            new_params = proposal['new_params']
            
            changed_params = []
            for key, new_value in new_params.items():
                if key in current_params and current_params[key] != new_value:
                    old_value = current_params[key]
                    changed_params.append(f"{key}: {old_value} → {new_value}")
            
            if changed_params:
                print(f"   変更パラメータ: {', '.join(changed_params)}")

def main():
    parser = argparse.ArgumentParser(description='AI改善提案生成')
    parser.add_argument('--mode', choices=['verification', 'adoption'], 
                       default='verification', help='実行モード')
    parser.add_argument('--strategy', type=str, help='対象戦略名（空欄で全戦略）')
    parser.add_argument('--force', action='store_true', help='強制改善実行')
    parser.add_argument('--output', type=str, default='improvement_proposals.json',
                       help='出力ファイル名')
    
    args = parser.parse_args()
    
    try:
        generator = ImprovementGenerator()
        
        # 改善提案を生成
        proposals = generator.generate_improvements(
            mode=args.mode,
            target_strategy=args.strategy,
            force_improvement=args.force
        )
        
        # 提案を保存
        if proposals:
            generator.save_proposals(proposals, args.output)
            generator.print_proposals_summary(proposals)
        else:
            logger.info("改善提案が生成されませんでした")
        
        # 終了コードを設定
        sys.exit(0 if proposals else 1)
        
    except Exception as e:
        logger.error(f"改善提案生成エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
