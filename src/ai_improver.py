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
from src.dynamic_optimizer import dynamic_optimizer

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
        
        # 4. 高度な改善提案
        advanced_proposals = self._generate_advanced_improvements(
            strategy_name, current_params, analysis, historical_data
        )
        proposals.extend(advanced_proposals)
        
        # 5. 動的最適化提案
        dynamic_proposals = self._generate_dynamic_optimization_proposals(
            strategy_name, current_params, performance_metrics
        )
        proposals.extend(dynamic_proposals)
        
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
        strategy_improvers = {
            'FixedSma': self._propose_sma_improvements,
            'SmaCross': self._propose_sma_cross_improvements,
            'Momentum': self._propose_momentum_improvements,
            'MovingAverageBreakout': self._propose_ma_breakout_improvements,
            'DonchianChannel': self._propose_donchian_improvements,
            'MACD': self._propose_macd_improvements,
            'RSIMomentum': self._propose_rsi_momentum_improvements,
            'RSIExtreme': self._propose_rsi_extreme_improvements,
            'BollingerBands': self._propose_bollinger_improvements,
            'Squeeze': self._propose_squeeze_improvements,
            'VolumeBreakout': self._propose_volume_breakout_improvements,
            'OBV': self._propose_obv_improvements,
            'TrendFollowing': self._propose_trend_following_improvements,
        }
        
        improver_func = strategy_improvers.get(strategy_name)
        if improver_func:
            proposals.extend(improver_func(current_params, analysis))
        else:
            logger.warning(f"戦略 '{strategy_name}' の改善提案は未実装です")
            # 汎用的な改善提案を生成
            proposals.extend(self._propose_generic_improvements(current_params, analysis))
        
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
    
    def _propose_ma_breakout_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """移動平均ブレイクアウト戦略の改善提案"""
        proposals = []
        
        sma_short = current_params.get('sma_short', [20, 30])[0] if current_params.get('sma_short') else 20
        sma_medium = current_params.get('sma_medium', [50, 60])[0] if current_params.get('sma_medium') else 50
        
        if '低い勝率' in analysis['weaknesses']:
            # より敏感な設定
            new_short = max(10, sma_short - 5)
            new_medium = max(new_short + 10, sma_medium - 10)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'短期SMAを{sma_short}→{new_short}、中期SMAを{sma_medium}→{new_medium}に調整',
                'new_params': {**current_params, 'sma_short': [new_short], 'sma_medium': [new_medium]},
                'expected_improvement': 'エントリー感度向上',
                'confidence': 0.7
            })
        
        return proposals
    
    def _propose_donchian_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ドンチャンチャネル戦略の改善提案"""
        proposals = []
        
        channel_period = current_params.get('channel_period', [55])[0] if current_params.get('channel_period') else 55
        
        if '高い最大ドローダウン' in analysis['weaknesses']:
            # より保守的な設定
            new_period = min(100, channel_period + 20)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'チャネル期間を{channel_period}→{new_period}に延長してブレイクアウトの信頼性向上',
                'new_params': {**current_params, 'channel_period': [new_period]},
                'expected_improvement': 'ドローダウン削減',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_macd_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """MACD戦略の改善提案"""
        proposals = []
        
        macd_fast = current_params.get('macd_fast', [12])[0] if current_params.get('macd_fast') else 12
        macd_slow = current_params.get('macd_slow', [26])[0] if current_params.get('macd_slow') else 26
        
        if '低いシャープレシオ' in analysis['weaknesses']:
            # より敏感な設定
            new_fast = max(8, macd_fast - 2)
            new_slow = max(new_fast + 8, macd_slow - 4)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'MACD高速を{macd_fast}→{new_fast}、低速を{macd_slow}→{new_slow}に調整',
                'new_params': {**current_params, 'macd_fast': [new_fast], 'macd_slow': [new_slow]},
                'expected_improvement': 'シグナル感度向上',
                'confidence': 0.65
            })
        
        return proposals
    
    def _propose_rsi_momentum_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """RSIモメンタム戦略の改善提案"""
        proposals = []
        
        rsi_period = current_params.get('rsi_period', [14])[0] if current_params.get('rsi_period') else 14
        rsi_entry = current_params.get('rsi_entry', [50])[0] if current_params.get('rsi_entry') else 50
        
        if '低い勝率' in analysis['weaknesses']:
            # エントリー閾値の調整
            new_entry = min(65, rsi_entry + 10)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'RSIエントリー閾値を{rsi_entry}→{new_entry}に引き上げてモメンタム強化',
                'new_params': {**current_params, 'rsi_entry': [new_entry]},
                'expected_improvement': 'エントリー精度向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_rsi_extreme_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """RSI極端値戦略の改善提案"""
        proposals = []
        
        rsi_oversold = current_params.get('rsi_oversold', [10])[0] if current_params.get('rsi_oversold') else 10
        rsi_overbought = current_params.get('rsi_overbought', [75])[0] if current_params.get('rsi_overbought') else 75
        
        if '低い利益因子' in analysis['weaknesses']:
            # より極端な閾値に調整
            new_oversold = max(5, rsi_oversold - 3)
            new_overbought = min(85, rsi_overbought + 5)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'RSI閾値を売られ過ぎ{rsi_oversold}→{new_oversold}、買われ過ぎ{rsi_overbought}→{new_overbought}に調整',
                'new_params': {**current_params, 'rsi_oversold': [new_oversold], 'rsi_overbought': [new_overbought]},
                'expected_improvement': 'エントリーの選択性向上',
                'confidence': 0.55
            })
        
        return proposals
    
    def _propose_bollinger_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ボリンジャーバンド戦略の改善提案"""
        proposals = []
        
        bb_period = current_params.get('bb_period', [20])[0] if current_params.get('bb_period') else 20
        bb_std = current_params.get('bb_std', [2.0])[0] if current_params.get('bb_std') else 2.0
        
        if '高い最大ドローダウン' in analysis['weaknesses']:
            # より保守的な設定
            new_std = min(2.5, bb_std + 0.3)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'ボリンジャーバンド標準偏差を{bb_std}→{new_std}に拡張してエントリー厳格化',
                'new_params': {**current_params, 'bb_std': [new_std]},
                'expected_improvement': 'ドローダウン削減',
                'confidence': 0.65
            })
        
        return proposals
    
    def _propose_squeeze_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """スクイーズ戦略の改善提案"""
        proposals = []
        
        bb_period = current_params.get('bb_period', [20])[0] if current_params.get('bb_period') else 20
        volume_multiplier = current_params.get('volume_multiplier', [1.5])[0] if current_params.get('volume_multiplier') else 1.5
        
        if '低い勝率' in analysis['weaknesses']:
            # 出来高フィルターを強化
            new_volume_mult = min(2.5, volume_multiplier + 0.3)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'出来高倍率を{volume_multiplier}→{new_volume_mult}に引き上げてエントリー精度向上',
                'new_params': {**current_params, 'volume_multiplier': [new_volume_mult]},
                'expected_improvement': 'エントリー品質向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_volume_breakout_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """出来高ブレイクアウト戦略の改善提案"""
        proposals = []
        
        breakout_period = current_params.get('breakout_period', [20])[0] if current_params.get('breakout_period') else 20
        volume_multiplier = current_params.get('volume_multiplier', [2.0])[0] if current_params.get('volume_multiplier') else 2.0
        
        if '低いシャープレシオ' in analysis['weaknesses']:
            # ブレイクアウト期間の最適化
            new_period = max(15, breakout_period - 5)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'ブレイクアウト期間を{breakout_period}→{new_period}に短縮して感度向上',
                'new_params': {**current_params, 'breakout_period': [new_period]},
                'expected_improvement': 'シグナル反応速度向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_obv_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """OBV戦略の改善提案"""
        proposals = []
        
        obv_period = current_params.get('obv_period', [20])[0] if current_params.get('obv_period') else 20
        
        if '低い勝率' in analysis['weaknesses']:
            # OBV期間の調整
            new_period = max(15, obv_period - 5)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'OBV期間を{obv_period}→{new_period}に短縮してトレンド感度向上',
                'new_params': {**current_params, 'obv_period': [new_period]},
                'expected_improvement': 'トレンド検出精度向上',
                'confidence': 0.6
            })
        
        return proposals
    
    def _propose_trend_following_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """トレンドフォロー戦略の改善提案"""
        proposals = []
        
        sma_short = current_params.get('sma_short', [20])[0] if current_params.get('sma_short') else 20
        sma_medium = current_params.get('sma_medium', [50])[0] if current_params.get('sma_medium') else 50
        adx_period = current_params.get('adx_period', [14])[0] if current_params.get('adx_period') else 14
        
        if '低いシャープレシオ' in analysis['weaknesses']:
            # トレンドフィルターの強化
            new_adx_period = min(21, adx_period + 3)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'ADX期間を{adx_period}→{new_adx_period}に延長してトレンド判定安定化',
                'new_params': {**current_params, 'adx_period': [new_adx_period]},
                'expected_improvement': 'トレンド判定精度向上',
                'confidence': 0.65
            })
        
        if '高い最大ドローダウン' in analysis['weaknesses']:
            # より保守的な移動平均設定
            new_short = min(30, sma_short + 5)
            new_medium = min(70, sma_medium + 10)
            proposals.append({
                'type': 'parameter_adjustment',
                'description': f'短期SMAを{sma_short}→{new_short}、中期SMAを{sma_medium}→{new_medium}に延長',
                'new_params': {**current_params, 'sma_short': [new_short], 'sma_medium': [new_medium]},
                'expected_improvement': 'ドローダウン削減',
                'confidence': 0.7
            })
        
        return proposals
    
    def _propose_generic_improvements(self, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """汎用的な改善提案"""
        proposals = []
        
        # 基本的なリスク管理改善
        if '高い最大ドローダウン' in analysis['weaknesses']:
            proposals.append({
                'type': 'generic_improvement',
                'description': 'ストップロス機能の強化',
                'new_params': {**current_params, 'enhanced_stop_loss': True},
                'expected_improvement': 'リスク管理強化',
                'confidence': 0.5
            })
        
        if '低い勝率' in analysis['weaknesses']:
            proposals.append({
                'type': 'generic_improvement',
                'description': 'エントリーフィルター追加',
                'new_params': {**current_params, 'entry_filter': True},
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
    
    def _generate_advanced_improvements(self, 
                                      strategy_name: str,
                                      current_params: Dict[str, Any],
                                      analysis: Dict[str, Any],
                                      historical_performance: List[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """高度な改善提案を生成"""
        proposals = []
        
        # 1. 機械学習ベースの最適化提案
        ml_proposals = self._generate_ml_optimization_proposals(
            strategy_name, current_params, analysis, historical_performance
        )
        proposals.extend(ml_proposals)
        
        # 2. 市場環境適応型提案
        adaptive_proposals = self._generate_adaptive_proposals(
            strategy_name, current_params, analysis
        )
        proposals.extend(adaptive_proposals)
        
        # 3. ポートフォリオ最適化提案
        portfolio_proposals = self._generate_portfolio_optimization_proposals(
            strategy_name, current_params, analysis
        )
        proposals.extend(portfolio_proposals)
        
        # 4. 動的リスク管理提案
        dynamic_risk_proposals = self._generate_dynamic_risk_proposals(
            strategy_name, current_params, analysis
        )
        proposals.extend(dynamic_risk_proposals)
        
        return proposals
    
    def _generate_ml_optimization_proposals(self, strategy_name: str, current_params: Dict[str, Any], 
                                          analysis: Dict[str, Any], historical_performance: List[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """機械学習ベースの最適化提案"""
        proposals = []
        
        # パフォーマンス履歴がある場合の学習ベース提案
        if historical_performance and len(historical_performance) >= 5:
            # トレンド分析
            recent_performance = historical_performance[-3:]
            performance_trend = self._analyze_performance_trend(recent_performance)
            
            if performance_trend == 'declining':
                proposals.append({
                    'type': 'ml_optimization',
                    'description': f'パフォーマンス低下傾向検出 - {strategy_name}の感度調整を推奨',
                    'new_params': self._suggest_sensitivity_adjustment(current_params, 'increase'),
                    'expected_improvement': 'パフォーマンス回復',
                    'confidence': 0.75,
                    'ml_based': True
                })
            elif performance_trend == 'volatile':
                proposals.append({
                    'type': 'ml_optimization',
                    'description': f'高ボラティリティ検出 - {strategy_name}の安定化調整を推奨',
                    'new_params': self._suggest_stability_adjustment(current_params),
                    'expected_improvement': 'パフォーマンス安定化',
                    'confidence': 0.7,
                    'ml_based': True
                })
        
        # 相関分析ベース提案
        correlation_proposal = self._generate_correlation_based_proposal(strategy_name, current_params, analysis)
        if correlation_proposal:
            proposals.append(correlation_proposal)
        
        return proposals
    
    def _generate_adaptive_proposals(self, strategy_name: str, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """市場環境適応型提案"""
        proposals = []
        
        # 市場状況に応じた動的調整
        market_regime = self._detect_market_regime(analysis)
        
        if market_regime == 'trending':
            proposals.append({
                'type': 'adaptive_optimization',
                'description': f'トレンド市場検出 - {strategy_name}のトレンドフォロー強化',
                'new_params': self._enhance_trend_following(current_params),
                'expected_improvement': 'トレンド市場での収益性向上',
                'confidence': 0.8,
                'market_adaptive': True
            })
        elif market_regime == 'ranging':
            proposals.append({
                'type': 'adaptive_optimization',
                'description': f'レンジ市場検出 - {strategy_name}の逆張り要素強化',
                'new_params': self._enhance_mean_reversion(current_params),
                'expected_improvement': 'レンジ市場での収益性向上',
                'confidence': 0.75,
                'market_adaptive': True
            })
        elif market_regime == 'volatile':
            proposals.append({
                'type': 'adaptive_optimization',
                'description': f'高ボラティリティ市場検出 - {strategy_name}のリスク管理強化',
                'new_params': self._enhance_volatility_protection(current_params),
                'expected_improvement': 'ボラティリティ耐性向上',
                'confidence': 0.85,
                'market_adaptive': True
            })
        
        return proposals
    
    def _generate_portfolio_optimization_proposals(self, strategy_name: str, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ポートフォリオ最適化提案"""
        proposals = []
        
        # 分散効果の向上
        proposals.append({
            'type': 'portfolio_optimization',
            'description': f'{strategy_name}の分散効果最適化 - 相関の低い銘柄群への重点配分',
            'new_params': {**current_params, 'diversification_enhancement': True},
            'expected_improvement': 'ポートフォリオ分散効果向上',
            'confidence': 0.6,
            'portfolio_based': True
        })
        
        # リスクパリティ調整
        if '高い最大ドローダウン' in analysis['weaknesses']:
            proposals.append({
                'type': 'portfolio_optimization',
                'description': f'{strategy_name}のリスクパリティ調整 - 各銘柄のリスク寄与度均等化',
                'new_params': {**current_params, 'risk_parity': True},
                'expected_improvement': 'リスク分散の最適化',
                'confidence': 0.7,
                'portfolio_based': True
            })
        
        return proposals
    
    def _generate_dynamic_risk_proposals(self, strategy_name: str, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """動的リスク管理提案"""
        proposals = []
        
        # VaRベースのポジションサイジング
        proposals.append({
            'type': 'dynamic_risk_management',
            'description': f'{strategy_name}にVaRベース動的ポジションサイジング導入',
            'new_params': {**current_params, 'var_based_sizing': True, 'var_confidence': 0.95},
            'expected_improvement': 'リスク調整後リターン向上',
            'confidence': 0.8,
            'dynamic_risk': True
        })
        
        # ボラティリティターゲット調整
        if 'ボラティリティ' in analysis.get('metrics', {}):
            proposals.append({
                'type': 'dynamic_risk_management',
                'description': f'{strategy_name}にボラティリティターゲット機能追加',
                'new_params': {**current_params, 'volatility_targeting': True, 'target_volatility': 0.15},
                'expected_improvement': 'リスク水準の安定化',
                'confidence': 0.75,
                'dynamic_risk': True
            })
        
        return proposals
    
    def _analyze_performance_trend(self, recent_performance: List[Dict[str, float]]) -> str:
        """パフォーマンストレンドを分析"""
        if len(recent_performance) < 2:
            return 'insufficient_data'
        
        sharpe_values = [p.get('sharpe_ratio', 0) for p in recent_performance]
        
        # トレンド分析
        if len(sharpe_values) >= 3:
            trend = np.polyfit(range(len(sharpe_values)), sharpe_values, 1)[0]
            volatility = np.std(sharpe_values)
            
            if trend < -0.1:
                return 'declining'
            elif volatility > 0.5:
                return 'volatile'
            elif trend > 0.1:
                return 'improving'
        
        return 'stable'
    
    def _detect_market_regime(self, analysis: Dict[str, Any]) -> str:
        """市場状況を検出"""
        # 簡単な市場状況判定（実際にはより複雑な分析が必要）
        max_dd = analysis.get('metrics', {}).get('max_drawdown', 0)
        sharpe = analysis.get('metrics', {}).get('sharpe_ratio', 0)
        
        if max_dd > 0.2:
            return 'volatile'
        elif sharpe > 1.0:
            return 'trending'
        else:
            return 'ranging'
    
    def _suggest_sensitivity_adjustment(self, current_params: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """感度調整の提案"""
        new_params = current_params.copy()
        
        # パラメータの感度を調整
        for key, value in current_params.items():
            if isinstance(value, list) and len(value) > 0:
                if 'period' in key.lower() or 'sma' in key.lower():
                    if direction == 'increase':
                        # より敏感に（期間を短く）
                        new_params[key] = [max(5, int(v * 0.8)) for v in value]
                    else:
                        # より保守的に（期間を長く）
                        new_params[key] = [min(100, int(v * 1.2)) for v in value]
        
        return new_params
    
    def _suggest_stability_adjustment(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """安定化調整の提案"""
        new_params = current_params.copy()
        
        # より安定したパラメータに調整
        for key, value in current_params.items():
            if isinstance(value, list) and len(value) > 0:
                if 'period' in key.lower():
                    # 期間を長くして安定化
                    new_params[key] = [min(50, int(v * 1.3)) for v in value]
        
        return new_params
    
    def _enhance_trend_following(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """トレンドフォロー強化"""
        new_params = current_params.copy()
        new_params['trend_enhancement'] = True
        new_params['trend_filter_strength'] = 1.2
        return new_params
    
    def _enhance_mean_reversion(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """逆張り要素強化"""
        new_params = current_params.copy()
        new_params['mean_reversion_enhancement'] = True
        new_params['reversion_strength'] = 1.1
        return new_params
    
    def _enhance_volatility_protection(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """ボラティリティ保護強化"""
        new_params = current_params.copy()
        new_params['volatility_protection'] = True
        new_params['volatility_threshold'] = 0.8
        return new_params
    
    def _generate_correlation_based_proposal(self, strategy_name: str, current_params: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """相関分析ベース提案"""
        # 簡単な相関ベース提案（実際にはより複雑な分析が必要）
        return {
            'type': 'correlation_optimization',
            'description': f'{strategy_name}の銘柄間相関を考慮した最適化',
            'new_params': {**current_params, 'correlation_adjustment': True},
            'expected_improvement': '分散効果向上',
            'confidence': 0.6,
            'correlation_based': True
        }
    
    def _generate_dynamic_optimization_proposals(self, strategy_name: str, current_params: Dict[str, Any], performance_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """動的最適化ベースの提案を生成"""
        proposals = []
        
        # 動的最適化システムから最適化されたパラメータを取得
        try:
            # パフォーマンスを動的最適化システムに更新
            dynamic_optimizer.update_performance(strategy_name, performance_metrics)
            
            # 最適化されたパラメータを取得
            optimized_params = dynamic_optimizer.optimize_parameters(strategy_name)
            
            if optimized_params and optimized_params != current_params:
                # 最適化状況を取得
                optimization_status = dynamic_optimizer.get_optimization_status()
                strategy_status = optimization_status.get('strategies', {}).get(strategy_name, {})
                
                proposals.append({
                    'type': 'dynamic_optimization',
                    'description': f'{strategy_name}の動的最適化による自動調整 (収束状態: {strategy_status.get("convergence_status", "unknown")})',
                    'new_params': optimized_params,
                    'expected_improvement': '継続的パフォーマンス最適化',
                    'confidence': 0.9,
                    'dynamic_optimized': True,
                    'convergence_status': strategy_status.get('convergence_status', 'unknown'),
                    'adaptation_rate': strategy_status.get('adaptation_rate', 0.1)
                })
            
            # 収束状態に基づく追加提案
            strategy_status = optimization_status.get('strategies', {}).get(strategy_name, {})
            convergence_status = strategy_status.get('convergence_status', 'unknown')
            
            if convergence_status == 'diverging':
                proposals.append({
                    'type': 'dynamic_stabilization',
                    'description': f'{strategy_name}の発散検出 - 安定化モードに切り替え',
                    'new_params': {**current_params, 'optimization_mode': 'conservative'},
                    'expected_improvement': 'パフォーマンス安定化',
                    'confidence': 0.8,
                    'stabilization': True
                })
            elif convergence_status == 'converging':
                proposals.append({
                    'type': 'dynamic_acceleration',
                    'description': f'{strategy_name}の収束検出 - 探索モードに切り替え',
                    'new_params': {**current_params, 'optimization_mode': 'aggressive'},
                    'expected_improvement': '新しい最適解の探索',
                    'confidence': 0.7,
                    'acceleration': True
                })
            
        except Exception as e:
            logger.warning(f"動的最適化提案の生成エラー: {e}")
        
        return proposals
    
    def update_dynamic_optimization(self, strategy_name: str, params: Dict[str, Any], metrics: Dict[str, float]):
        """動的最適化システムにパフォーマンスデータを送信"""
        try:
            # 戦略の最適化を初期化（まだの場合）
            optimization_status = dynamic_optimizer.get_optimization_status()
            if strategy_name not in optimization_status.get('strategies', {}):
                dynamic_optimizer.initialize_strategy_optimization(strategy_name, params)
            
            # パフォーマンスデータを更新
            dynamic_optimizer.update_performance(strategy_name, metrics)
            
            # 改善履歴にもパフォーマンスを追跡
            improvement_history.track_performance(strategy_name, metrics)
            
            logger.info(f"動的最適化システムを更新: {strategy_name}")
        except Exception as e:
            logger.error(f"動的最適化更新エラー: {e}")
    
    def get_optimization_insights(self, strategy_name: str) -> Dict[str, Any]:
        """最適化に関するインサイトを取得"""
        insights = {
            'dynamic_optimization': {},
            'performance_trends': {},
            'recommendations': []
        }
        
        try:
            # 動的最適化の状況
            optimization_status = dynamic_optimizer.get_optimization_status()
            if strategy_name in optimization_status.get('strategies', {}):
                insights['dynamic_optimization'] = optimization_status['strategies'][strategy_name]
            
            # パフォーマンストレンド
            performance_stats = improvement_history.get_performance_statistics(strategy_name)
            insights['performance_trends'] = performance_stats
            
            # 推奨事項
            convergence_status = insights['dynamic_optimization'].get('convergence_status', 'unknown')
            
            if convergence_status == 'diverging':
                insights['recommendations'].append({
                    'type': 'stability',
                    'message': 'パフォーマンスが不安定です。より保守的な設定を検討してください。',
                    'priority': 'high'
                })
            elif convergence_status == 'converging':
                insights['recommendations'].append({
                    'type': 'exploration',
                    'message': 'パフォーマンスが安定しています。新しい最適解の探索を検討してください。',
                    'priority': 'medium'
                })
            
            # パフォーマンストレンドに基づく推奨
            for metric, stats in performance_stats.items():
                if stats.get('trend') == 'declining':
                    insights['recommendations'].append({
                        'type': 'performance_decline',
                        'message': f'{metric}が低下傾向にあります。パラメータ調整が必要です。',
                        'priority': 'high'
                    })
        
        except Exception as e:
            logger.error(f"最適化インサイト取得エラー: {e}")
        
        return insights
    
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
