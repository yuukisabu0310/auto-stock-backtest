"""
動的パラメータ最適化システム
リアルタイムでのパラメータ調整と適応的最適化を提供
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd

from src.config import config
from src.logger import get_logger
from src.improvement_history import improvement_history

logger = get_logger("dynamic_optimizer")

@dataclass
class OptimizationState:
    """最適化状態を表すデータクラス"""
    strategy_name: str
    current_params: Dict[str, Any]
    performance_history: List[Dict[str, float]]
    optimization_mode: str  # "conservative", "aggressive", "adaptive"
    last_update: str
    convergence_status: str  # "converging", "diverging", "stable"
    adaptation_rate: float

class DynamicParameterOptimizer:
    """動的パラメータ最適化クラス"""
    
    def __init__(self):
        self.config = config.get_backtest_config()
        self.optimization_config = self.config.get('dynamic_optimization', {})
        self.state_file = Path("data/optimization_states.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 最適化状態
        self.optimization_states: Dict[str, OptimizationState] = {}
        
        # 設定パラメータ
        self.adaptation_rate_base = self.optimization_config.get('adaptation_rate', 0.1)
        self.performance_window = self.optimization_config.get('performance_window', 20)
        self.convergence_threshold = self.optimization_config.get('convergence_threshold', 0.02)
        self.min_samples_for_optimization = self.optimization_config.get('min_samples', 10)
        
        self.load_optimization_states()
    
    def load_optimization_states(self):
        """最適化状態を読み込み"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.optimization_states = {
                        name: OptimizationState(**state_data)
                        for name, state_data in data.items()
                    }
                logger.info(f"最適化状態を読み込み: {len(self.optimization_states)}戦略")
            except Exception as e:
                logger.error(f"最適化状態の読み込みエラー: {e}")
                self.optimization_states = {}
        else:
            self.optimization_states = {}
    
    def save_optimization_states(self):
        """最適化状態を保存"""
        try:
            data = {
                name: asdict(state)
                for name, state in self.optimization_states.items()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.info("最適化状態を保存")
        except Exception as e:
            logger.error(f"最適化状態の保存エラー: {e}")
    
    def initialize_strategy_optimization(self, strategy_name: str, initial_params: Dict[str, Any]):
        """戦略の最適化を初期化"""
        state = OptimizationState(
            strategy_name=strategy_name,
            current_params=initial_params,
            performance_history=[],
            optimization_mode="adaptive",
            last_update=datetime.now().isoformat(),
            convergence_status="stable",
            adaptation_rate=self.adaptation_rate_base
        )
        
        self.optimization_states[strategy_name] = state
        self.save_optimization_states()
        logger.info(f"戦略最適化を初期化: {strategy_name}")
    
    def update_performance(self, strategy_name: str, metrics: Dict[str, float]):
        """パフォーマンスデータを更新"""
        if strategy_name not in self.optimization_states:
            logger.warning(f"最適化状態が見つかりません: {strategy_name}")
            return
        
        state = self.optimization_states[strategy_name]
        
        # パフォーマンス履歴に追加
        performance_entry = {
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
        state.performance_history.append(performance_entry)
        
        # 履歴を制限
        state.performance_history = state.performance_history[-self.performance_window:]
        
        # 収束状態を更新
        state.convergence_status = self._analyze_convergence(state)
        
        # 適応率を調整
        state.adaptation_rate = self._calculate_adaptation_rate(state)
        
        state.last_update = datetime.now().isoformat()
        
        self.save_optimization_states()
        logger.info(f"パフォーマンス更新: {strategy_name}, 収束状態: {state.convergence_status}")
    
    def optimize_parameters(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """パラメータを動的最適化"""
        if strategy_name not in self.optimization_states:
            logger.warning(f"最適化状態が見つかりません: {strategy_name}")
            return None
        
        state = self.optimization_states[strategy_name]
        
        # 十分なデータがない場合は最適化しない
        if len(state.performance_history) < self.min_samples_for_optimization:
            logger.info(f"最適化に十分なデータがありません: {strategy_name}")
            return None
        
        # 最適化手法を選択
        optimization_method = self._select_optimization_method(state)
        
        if optimization_method == "gradient_based":
            new_params = self._gradient_based_optimization(state)
        elif optimization_method == "bayesian":
            new_params = self._bayesian_optimization(state)
        elif optimization_method == "evolutionary":
            new_params = self._evolutionary_optimization(state)
        else:
            new_params = self._random_search_optimization(state)
        
        if new_params and new_params != state.current_params:
            # パラメータを更新
            old_params = state.current_params.copy()
            state.current_params = new_params
            state.last_update = datetime.now().isoformat()
            
            self.save_optimization_states()
            
            logger.info(f"パラメータ最適化完了: {strategy_name}")
            logger.info(f"旧パラメータ: {old_params}")
            logger.info(f"新パラメータ: {new_params}")
            
            return new_params
        
        return None
    
    def _analyze_convergence(self, state: OptimizationState) -> str:
        """収束状態を分析"""
        if len(state.performance_history) < 5:
            return "insufficient_data"
        
        # 最近のシャープレシオの変動を分析
        recent_sharpe = [
            h.get('sharpe_ratio', 0) 
            for h in state.performance_history[-10:]
            if 'sharpe_ratio' in h
        ]
        
        if len(recent_sharpe) < 3:
            return "insufficient_data"
        
        # 変動を計算
        volatility = np.std(recent_sharpe)
        
        if volatility < self.convergence_threshold:
            return "converging"
        elif volatility > self.convergence_threshold * 3:
            return "diverging"
        else:
            return "stable"
    
    def _calculate_adaptation_rate(self, state: OptimizationState) -> float:
        """適応率を計算"""
        base_rate = self.adaptation_rate_base
        
        # 収束状態に基づいて調整
        if state.convergence_status == "converging":
            # 収束している場合は小さな変更
            return base_rate * 0.5
        elif state.convergence_status == "diverging":
            # 発散している場合は大きな変更
            return base_rate * 2.0
        else:
            # 安定している場合は通常の変更
            return base_rate
    
    def _select_optimization_method(self, state: OptimizationState) -> str:
        """最適化手法を選択"""
        history_length = len(state.performance_history)
        
        if history_length >= 50:
            # 十分なデータがある場合は高度な手法
            if state.convergence_status == "converging":
                return "gradient_based"
            elif state.convergence_status == "diverging":
                return "evolutionary"
            else:
                return "bayesian"
        elif history_length >= 20:
            # 中程度のデータがある場合
            return "bayesian"
        else:
            # データが少ない場合
            return "random_search"
    
    def _gradient_based_optimization(self, state: OptimizationState) -> Dict[str, Any]:
        """勾配ベース最適化"""
        current_params = state.current_params.copy()
        new_params = current_params.copy()
        
        # 最近のパフォーマンスから勾配を推定
        recent_performance = state.performance_history[-5:]
        target_metric = 'sharpe_ratio'
        
        # パラメータごとに勾配を推定して調整
        for param_name, param_value in current_params.items():
            if isinstance(param_value, list) and len(param_value) > 0:
                # リストパラメータの場合、最初の値を調整
                current_val = param_value[0]
                if isinstance(current_val, (int, float)):
                    # 簡単な数値微分による勾配推定
                    gradient = self._estimate_gradient(state, param_name, target_metric)
                    
                    # 勾配に基づく更新
                    step_size = state.adaptation_rate * abs(current_val) * 0.1
                    new_val = current_val + gradient * step_size
                    
                    # 範囲制限
                    new_val = max(1, min(new_val, current_val * 2))
                    new_params[param_name] = [int(new_val) if isinstance(current_val, int) else new_val]
        
        return new_params
    
    def _bayesian_optimization(self, state: OptimizationState) -> Dict[str, Any]:
        """ベイジアン最適化（簡易版）"""
        current_params = state.current_params.copy()
        new_params = current_params.copy()
        
        # 探索vs活用のバランスを取った調整
        exploration_factor = 0.3 if state.convergence_status == "converging" else 0.7
        
        for param_name, param_value in current_params.items():
            if isinstance(param_value, list) and len(param_value) > 0:
                current_val = param_value[0]
                if isinstance(current_val, (int, float)):
                    # 不確実性を考慮した探索
                    uncertainty = self._estimate_uncertainty(state, param_name)
                    
                    # 探索と活用のバランス
                    if np.random.random() < exploration_factor:
                        # 探索：不確実性の高い領域を探索
                        noise = np.random.normal(0, uncertainty * current_val * 0.2)
                    else:
                        # 活用：既知の良い方向に調整
                        gradient = self._estimate_gradient(state, param_name, 'sharpe_ratio')
                        noise = gradient * state.adaptation_rate * current_val * 0.1
                    
                    new_val = current_val + noise
                    new_val = max(1, min(new_val, current_val * 1.5))
                    new_params[param_name] = [int(new_val) if isinstance(current_val, int) else new_val]
        
        return new_params
    
    def _evolutionary_optimization(self, state: OptimizationState) -> Dict[str, Any]:
        """進化的最適化"""
        current_params = state.current_params.copy()
        
        # 複数の候補を生成
        candidates = []
        for _ in range(5):
            candidate = current_params.copy()
            
            for param_name, param_value in current_params.items():
                if isinstance(param_value, list) and len(param_value) > 0:
                    current_val = param_value[0]
                    if isinstance(current_val, (int, float)):
                        # 変異
                        mutation_rate = state.adaptation_rate
                        if np.random.random() < mutation_rate:
                            noise = np.random.normal(0, current_val * 0.3)
                            new_val = current_val + noise
                            new_val = max(1, min(new_val, current_val * 2))
                            candidate[param_name] = [int(new_val) if isinstance(current_val, int) else new_val]
            
            candidates.append(candidate)
        
        # 最も有望な候補を選択（ここでは単純にランダム選択）
        return np.random.choice(candidates)
    
    def _random_search_optimization(self, state: OptimizationState) -> Dict[str, Any]:
        """ランダム探索最適化"""
        current_params = state.current_params.copy()
        new_params = current_params.copy()
        
        # ランダムに一部のパラメータを調整
        for param_name, param_value in current_params.items():
            if isinstance(param_value, list) and len(param_value) > 0:
                current_val = param_value[0]
                if isinstance(current_val, (int, float)) and np.random.random() < 0.3:
                    # 30%の確率でパラメータを調整
                    noise_scale = state.adaptation_rate * current_val * 0.2
                    noise = np.random.normal(0, noise_scale)
                    new_val = current_val + noise
                    new_val = max(1, min(new_val, current_val * 1.5))
                    new_params[param_name] = [int(new_val) if isinstance(current_val, int) else new_val]
        
        return new_params
    
    def _estimate_gradient(self, state: OptimizationState, param_name: str, target_metric: str) -> float:
        """パラメータに対する勾配を推定"""
        # 履歴データから勾配を推定（簡易版）
        if len(state.performance_history) < 3:
            return 0.0
        
        # 最近の3つのデータポイントから線形回帰
        recent_data = state.performance_history[-3:]
        
        # 時間に対するメトリクスの変化率を計算
        metrics = [d.get(target_metric, 0) for d in recent_data]
        
        if len(metrics) >= 2:
            # 簡単な差分による勾配推定
            gradient = (metrics[-1] - metrics[0]) / len(metrics)
            return gradient
        
        return 0.0
    
    def _estimate_uncertainty(self, state: OptimizationState, param_name: str) -> float:
        """パラメータの不確実性を推定"""
        if len(state.performance_history) < 5:
            return 1.0  # 高い不確実性
        
        # 最近のパフォーマンスの変動を不確実性として使用
        recent_sharpe = [
            h.get('sharpe_ratio', 0)
            for h in state.performance_history[-10:]
            if 'sharpe_ratio' in h
        ]
        
        if len(recent_sharpe) >= 3:
            return np.std(recent_sharpe)
        
        return 1.0
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """最適化状況を取得"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'total_strategies': len(self.optimization_states),
            'strategies': {}
        }
        
        for name, state in self.optimization_states.items():
            status['strategies'][name] = {
                'convergence_status': state.convergence_status,
                'adaptation_rate': state.adaptation_rate,
                'performance_history_length': len(state.performance_history),
                'last_update': state.last_update,
                'optimization_mode': state.optimization_mode
            }
        
        return status
    
    def set_optimization_mode(self, strategy_name: str, mode: str):
        """最適化モードを設定"""
        if strategy_name in self.optimization_states:
            self.optimization_states[strategy_name].optimization_mode = mode
            self.save_optimization_states()
            logger.info(f"最適化モード変更: {strategy_name} -> {mode}")
    
    def reset_optimization(self, strategy_name: str):
        """最適化状態をリセット"""
        if strategy_name in self.optimization_states:
            state = self.optimization_states[strategy_name]
            state.performance_history = []
            state.convergence_status = "stable"
            state.adaptation_rate = self.adaptation_rate_base
            self.save_optimization_states()
            logger.info(f"最適化状態をリセット: {strategy_name}")

# グローバルインスタンス
dynamic_optimizer = DynamicParameterOptimizer()
