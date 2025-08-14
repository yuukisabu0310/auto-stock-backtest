"""
戦略ベースクラス
拡張可能な戦略システムの基盤を提供します
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from backtesting import Strategy
from backtesting.lib import crossover

from src.config import config
from src.logger import get_logger

logger = get_logger("strategy_base")

class BaseStrategy(Strategy, ABC):
    """戦略のベースクラス"""
    
    def __init__(self, *args, **kwargs):
        # backtesting.Strategy は (broker, data, params) を位置引数で受け取るため
        # 互換性確保のために *args, **kwargs をそのまま親へ渡す
        super().__init__(*args, **kwargs)
        self.risk_config = self._get_risk_config()
        self.position_size = 0
        self.stop_loss_price = None
        self.take_profit_price = None
        
    def _get_risk_config(self) -> Dict[str, Any]:
        """リスク管理設定を取得"""
        strategy_name = self.__class__.__name__
        return config.get_risk_management_config(strategy_name)
        
    def init(self):
        """戦略の初期化（サブクラスで実装）"""
        self._init_indicators()
        self._init_risk_management()
        
    @abstractmethod
    def _init_indicators(self):
        """テクニカル指標の初期化"""
        pass
        
    def _init_risk_management(self):
        """リスク管理の初期化"""
        # リスク管理パラメータ（常に初期化）
        self.max_position_size = self.risk_config.get('max_position_size', 0.1)
        self.max_drawdown_limit = self.risk_config.get('max_drawdown_limit', 0.2)
        self.stop_loss_pct = self.risk_config.get('stop_loss', 0.05)
        self.take_profit_pct = self.risk_config.get('take_profit', 0.15)
        
    def next(self):
        """次のバーでの処理"""
        # リスク管理チェック
        if self._should_close_position():
            self.position.close()
            return
            
        # 戦略ロジック実行
        self._execute_strategy()
        
        # リスク管理適用
        self._apply_risk_management()
        
    @abstractmethod
    def _execute_strategy(self):
        """戦略ロジックの実行（サブクラスで実装）"""
        pass
        
    def _should_close_position(self) -> bool:
        """ポジションを閉じるべきかチェック"""
        if not self.position.is_long:
            return False
            
        # リスク管理が無効の場合は早期リターン
        if not self.risk_config.get('enabled', False):
            return False
            
        # ドローダウン制限チェック
        if hasattr(self, 'max_drawdown_limit') and self.max_drawdown_limit:
            current_drawdown = self._calculate_drawdown()
            if current_drawdown > self.max_drawdown_limit:
                logger.debug(f"ドローダウン制限によりポジション閉鎖: {current_drawdown:.2%}")
                return True
                
        # ストップロスチェック
        if hasattr(self, 'stop_loss_price') and self.stop_loss_price and self.data.Close[-1] <= self.stop_loss_price:
            logger.debug(f"ストップロスによりポジション閉鎖: {self.data.Close[-1]:.2f}")
            return True
            
        # 利確チェック
        if hasattr(self, 'take_profit_price') and self.take_profit_price and self.data.Close[-1] >= self.take_profit_price:
            logger.debug(f"利確によりポジション閉鎖: {self.data.Close[-1]:.2f}")
            return True
            
        return False
        
    def _calculate_drawdown(self) -> float:
        """現在のドローダウンを計算"""
        if not hasattr(self, '_peak_equity'):
            self._peak_equity = self.equity
            
        self._peak_equity = max(self._peak_equity, self.equity)
        return (self._peak_equity - self.equity) / self._peak_equity
        
    def _apply_risk_management(self):
        """リスク管理の適用"""
        if not self.risk_config.get('enabled', False):
            return
            
        # ポジションサイズの制限
        if self.max_position_size:
            max_size = self.equity * self.max_position_size / self.data.Close[-1]
            if self.position.size > max_size:
                self.position.close()
                self.buy(size=max_size)
                
    def _calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """ポジションサイズの計算"""
        if not self.risk_config.get('enabled', False):
            return 0.1  # デフォルトで10%
            
        try:
            base_size = self.equity * self.max_position_size / self.data.Close[-1]
            size = base_size * signal_strength
            
            # backtestingの要件に合わせてsizeを調整
            if size > 0:
                # 資金の割合として使用（0 < size < 1）
                size = min(size, 0.95)  # 最大95%まで
                if size < 0.01:  # 1%未満は最小値に
                    size = 0.01
                return size
            else:
                return 0.1  # デフォルト値
        except (ZeroDivisionError, ValueError, TypeError):
            return 0.1  # エラー時はデフォルト値
        
    def _set_stop_loss(self, entry_price: float):
        """ストップロス価格を設定"""
        if self.stop_loss_pct:
            self.stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            
    def _set_take_profit(self, entry_price: float):
        """利確価格を設定"""
        if self.take_profit_pct:
            self.take_profit_price = entry_price * (1 + self.take_profit_pct)

    @staticmethod
    def _sma_indicator(series, period: int = 14) -> np.ndarray:
        """シンプルなSMA（NumPyベース）"""
        # backtestingの_Arrayオブジェクトをnumpy配列に変換
        if hasattr(series, 'to_numpy'):
            data = series.to_numpy()
        else:
            data = np.array(series)
        
        # 移動平均の計算
        result = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            result[i] = np.mean(data[i - period + 1:i + 1])
        
        # 前方埋め
        result = np.where(np.isnan(result), data, result)
        return result

    @staticmethod
    def _atr_indicator(high, low, close, period: int = 14) -> np.ndarray:
        """シンプルなATR（NumPyベース）"""
        # backtestingの_Arrayオブジェクトをnumpy配列に変換
        if hasattr(high, 'to_numpy'):
            high_data = high.to_numpy()
            low_data = low.to_numpy()
            close_data = close.to_numpy()
        else:
            high_data = np.array(high)
            low_data = np.array(low)
            close_data = np.array(close)
        
        # True Rangeの計算
        prev_close = np.roll(close_data, 1)
        prev_close[0] = close_data[0]  # 最初の値は同じにする
        
        tr1 = np.abs(high_data - low_data)
        tr2 = np.abs(high_data - prev_close)
        tr3 = np.abs(low_data - prev_close)
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # ATRの計算（移動平均）
        result = np.full_like(tr, np.nan)
        for i in range(period - 1, len(tr)):
            result[i] = np.mean(tr[i - period + 1:i + 1])
        
        # 前方埋め
        result = np.where(np.isnan(result), tr, result)
        return result

    @staticmethod
    def _rsi_indicator(series, period: int = 14) -> np.ndarray:
        """シンプルなRSI実装（NumPyベース）"""
        # backtestingの_Arrayオブジェクトをnumpy配列に変換
        if hasattr(series, 'to_numpy'):
            data = series.to_numpy()
        else:
            data = np.array(series)
        
        # 価格変化の計算
        diff = np.diff(data)
        diff = np.insert(diff, 0, 0)  # 最初の要素を0で埋める
        
        # 上昇・下降の分離
        up = np.where(diff > 0, diff, 0)
        down = np.where(diff < 0, -diff, 0)
        
        # 指数移動平均の計算
        alpha = 1.0 / period
        roll_up = np.zeros_like(up)
        roll_down = np.zeros_like(down)
        
        # 最初の値
        roll_up[0] = up[0]
        roll_down[0] = down[0]
        
        # 指数移動平均の計算
        for i in range(1, len(up)):
            roll_up[i] = alpha * up[i] + (1 - alpha) * roll_up[i-1]
            roll_down[i] = alpha * down[i] + (1 - alpha) * roll_down[i-1]
        
        # RSIの計算
        rs = np.where(roll_down != 0, roll_up / roll_down, 0)
        rsi = 100 - (100 / (1 + rs))
        
        # NaNの処理
        rsi = np.where(np.isnan(rsi), 50, rsi)
        return rsi

class FixedSmaStrategy(BaseStrategy):
    """固定SMA戦略"""
    
    # パラメータ
    n_fast = 10
    n_slow = 20
    
    def _init_indicators(self):
        """SMA指標の初期化"""
        close = self.data.Close
        self.sma_fast = self.I(self._sma_indicator, close, self.n_fast)
        self.sma_slow = self.I(self._sma_indicator, close, self.n_slow)
        
    def _execute_strategy(self):
        """SMAクロス戦略の実行"""
        if crossover(self.sma_fast, self.sma_slow):
            if not self.position.is_long:
                self.position.close()
                size = self._calculate_position_size()
                self.buy(size=size)
                self._set_stop_loss(self.data.Close[-1])
                self._set_take_profit(self.data.Close[-1])
                
        elif crossover(self.sma_slow, self.sma_fast):
            if self.position.is_long:
                self.position.close()
                self.stop_loss_price = None
                self.take_profit_price = None

class SmaCrossStrategy(BaseStrategy):
    """SMA + ATR リスク管理戦略"""
    
    # パラメータ
    n_fast = 20
    n_slow = 50
    target_vol_yr = 0.15
    risk_cap = 0.25
    atr_n = 14
    slip_k_atr = 0.05
    
    def _init_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        self.sma_fast = self.I(self._sma_indicator, close, self.n_fast)
        self.sma_slow = self.I(self._sma_indicator, close, self.n_slow)
        self.atr = self.I(self._atr_indicator, self.data.High, self.data.Low, close, self.atr_n)
        
    def _execute_strategy(self):
        """SMA + ATR戦略の実行"""
        atr_val = self.atr[-1]
        
        # ATR値の検証
        if not np.isfinite(atr_val) or atr_val <= 0:
            size = 0
        else:
            try:
                daily_vol = atr_val / self.data.Close[-1]
                if daily_vol and daily_vol > 0:
                    target_pos_vol = self.target_vol_yr / (daily_vol * (252 ** 0.5))
                    max_size = self.equity * self.risk_cap / self.data.Close[-1]
                    size = max(0, min(max_size, self.equity * target_pos_vol / self.data.Close[-1]))
                    
                    # backtestingの要件に合わせてsizeを調整
                    if size > 0:
                        # 資金の割合として使用（0 < size < 1）
                        size = min(size, 0.95)  # 最大95%まで
                        if size < 0.01:  # 1%未満は最小値に
                            size = 0.01
                else:
                    size = 0
            except (ZeroDivisionError, ValueError, TypeError):
                size = 0
                
        px = self.data.Close[-1] * (
            1 + self.slip_k_atr * (atr_val / self.data.Close[-1] if self.data.Close[-1] else 0)
        )
        
        if crossover(self.sma_fast, self.sma_slow):
            if not self.position.is_long and size > 0:
                self.position.close()
                self.buy(size=size, limit=px)
                self._set_stop_loss(self.data.Close[-1])
                self._set_take_profit(self.data.Close[-1])
                
        elif crossover(self.sma_slow, self.sma_fast):
            if self.position.is_long:
                self.position.close()
                self.stop_loss_price = None
                self.take_profit_price = None

class MomentumStrategy(BaseStrategy):
    """モメンタム戦略（RSIベース）"""
    
    # パラメータ
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    lookback_period = 20
    
    def _init_indicators(self):
        """RSI指標の初期化"""
        close = self.data.Close
        # backtesting.lib にはRSIがないため、簡易実装
        self.rsi = self.I(self._rsi_indicator, close, self.rsi_period)
        self.sma = self.I(self._sma_indicator, close, self.lookback_period)
        
    def _execute_strategy(self):
        """RSIモメンタム戦略の実行"""
        if len(self.rsi) < 2:
            return
            
        rsi_current = self.rsi[-1]
        rsi_prev = self.rsi[-2]
        price_current = self.data.Close[-1]
        sma_current = self.sma[-1]
        
        # 買いシグナル: RSIが30を上向きにクロス + 価格がSMA上
        if (rsi_prev <= self.rsi_oversold and rsi_current > self.rsi_oversold and 
            price_current > sma_current):
            if not self.position.is_long:
                self.position.close()
                size = self._calculate_position_size()
                self.buy(size=size)
                self._set_stop_loss(self.data.Close[-1])
                self._set_take_profit(self.data.Close[-1])
                
        # 売りシグナル: RSIが70を下向きにクロス + 価格がSMA下
        elif (rsi_prev >= self.rsi_overbought and rsi_current < self.rsi_overbought and 
              price_current < sma_current):
            if self.position.is_long:
                self.position.close()
                self.stop_loss_price = None
                self.take_profit_price = None

class StrategyFactory:
    """戦略ファクトリークラス"""
    
    _strategies = {
        'FixedSma': FixedSmaStrategy,
        'SmaCross': SmaCrossStrategy,
        'Momentum': MomentumStrategy
    }
    
    @classmethod
    def get_strategy(cls, strategy_name: str) -> type:
        """戦略クラスを取得"""
        if strategy_name not in cls._strategies:
            raise ValueError(f"未知の戦略: {strategy_name}")
        return cls._strategies[strategy_name]
        
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """新しい戦略を登録"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"戦略クラスはBaseStrategyを継承する必要があります: {strategy_class}")
        cls._strategies[name] = strategy_class
        logger.info(f"戦略登録: {name}")
        
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """利用可能な戦略のリストを取得"""
        return list(cls._strategies.keys())
        
    @classmethod
    def create_strategy(cls, strategy_name: str, **params) -> BaseStrategy:
        """戦略インスタンスを作成"""
        strategy_class = cls.get_strategy(strategy_name)
        return strategy_class(**params)

# 戦略の自動登録
def register_builtin_strategies():
    """組み込み戦略を登録"""
    StrategyFactory.register_strategy('FixedSma', FixedSmaStrategy)
    StrategyFactory.register_strategy('SmaCross', SmaCrossStrategy)
    StrategyFactory.register_strategy('Momentum', MomentumStrategy)

# 初期化時に組み込み戦略を登録
register_builtin_strategies()
