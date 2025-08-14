"""
拡張評価指標モジュール
包括的なパフォーマンス評価指標を提供します
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from src.config import config
from src.logger import get_logger

logger = get_logger("metrics")

class EnhancedMetrics:
    """拡張評価指標クラス"""
    
    def __init__(self):
        self.metrics_config = config.get_metrics_config()
        
    def calculate_all_metrics(self, equity_curve: pd.DataFrame, trades_df: pd.DataFrame = None) -> Dict[str, Any]:
        """全評価指標を計算"""
        metrics = {}
        
        # 基本指標
        basic_metrics = self._calculate_basic_metrics(equity_curve)
        metrics.update(basic_metrics)
        
        # 取引指標
        if trades_df is not None and not trades_df.empty:
            trading_metrics = self._calculate_trading_metrics(trades_df)
            metrics.update(trading_metrics)
            
        # リスク指標
        risk_metrics = self._calculate_risk_metrics(equity_curve)
        metrics.update(risk_metrics)
        
        # 安定性指標
        stability_metrics = self._calculate_stability_metrics(equity_curve)
        metrics.update(stability_metrics)
        
        return metrics
        
    def _calculate_basic_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """基本指標の計算"""
        if equity_curve.empty:
            return {}
            
        returns = equity_curve['Equity'].pct_change().dropna()
        
        # 総リターン
        total_return = (equity_curve['Equity'].iloc[-1] / equity_curve['Equity'].iloc[0]) - 1
        
        # 年率リターン
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        annualized_return = ((1 + total_return) ** (365 / days)) - 1 if days > 0 else 0
        
        # ボラティリティ
        volatility = returns.std() * np.sqrt(252)
        
        # シャープレシオ
        risk_free_rate = 0.02  # 2%をリスクフリーレートとして仮定
        excess_returns = returns - (risk_free_rate / 252)
        sharpe_ratio = (excess_returns.mean() * 252) / volatility if volatility > 0 else 0
        
        # ソルティノレシオ
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (excess_returns.mean() * 252) / downside_deviation if downside_deviation > 0 else 0
        
        # 最大ドローダウン
        max_drawdown = self._calculate_max_drawdown(equity_curve['Equity'])
        
        # カルマーレシオ
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio
        }
        
    def _calculate_trading_metrics(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        """取引指標の計算"""
        if trades_df.empty:
            return {}
            
        # 勝率
        winning_trades = trades_df[trades_df['PnL'] > 0]
        losing_trades = trades_df[trades_df['PnL'] < 0]
        
        total_trades = len(trades_df)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # 平均取引
        average_trade = trades_df['PnL'].mean()
        
        # 最大利益・損失
        largest_win = trades_df['PnL'].max() if len(winning_trades) > 0 else 0
        largest_loss = trades_df['PnL'].min() if len(losing_trades) > 0 else 0
        
        # 利益因子
        gross_profit = winning_trades['PnL'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['PnL'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # 連続勝敗
        consecutive_wins = self._calculate_consecutive_wins(trades_df)
        consecutive_losses = self._calculate_consecutive_losses(trades_df)
        
        return {
            'win_rate': win_rate,
            'average_trade': average_trade,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses
        }
        
    def _calculate_risk_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """リスク指標の計算"""
        if equity_curve.empty:
            return {}
            
        returns = equity_curve['Equity'].pct_change().dropna()
        
        # VaR (Value at Risk)
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        # CVaR (Conditional Value at Risk)
        cvar_95 = returns[returns <= var_95].mean()
        cvar_99 = returns[returns <= var_99].mean()
        
        # 下方偏差
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
        
        # 潰瘍指数
        ulcer_index = self._calculate_ulcer_index(equity_curve['Equity'])
        
        return {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'var_99': var_99,
            'cvar_99': cvar_99,
            'downside_deviation': downside_deviation,
            'ulcer_index': ulcer_index
        }
        
    def _calculate_stability_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """安定性指標の計算"""
        if equity_curve.empty:
            return {}
            
        returns = equity_curve['Equity'].pct_change().dropna()
        
        # ロールングパフォーマンス
        rolling_performance = self._calculate_rolling_performance(returns)
        
        # リターンの正規性
        normality_test = self._test_normality(returns)
        
        # 自己相関
        autocorrelation = self._calculate_autocorrelation(returns)
        
        return {
            'rolling_performance': rolling_performance,
            'normality_test': normality_test,
            'autocorrelation': autocorrelation
        }
        
    def _calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """最大ドローダウンの計算"""
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        return drawdown.min()
        
    def _calculate_consecutive_wins(self, trades_df: pd.DataFrame) -> int:
        """連続勝利回数の計算"""
        if trades_df.empty:
            return 0
            
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in trades_df['PnL']:
            if pnl > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def _calculate_consecutive_losses(self, trades_df: pd.DataFrame) -> int:
        """連続損失回数の計算"""
        if trades_df.empty:
            return 0
            
        max_consecutive = 0
        current_consecutive = 0
        
        for pnl in trades_df['PnL']:
            if pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def _calculate_ulcer_index(self, equity_series: pd.Series) -> float:
        """潰瘍指数の計算"""
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        squared_drawdown = drawdown ** 2
        return np.sqrt(squared_drawdown.mean())
        
    def _calculate_rolling_performance(self, returns: pd.Series, window: int = 252) -> float:
        """ロールングパフォーマンスの計算"""
        if len(returns) < window:
            return 0
            
        rolling_returns = returns.rolling(window=window).mean() * 252
        return rolling_returns.std()
        
    def _test_normality(self, returns: pd.Series) -> float:
        """正規性検定（Jarque-Bera検定）"""
        if len(returns) < 4:
            return 0
            
        try:
            _, p_value = stats.jarque_bera(returns)
            return p_value
        except:
            return 0
            
    def _calculate_autocorrelation(self, returns: pd.Series, lag: int = 1) -> float:
        """自己相関の計算"""
        if len(returns) < lag + 1:
            return 0
            
        try:
            return returns.autocorr(lag=lag)
        except:
            return 0
            
    def calculate_robust_score(self, metrics: Dict[str, float]) -> float:
        """ロバストスコアの計算（改善版）"""
        if not metrics:
            return -1e9
            
        # 基本スコア
        sharpe = metrics.get('sharpe_ratio', 0)
        sortino = metrics.get('sortino_ratio', 0)
        calmar = metrics.get('calmar_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        
        # 取引スコア
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        
        # リスクスコア
        var_95 = metrics.get('var_95', 0)
        ulcer_index = metrics.get('ulcer_index', 0)
        
        # 重み付けスコア計算
        score = (
            sharpe * 0.3 +                    # シャープレシオ
            sortino * 0.2 +                   # ソルティノレシオ
            calmar * 0.15 +                   # カルマーレシオ
            (win_rate - 0.5) * 0.1 +          # 勝率（50%を基準）
            min(profit_factor, 3.0) * 0.1 +   # 利益因子（3.0でキャップ）
            max_dd * 0.05 +                   # 最大ドローダウン（ペナルティ）
            max(var_95, -0.1) * 0.05 +        # VaR（ペナルティ）
            (1.0 - min(ulcer_index, 1.0)) * 0.05  # 潰瘍指数（ペナルティ）
        )
        
        return score
        
    def generate_metrics_report(self, metrics: Dict[str, float]) -> str:
        """評価指標レポートの生成"""
        if not metrics:
            return "評価指標が計算できませんでした。"
            
        report = []
        report.append("=== バックテスト評価指標レポート ===")
        report.append("")
        
        # 基本指標
        report.append("【基本指標】")
        if 'total_return' in metrics:
            report.append(f"総リターン: {metrics['total_return']:.2%}")
        if 'annualized_return' in metrics:
            report.append(f"年率リターン: {metrics['annualized_return']:.2%}")
        if 'volatility' in metrics:
            report.append(f"ボラティリティ: {metrics['volatility']:.2%}")
        if 'sharpe_ratio' in metrics:
            report.append(f"シャープレシオ: {metrics['sharpe_ratio']:.3f}")
        if 'sortino_ratio' in metrics:
            report.append(f"ソルティノレシオ: {metrics['sortino_ratio']:.3f}")
        if 'max_drawdown' in metrics:
            report.append(f"最大ドローダウン: {metrics['max_drawdown']:.2%}")
        if 'calmar_ratio' in metrics:
            report.append(f"カルマーレシオ: {metrics['calmar_ratio']:.3f}")
        report.append("")
        
        # 取引指標
        if any(key in metrics for key in ['win_rate', 'profit_factor']):
            report.append("【取引指標】")
            if 'win_rate' in metrics:
                report.append(f"勝率: {metrics['win_rate']:.2%}")
            if 'profit_factor' in metrics:
                report.append(f"利益因子: {metrics['profit_factor']:.3f}")
            if 'average_trade' in metrics:
                report.append(f"平均取引: {metrics['average_trade']:.2f}")
            report.append("")
            
        # リスク指標
        if any(key in metrics for key in ['var_95', 'ulcer_index']):
            report.append("【リスク指標】")
            if 'var_95' in metrics:
                report.append(f"VaR(95%): {metrics['var_95']:.2%}")
            if 'cvar_95' in metrics:
                report.append(f"CVaR(95%): {metrics['cvar_95']:.2%}")
            if 'ulcer_index' in metrics:
                report.append(f"潰瘍指数: {metrics['ulcer_index']:.3f}")
            report.append("")
            
        # 総合スコア
        robust_score = self.calculate_robust_score(metrics)
        report.append(f"【総合スコア】")
        report.append(f"ロバストスコア: {robust_score:.4f}")
        
        return "\n".join(report)

# グローバルインスタンス
enhanced_metrics = EnhancedMetrics()
