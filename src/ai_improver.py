import json
import random
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history, ImprovementMode
from src.enhanced_metrics import enhanced_metrics

logger = get_logger("ai_improver")

class AIImprovementProposer:
    """AIによる改善提案を生成するクラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.improvement_config = self.config.get('ai_improvement', {})
        self.similarity_threshold = self.improvement_config.get('similarity_threshold', 0.9)
        self.max_improvements_per_run = self.improvement_config.get('max_improvements_per_run', 3)
        
    def analyze_performance_and_propose_improvements(self, 
                                                   strategy_name: str,
                                                   current_params: Dict[str, Any],
                                                   performance_metrics: Dict[str, float],
                                                   historical_data: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """パフォーマンスを分析して改善提案を生成"""
        
        logger.info(f"戦略 '{strategy_name}' の改善提案を生成中...")
        
        # 現在のパフォーマンスを分析
        analysis = self._analyze_current_performance(performance_metrics)
        
        # 改善提案を生成
        proposals = []
        
        # 1. パラメータ調整提案
        param_proposals = self._generate_parameter_improvements(
            strategy_name, current_params, analysis
        )
        proposals.extend(param_proposals)
        
        # 2. リスク管理改善提案
        risk_proposals = self._generate_risk_improvements(
            strategy_name, current_params, analysis
        )
        proposals.extend(risk_proposals)
        
        # 3. 戦略組み合わせ提案
        combination_proposals = self._generate_combination_improvements(
            strategy_name, current_params, analysis
        )
        proposals.extend(combination_proposals)
        
        # 類似提案のフィルタリング
        filtered_proposals = self._filter_similar_proposals(strategy_name, proposals)
        
        # 提案数を制限
        final_proposals = filtered_proposals[:self.max_improvements_per_run]
        
        logger.info(f"改善提案を生成しました: {len(final_proposals)}件")
        return final_proposals
    
    def _analyze_current_performance(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """現在のパフォーマンスを分析"""
        analysis = {
            'strengths': [],
            'weaknesses': [],
            'improvement_areas': [],
            'risk_level': 'medium'
        }
        
        # シャープレシオの分析
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe > 1.5:
            analysis['strengths'].append('高いシャープレシオ')
        elif sharpe < 0.5:
            analysis['weaknesses'].append('低いシャープレシオ')
            analysis['improvement_areas'].append('リターン/リスク比の改善')
        
        # 最大ドローダウンの分析
        max_dd = metrics.get('max_drawdown', 0)
        if max_dd < 0.1:
            analysis['strengths'].append('低い最大ドローダウン')
        elif max_dd > 0.3:
            analysis['weaknesses'].append('高い最大ドローダウン')
            analysis['improvement_areas'].append('リスク管理の強化')
            analysis['risk_level'] = 'high'
        
        # 勝率の分析
        win_rate = metrics.get('win_rate', 0)
        if win_rate > 0.6:
            analysis['strengths'].append('高い勝率')
        elif win_rate < 0.4:
            analysis['weaknesses'].append('低い勝率')
            analysis['improvement_areas'].append('エントリー/エグジット条件の改善')
        
        # 利益因子の分析
        profit_factor = metrics.get('profit_factor', 0)
        if profit_factor > 1.5:
            analysis['strengths'].append('高い利益因子')
        elif profit_factor < 1.0:
            analysis['weaknesses'].append('低い利益因子')
            analysis['improvement_areas'].append('損益比の改善')
        
        return analysis
    
    def _generate_parameter_improvements(self, 
                                       strategy_name: str,
                                       current_params: Dict[str, Any],
                                       analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """パラメータ調整による改善提案を生成"""
        proposals = []
        
        # 戦略別のパラメータ改善提案
        if strategy_name == 'FixedSma':
            proposals.extend(self._propose_sma_improvements(current_params, analysis))
        elif strategy_name == 'SmaCross':
            proposals.extend(self._propose_sma_cross_improvements(current_params, analysis))
        elif strategy_name == 'Momentum':
            proposals.extend(self._propose_momentum_improvements(current_params, analysis))
        
        return proposals
    
    def _propose_sma_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SMA戦略の改善提案"""
        proposals = []
        
        current_sma = current_params.get('sma_period', 20)
        
        # 短期SMAの提案（より敏感なエントリー）
        if '低い勝率' in analysis['weaknesses']:
            short_sma = max(5, current_sma - 5)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'SMA期間を{current_sma}から{short_sma}に短縮してエントリー感度を向上',
                'new_params': {**current_params, 'sma_period': short_sma},
                'expected_improvement': '勝率向上',
                'confidence': 0.7
            })
        
        # 長期SMAの提案（より安定したトレンド追従）
        if '高い最大ドローダウン' in analysis['weaknesses']:
            long_sma = min(50, current_sma + 10)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'SMA期間を{current_sma}から{long_sma}に延長してトレンド安定性を向上',
                'new_params': {**current_params, 'sma_period': long_sma},
                'expected_improvement': 'ドローダウン削減',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_sma_cross_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SMAクロス戦略の改善提案"""
        proposals = []
        
        fast_sma = current_params.get('fast_sma', 10)
        slow_sma = current_params.get('slow_sma', 30)
        
        # より敏感なクロス設定
        if '低い勝率' in analysis['weaknesses']:
            new_fast = max(5, fast_sma - 2)
            new_slow = max(new_fast + 5, slow_sma - 5)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'高速SMAを{fast_sma}→{new_fast}、低速SMAを{slow_sma}→{new_slow}に調整',
                'new_params': {**current_params, 'fast_sma': new_fast, 'slow_sma': new_slow},
                'expected_improvement': 'エントリー感度向上',
                'confidence': 0.7
            })
        
        # より安定したクロス設定
        if '高い最大ドローダウン' in analysis['weaknesses']:
            new_fast = min(20, fast_sma + 5)
            new_slow = min(50, slow_sma + 10)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'高速SMAを{fast_sma}→{new_fast}、低速SMAを{slow_sma}→{new_slow}に調整',
                'new_params': {**current_params, 'fast_sma': new_fast, 'slow_sma': new_slow},
                'expected_improvement': 'トレンド安定性向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_momentum_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """モメンタム戦略の改善提案"""
        proposals = []
        
        rsi_period = current_params.get('rsi_period', 14)
        rsi_oversold = current_params.get('rsi_oversold', 30)
        rsi_overbought = current_params.get('rsi_overbought', 70)
        
        # RSI感度向上
        if '低い勝率' in analysis['weaknesses']:
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'RSI期間を{rsi_period}から{max(7, rsi_period-3)}に短縮',
                'new_params': {**current_params, 'rsi_period': max(7, rsi_period-3)},
                'expected_improvement': 'RSI感度向上',
                'confidence': 0.6
            })
        
        # RSI閾値調整
        if '低い利益因子' in analysis['weaknesses']:
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'RSI閾値を{rsi_oversold}/{rsi_overbought}から25/75に調整',
                'new_params': {**current_params, 'rsi_oversold': 25, 'rsi_overbought': 75},
                'expected_improvement': 'エントリー精度向上',
                'confidence': 0.5
            })
        
        return proposals
    
    def _generate_risk_improvements(self, 
                                  strategy_name: str,
                                  current_params: Dict[str, Any],
                                  analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """リスク管理の改善提案を生成"""
        proposals = []
        
        # ストップロス調整
        if '高い最大ドローダウン' in analysis['weaknesses']:
            current_stop_loss = current_params.get('stop_loss', 0.05)
            tighter_stop = max(0.02, current_stop_loss * 0.8)
            proposals.append({
                'type': 'risk_management',
                'description': f'ストップロスを{current_stop_loss:.1%}から{tighter_stop:.1%}に厳格化',
                'new_params': {**current_params, 'stop_loss': tighter_stop},
                'expected_improvement': 'ドローダウン削減',
                'confidence': 0.8
            })
        
        # ポジションサイズ調整
        if analysis['risk_level'] == 'high':
            current_max_position = current_params.get('max_position_size', 0.1)
            smaller_position = max(0.05, current_max_position * 0.7)
            proposals.append({
                'type': 'risk_management',
                'description': f'最大ポジションサイズを{current_max_position:.1%}から{smaller_position:.1%}に削減',
                'new_params': {**current_params, 'max_position_size': smaller_position},
                'expected_improvement': 'リスク分散',
                'confidence': 0.9
            })
        
        # 利確調整
        if '低い利益因子' in analysis['weaknesses']:
            current_take_profit = current_params.get('take_profit', 0.1)
            higher_take_profit = current_take_profit * 1.5
            proposals.append({
                'type': 'risk_management',
                'description': f'利確を{current_take_profit:.1%}から{higher_take_profit:.1%}に引き上げ',
                'new_params': {**current_params, 'take_profit': higher_take_profit},
                'expected_improvement': '利益因子向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _generate_combination_improvements(self, 
                                         strategy_name: str,
                                         current_params: Dict[str, Any],
                                         analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """戦略組み合わせの改善提案を生成"""
        proposals = []
        
        # フィルター追加
        if '低い勝率' in analysis['weaknesses']:
            # ボラティリティフィルター追加
            proposals.append({
                'type': 'strategy_combination',
                'description': 'ATRベースのボラティリティフィルターを追加',
                'new_params': {**current_params, 'volatility_filter': True, 'atr_period': 14},
                'expected_improvement': 'エントリー精度向上',
                'confidence': 0.5
            })
        
        # トレンドフィルター追加
        if '低いシャープレシオ' in analysis['weaknesses']:
            proposals.append({
                'type': 'strategy_combination',
                'description': '長期移動平均によるトレンドフィルターを追加',
                'new_params': {**current_params, 'trend_filter': True, 'trend_sma': 50},
                'expected_improvement': 'トレンド追従性向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _filter_similar_proposals(self, strategy_name: str, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """類似提案をフィルタリング"""
        filtered_proposals = []
        
        for proposal in proposals:
            new_params = proposal['new_params']
            
            # 類似履歴をチェック
            similar_records = improvement_history.check_similar_improvements(
                strategy_name, new_params, self.similarity_threshold
            )
            
            if not similar_records:
                filtered_proposals.append(proposal)
            else:
                logger.info(f"類似提案を除外: {proposal['description']} (類似履歴: {len(similar_records)}件)")
        
        return filtered_proposals
    
    def evaluate_improvement_proposal(self, 
                                    strategy_name: str,
                                    old_params: Dict[str, Any],
                                    new_params: Dict[str, Any],
                                    old_metrics: Dict[str, float],
                                    new_metrics: Dict[str, float]) -> Dict[str, Any]:
        """改善提案の評価結果を生成"""
        
        # 改善スコアを計算
        improvement_score = self._calculate_improvement_score(old_metrics, new_metrics)
        
        # 改善度合いを判定
        improvement_level = self._determine_improvement_level(improvement_score)
        
        # 詳細な比較分析
        comparison = self._compare_metrics(old_metrics, new_metrics)
        
        evaluation = {
            'improvement_score': improvement_score,
            'improvement_level': improvement_level,
            'comparison': comparison,
            'recommendation': self._generate_recommendation(improvement_score, comparison),
            'risk_assessment': self._assess_improvement_risk(old_metrics, new_metrics)
        }
        
        return evaluation
    
    def _calculate_improvement_score(self, old_metrics: Dict[str, float], new_metrics: Dict[str, float]) -> float:
        """改善スコアを計算"""
        weights = {
            'sharpe_ratio': 0.25,
            'sortino_ratio': 0.20,
            'calmar_ratio': 0.15,
            'max_drawdown': 0.15,
            'win_rate': 0.10,
            'profit_factor': 0.10,
            'total_return': 0.05
        }
        
        score = 0.0
        for metric, weight in weights.items():
            old_val = old_metrics.get(metric, 0)
            new_val = new_metrics.get(metric, 0)
            
            if metric == 'max_drawdown':
                # ドローダウンは小さい方が良い
                improvement = (old_val - new_val) / max(abs(old_val), 0.01)
            else:
                # その他は大きい方が良い
                improvement = (new_val - old_val) / max(abs(old_val), 0.01)
            
            score += weight * improvement
        
        return score
    
    def _determine_improvement_level(self, score: float) -> str:
        """改善レベルを判定"""
        if score > 0.2:
            return 'significant'
        elif score > 0.1:
            return 'moderate'
        elif score > 0.05:
            return 'minor'
        elif score > -0.05:
            return 'neutral'
        else:
            return 'degradation'
    
    def _compare_metrics(self, old_metrics: Dict[str, float], new_metrics: Dict[str, float]) -> Dict[str, Any]:
        """メトリクスの詳細比較"""
        comparison = {
            'improved_metrics': [],
            'degraded_metrics': [],
            'unchanged_metrics': []
        }
        
        for metric in old_metrics.keys():
            old_val = old_metrics.get(metric, 0)
            new_val = new_metrics.get(metric, 0)
            
            if metric == 'max_drawdown':
                # ドローダウンは小さい方が良い
                if new_val < old_val * 0.95:
                    comparison['improved_metrics'].append(metric)
                elif new_val > old_val * 1.05:
                    comparison['degraded_metrics'].append(metric)
                else:
                    comparison['unchanged_metrics'].append(metric)
            else:
                # その他は大きい方が良い
                if new_val > old_val * 1.05:
                    comparison['improved_metrics'].append(metric)
                elif new_val < old_val * 0.95:
                    comparison['degraded_metrics'].append(metric)
                else:
                    comparison['unchanged_metrics'].append(metric)
        
        return comparison
    
    def _generate_recommendation(self, score: float, comparison: Dict[str, Any]) -> str:
        """推奨事項を生成"""
        if score > 0.2:
            return "強く推奨 - 大幅な改善が期待されます"
        elif score > 0.1:
            return "推奨 - 中程度の改善が期待されます"
        elif score > 0.05:
            return "軽微な改善 - 小さな改善が期待されます"
        elif score > -0.05:
            return "中立 - 大きな変化は期待されません"
        else:
            return "非推奨 - パフォーマンスの悪化が懸念されます"
    
    def _assess_improvement_risk(self, old_metrics: Dict[str, float], new_metrics: Dict[str, float]) -> str:
        """改善のリスクを評価"""
        # ドローダウンの悪化をチェック
        old_dd = old_metrics.get('max_drawdown', 0)
        new_dd = new_metrics.get('max_drawdown', 0)
        
        if new_dd > old_dd * 1.2:
            return 'high'
        elif new_dd > old_dd * 1.1:
            return 'medium'
        else:
            return 'low'

# グローバルインスタンス
ai_improver = AIImprovementProposer()
