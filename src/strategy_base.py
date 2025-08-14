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

from src.config import ConfigManager
from src.logger import get_logger

logger = get_logger("strategy_base")

class BaseStrategy(Strategy, ABC):
    """戦略のベースクラス"""
    
    def __init__(self, *args, **kwargs):
        """初期化"""
        # backtestingライブラリの要件に準拠
        super().__init__(*args, **kwargs)
        
        # 基本属性の初期化
        self.stop_loss_price = None
        self.take_profit_price = None
        self.trailing_stop = None
        self.max_position_size = 0.95
        self.max_drawdown_limit = 0.25
        
        # リスク管理の初期化
        self._init_risk_management()
        
        # 指標の初期化（データが利用可能な場合のみ）
        if hasattr(self, 'data') and len(self.data) > 0:
            try:
                self._init_indicators()
            except Exception as e:
                # 指標初期化エラーは無視
                pass
        
    def _get_risk_config(self) -> Dict[str, Any]:
        """リスク設定を取得"""
        try:
            # 設定ファイルから読み込み
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # 戦略名を取得
            strategy_name = self.__class__.__name__.replace('Strategy', '')
            
            # 戦略固有のリスク設定を取得
            strategy_config = config.get('strategies', {}).get(strategy_name, {})
            risk_config = strategy_config.get('risk_management', {})
            
            return risk_config
            
        except Exception as e:
            # エラーの場合はデフォルト設定を返す
            return {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.10,
                'max_position_size': 0.1,
                'max_drawdown_limit': 0.25
            }
        
    def init(self):
        """戦略の初期化（サブクラスで実装）"""
        self._init_indicators()
        self._init_risk_management()
        
    def _init_indicators(self):
        """指標の初期化（オーバーライド用）"""
        # データサイズの検証
        if len(self.data) < 50:  # 最小データサイズ
            return
            
        # 基本指標の初期化
        self._init_basic_indicators()
        
    def _init_basic_indicators(self):
        """基本指標の初期化"""
        # データサイズの再確認
        if len(self.data) < 20:
            return
            
        try:
            # 基本データの取得
            close = self.data.Close
            high = self.data.High
            low = self.data.Low
            volume = self.data.Volume
            
            # データの妥当性チェック
            if not all(len(arr) == len(close) for arr in [high, low, volume]):
                return
                
            # 指標の初期化（エラーハンドリング付き）
            self._init_strategy_specific_indicators()
            
        except Exception as e:
            # 指標初期化エラーの場合は何もしない
            pass
        
    @abstractmethod
    def _init_strategy_specific_indicators(self):
        """戦略固有の指標の初期化"""
        pass
        
    def _safe_indicator_init(self, indicator_func, *args, **kwargs):
        """安全な指標初期化"""
        try:
            # データサイズの厳密なチェック
            if len(self.data) < 50:  # 最小データサイズを増加
                return None
                
            # 引数の妥当性チェック
            if not args or len(args) == 0:
                return None
                
            # 最初の引数（通常は価格データ）のチェック
            price_data = args[0]
            if len(price_data) < 20:
                return None
                
            # 指標の計算
            result = self.I(indicator_func, *args, **kwargs)
            
            # 結果の妥当性チェック
            if result is None or len(result) == 0:
                return None
                
            return result
            
        except Exception as e:
            # 指標初期化エラーの場合はNoneを返す
            return None
        
    def _init_risk_management(self):
        """リスク管理の初期化"""
        try:
            # リスク設定を取得
            self.risk_config = self._get_risk_config()
            
            # リスク管理パラメータの初期化
            self.stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.05)
            self.take_profit_pct = self.risk_config.get('take_profit_pct', 0.10)
            self.max_position_size = self.risk_config.get('max_position_size', 0.1)
            self.max_drawdown_limit = self.risk_config.get('max_drawdown_limit', 0.25)
            
        except Exception as e:
            # エラーの場合はデフォルト値を使用
            self.stop_loss_pct = 0.05
            self.take_profit_pct = 0.10
            self.max_position_size = 0.1
            self.max_drawdown_limit = 0.25
        
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

    @staticmethod
    def _macd_indicator(series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD指標の計算"""
        if hasattr(series, 'to_numpy'):
            data = series.to_numpy()
        else:
            data = np.array(series)
        
        # EMAの計算
        def ema(data, period):
            alpha = 2.0 / (period + 1)
            result = np.zeros_like(data)
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result
        
        # MACDライン
        ema_fast = ema(data, fast)
        ema_slow = ema(data, slow)
        macd_line = ema_fast - ema_slow
        
        # シグナルライン
        signal_line = ema(macd_line, signal)
        
        # ヒストグラム
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram

    @staticmethod
    def _bollinger_bands(series, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """ボリンジャーバンドの計算"""
        if hasattr(series, 'to_numpy'):
            data = series.to_numpy()
        else:
            data = np.array(series)
        
        # SMA計算
        sma = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            sma[i] = np.mean(data[i - period + 1:i + 1])
        
        # 標準偏差計算
        std = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            std[i] = np.std(data[i - period + 1:i + 1])
        
        # バンド計算
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band

    @staticmethod
    def _keltner_channels(high, low, close, period: int = 20, multiplier: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """ケルトナーチャネルの計算"""
        if hasattr(high, 'to_numpy'):
            high_data = high.to_numpy()
            low_data = low.to_numpy()
            close_data = close.to_numpy()
        else:
            high_data = np.array(high)
            low_data = np.array(low)
            close_data = np.array(close)
        
        # 真のレンジ計算
        prev_close = np.roll(close_data, 1)
        prev_close[0] = close_data[0]
        
        tr1 = high_data - low_data
        tr2 = np.abs(high_data - prev_close)
        tr3 = np.abs(low_data - prev_close)
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # ATR計算
        atr = np.full_like(tr, np.nan)
        for i in range(period - 1, len(tr)):
            atr[i] = np.mean(tr[i - period + 1:i + 1])
        
        # 中心線（EMA）
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(close_data)
        ema[0] = close_data[0]
        for i in range(1, len(close_data)):
            ema[i] = alpha * close_data[i] + (1 - alpha) * ema[i-1]
        
        # チャネル計算
        upper_channel = ema + (multiplier * atr)
        lower_channel = ema - (multiplier * atr)
        
        return upper_channel, ema, lower_channel

    @staticmethod
    def _adx_indicator(high, low, close, period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """ADX指標の計算"""
        if hasattr(high, 'to_numpy'):
            high_data = high.to_numpy()
            low_data = low.to_numpy()
            close_data = close.to_numpy()
        else:
            high_data = np.array(high)
            low_data = np.array(low)
            close_data = np.array(close)
        
        # 真のレンジ計算
        prev_close = np.roll(close_data, 1)
        prev_close[0] = close_data[0]
        
        tr1 = high_data - low_data
        tr2 = np.abs(high_data - prev_close)
        tr3 = np.abs(low_data - prev_close)
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # 方向性移動計算
        up_move = high_data - np.roll(high_data, 1)
        down_move = np.roll(low_data, 1) - low_data
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 平滑化
        alpha = 1.0 / period
        tr_smooth = np.zeros_like(tr)
        plus_dm_smooth = np.zeros_like(plus_dm)
        minus_dm_smooth = np.zeros_like(minus_dm)
        
        tr_smooth[0] = tr[0]
        plus_dm_smooth[0] = plus_dm[0]
        minus_dm_smooth[0] = minus_dm[0]
        
        for i in range(1, len(tr)):
            tr_smooth[i] = alpha * tr[i] + (1 - alpha) * tr_smooth[i-1]
            plus_dm_smooth[i] = alpha * plus_dm[i] + (1 - alpha) * plus_dm_smooth[i-1]
            minus_dm_smooth[i] = alpha * minus_dm[i] + (1 - alpha) * minus_dm_smooth[i-1]
        
        # DI計算
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # DX計算
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        dx = np.where(np.isnan(dx), 0, dx)
        
        # ADX計算
        adx = np.zeros_like(dx)
        adx[0] = dx[0]
        for i in range(1, len(dx)):
            adx[i] = alpha * dx[i] + (1 - alpha) * adx[i-1]
        
        return adx, plus_di, minus_di

    @staticmethod
    def _obv_indicator(close, volume) -> np.ndarray:
        """OBV（On Balance Volume）の計算"""
        if hasattr(close, 'to_numpy'):
            close_data = close.to_numpy()
            volume_data = volume.to_numpy()
        else:
            close_data = np.array(close)
            volume_data = np.array(volume)
        
        obv = np.zeros_like(close_data)
        obv[0] = volume_data[0]
        
        for i in range(1, len(close_data)):
            if close_data[i] > close_data[i-1]:
                obv[i] = obv[i-1] + volume_data[i]
            elif close_data[i] < close_data[i-1]:
                obv[i] = obv[i-1] - volume_data[i]
            else:
                obv[i] = obv[i-1]
        
        return obv

    def _apply_common_filters(self):
        """共通フィルタの適用"""
        # 一時的に無効化してシンプルな戦略に集中
        return True
        
        # 元の実装（後で有効化）
        """
        # 流動性フィルタ
        if not self._check_liquidity():
            return False
            
        # 市場レジームフィルタ
        if not self._check_market_regime():
            return False
            
        # ボラティリティフィルタ
        if not self._check_volatility():
            return False
            
        return True
        """

    def _calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """ポジションサイズの計算（リスクベース）"""
        if not self.risk_config.get('enabled', False):
            return 0.1  # デフォルトで10%
        
        try:
            # ATRベースのリスク計算
            atr_14 = self.I(self._atr_indicator, self.data.High, self.data.Low, self.data.Close, 14)
            current_atr = atr_14[-1]
            
            if current_atr <= 0:
                return 0.1
            
            # リスク設定
            risk_per_trade = self.equity * 0.01  # 1%リスク
            stop_distance = current_atr * 2  # 2*ATRでストップ
            
            # ポジションサイズ計算
            position_size = risk_per_trade / stop_distance
            
            # 最大ポジションサイズ制限
            max_size = self.equity * self.max_position_size / self.data.Close[-1]
            position_size = min(position_size, max_size)
            
            # 最小・最大制限
            position_size = max(0.01, min(position_size, 0.95))
            
            return position_size * signal_strength
            
        except (ZeroDivisionError, ValueError, TypeError):
            return 0.1

    def _set_stop_loss(self, entry_price: float):
        """ストップロス価格を設定"""
        if self.stop_loss_pct:
            self.stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            
    def _set_take_profit(self, entry_price: float):
        """利確価格を設定"""
        if self.take_profit_pct:
            self.take_profit_price = entry_price * (1 + self.take_profit_pct)

    def _set_trailing_stop(self, entry_price: float, atr_multiplier: float = 1.5):
        """トレーリングストップの設定"""
        try:
            atr_14 = self.I(self._atr_indicator, self.data.High, self.data.Low, self.data.Close, 14)
            current_atr = atr_14[-1]
            
            if current_atr > 0:
                self.trailing_stop = entry_price - (atr_multiplier * current_atr)
            else:
                self.trailing_stop = entry_price * 0.95  # 5%ストップ
                
        except Exception as e:
            logger.error(f"トレーリングストップ設定エラー: {e}")
            self.trailing_stop = entry_price * 0.95

    def _update_trailing_stop(self, current_price: float):
        """トレーリングストップの更新"""
        if hasattr(self, 'trailing_stop') and self.trailing_stop:
            try:
                atr_14 = self.I(self._atr_indicator, self.data.High, self.data.Low, self.data.Close, 14)
                current_atr = atr_14[-1]
                
                new_stop = current_price - (1.5 * current_atr)
                if new_stop > self.trailing_stop:
                    self.trailing_stop = new_stop
                    
            except Exception as e:
                logger.error(f"トレーリングストップ更新エラー: {e}")

    def _check_trailing_stop(self) -> bool:
        """トレーリングストップチェック"""
        if hasattr(self, 'trailing_stop') and self.trailing_stop:
            return self.data.Close[-1] <= self.trailing_stop
        return False

class FixedSmaStrategy(BaseStrategy):
    """固定SMA戦略"""
    
    # パラメータ（backtesting用）
    n_fast = 20
    n_slow = 20
    sma_period = 20  # 実際に使用するパラメータ
    
    def _init_strategy_specific_indicators(self):
        """SMA指標の初期化"""
        try:
            # データサイズの検証
            if len(self.data) < self.sma_period + 10:
                return
                
            # シンプルなSMA計算
            close = self.data.Close
            if len(close) < self.sma_period:
                return
                
            self.sma = self.I(self._calculate_sma, close, self.sma_period)
        except Exception as e:
            # 指標初期化エラーは無視
            pass
        
    def _calculate_sma(self, prices, period):
        """シンプルなSMA計算"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
            
        sma = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])
        return sma
        
    def _execute_strategy(self):
        """固定SMA戦略の実行"""
        try:
            # 指標が初期化されていない場合は何もしない
            if not hasattr(self, 'sma') or self.sma is None:
                return
                
            # データサイズの再確認
            if len(self.data) < 2:
                return
                
            current_price = self.data.Close[-1]
            current_sma = self.sma[-1]
            prev_price = self.data.Close[-2]
            prev_sma = self.sma[-2]
            
            # NaNチェック
            if np.isnan(current_sma) or np.isnan(prev_sma):
                return
            
            # ロングポジションがない場合
            if not self.position.is_long:
                # 価格がSMAを上向きにクロス
                if current_price > current_sma and prev_price <= prev_sma:
                    size = self._calculate_position_size()
                    if size > 0:
                        self.buy(size=size)
                        self._set_stop_loss(current_price)
                        self._set_take_profit(current_price)
                    
            # ロングポジションがある場合
            elif self.position.is_long:
                # 価格がSMAを下向きにクロス
                if current_price < current_sma and prev_price >= prev_sma:
                    self.position.close()
                    self.stop_loss_price = None
                    self.take_profit_price = None
                    
        except Exception as e:
            # 戦略実行エラーは無視
            pass

class SmaCrossStrategy(BaseStrategy):
    """SMA + ATR リスク管理戦略"""
    
    # パラメータ
    n_fast = 20
    n_slow = 50
    target_vol_yr = 0.15
    risk_cap = 0.25
    atr_n = 14
    slip_k_atr = 0.05
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        # データサイズの検証
        if len(self.data) < max(self.n_fast, self.n_slow, self.atr_n) + 10:
            return
            
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
    
    def _init_strategy_specific_indicators(self):
        """RSI指標の初期化"""
        close = self.data.Close
        self.rsi = self.I(self._rsi_indicator, close, self.rsi_period) # カスタムRSI関数を使用
        self.sma = self.I(self._sma_indicator, close, self.lookback_period) # backtesting.test.SMAを使用
        
    def _execute_strategy(self):
        """モメンタム戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        rsi_current = self.rsi[-1]
        rsi_prev = self.rsi[-2]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # RSIオーバーソールドからの反転
            if (rsi_prev <= self.rsi_oversold and rsi_current > self.rsi_oversold and
                current_price > self.sma[-1]):
                
                size = self._calculate_position_size()
                self.buy(size=size)
                self._set_stop_loss(current_price)
                self._set_take_profit(current_price)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # RSIオーバーブoughtで利確
            if (rsi_prev >= self.rsi_overbought and rsi_current < self.rsi_overbought and
                current_price < self.sma[-1]):
                self.position.close()
                self.stop_loss_price = None
                self.take_profit_price = None

class MovingAverageBreakoutStrategy(BaseStrategy):
    """移動平均ブレイク戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 20  # backtesting用
    n_slow = 50  # backtesting用
    sma_short = 20
    sma_medium = 50
    sma_long = 200
    atr_period = 14
    volume_multiplier = 1.5
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        volume = self.data.Volume
        
        self.sma_20 = self.I(self._sma_indicator, close, self.sma_short)
        self.sma_50 = self.I(self._sma_indicator, close, self.sma_medium)
        self.sma_200 = self.I(self._sma_indicator, close, self.sma_long)
        self.atr = self.I(self._atr_indicator, self.data.High, self.data.Low, close, self.atr_period)
        self.volume_sma = self.I(self._sma_indicator, volume, 20)
        
    def _execute_strategy(self):
        """移動平均ブレイク戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # 20日高値の計算
        high_20 = max(self.data.High[-20:])
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # ブレイクアウト条件
            breakout_condition = (
                current_price > self.sma_50[-1] and
                self.sma_50[-1] > self.sma_200[-1] and
                current_price > high_20 + 0.2 * self.atr[-1] and
                current_volume > self.volume_sma[-1] * self.volume_multiplier
            )
            
            if breakout_condition:
                size = self._calculate_position_size()
                self.buy(size=size)
                self._set_trailing_stop(current_price, 1.5)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # イグジット条件
            exit_condition = (
                current_price < self.sma_20[-1] or
                self._check_trailing_stop()
            )
            
            if exit_condition:
                self.position.close()
                self.trailing_stop = None
            else:
                # トレーリングストップ更新
                self._update_trailing_stop(current_price)

class DonchianChannelStrategy(BaseStrategy):
    """ドンチャンチャネル戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 55  # backtesting用
    n_slow = 20  # backtesting用
    channel_period = 55
    stop_period = 20
    atr_multiplier = 2.0
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # ドンチャンチャネル計算
        self.upper_channel = self.I(self._donchian_upper, high, self.channel_period)
        self.lower_channel = self.I(self._donchian_lower, low, self.channel_period)
        self.stop_upper = self.I(self._donchian_upper, high, self.stop_period)
        self.stop_lower = self.I(self._donchian_lower, low, self.stop_period)
        self.atr = self.I(self._atr_indicator, high, low, close, 20)
        
    @staticmethod
    def _donchian_upper(high, period: int) -> np.ndarray:
        """ドンチャン上チャネル"""
        if hasattr(high, 'to_numpy'):
            data = high.to_numpy()
        else:
            data = np.array(high)
        
        result = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            result[i] = np.max(data[i - period + 1:i + 1])
        return result
    
    @staticmethod
    def _donchian_lower(low, period: int) -> np.ndarray:
        """ドンチャン下チャネル"""
        if hasattr(low, 'to_numpy'):
            data = low.to_numpy()
        else:
            data = np.array(low)
        
        result = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            result[i] = np.min(data[i - period + 1:i + 1])
        return result
        
    def _execute_strategy(self):
        """ドンチャンチャネル戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # 上ブレイクアウト
            if current_price > self.upper_channel[-1]:
                size = self._calculate_position_size()
                self.buy(size=size)
                # ストップ設定
                self.stop_loss_price = min(self.stop_lower[-1], 
                                         current_price - self.atr_multiplier * self.atr[-1])
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # 下ブレイクアウトまたはストップ
            if (current_price < self.lower_channel[-1] or
                current_price <= self.stop_loss_price):
                self.position.close()
                self.stop_loss_price = None

class MACDStrategy(BaseStrategy):
    """MACD戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 12  # backtesting用
    n_slow = 26  # backtesting用
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    volume_multiplier = 1.0
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        volume = self.data.Volume
        
        self.macd_line, self.signal_line, self.histogram = self.I(
            self._macd_indicator, close, self.macd_fast, self.macd_slow, self.macd_signal
        )
        self.volume_sma = self.I(self._sma_indicator, volume, 20)
        
    def _execute_strategy(self):
        """MACD戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_volume = self.data.Volume[-1]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # MACDゼロライン越え + シグナル上抜け
            macd_condition = (
                self.macd_line[-1] > 0 and
                self.macd_line[-1] > self.signal_line[-1] and
                self.macd_line[-2] <= self.signal_line[-2] and
                current_volume > self.volume_sma[-1] * self.volume_multiplier
            )
            
            if macd_condition:
                size = self._calculate_position_size()
                self.buy(size=size)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # MACDゼロライン下 + シグナル下抜け
            exit_condition = (
                self.macd_line[-1] < 0 and
                self.macd_line[-1] < self.signal_line[-1] and
                self.macd_line[-2] >= self.signal_line[-2]
            )
            
            if exit_condition:
                self.position.close()

class RSIMomentumStrategy(BaseStrategy):
    """RSIモメンタム戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 14  # backtesting用
    n_slow = 55  # backtesting用
    rsi_period = 14
    rsi_entry = 55
    rsi_exit_high = 70
    rsi_exit_low = 45
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        self.rsi = self.I(self._rsi_indicator, close, self.rsi_period)
        
    def _execute_strategy(self):
        """RSIモメンタム戦略の実行"""
        if not self._apply_common_filters():
            return
            
        rsi_current = self.rsi[-1]
        rsi_prev = self.rsi[-2]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # RSI上昇継続
            if (rsi_current > self.rsi_entry and rsi_current > rsi_prev):
                size = self._calculate_position_size()
                self.buy(size=size)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # 利確・損切条件
            if rsi_current >= self.rsi_exit_high or rsi_current <= self.rsi_exit_low:
                self.position.close()

class RSIExtremeStrategy(BaseStrategy):
    """RSI極端値戦略（逆張り）"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 2   # backtesting用
    n_slow = 200 # backtesting用
    rsi_period = 2
    rsi_oversold = 5
    rsi_overbought = 70
    sma_period = 200
    time_stop_days = 3
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        self.rsi = self.I(self._rsi_indicator, close, self.rsi_period)
        self.sma_200 = self.I(self._sma_indicator, close, self.sma_period)
        
    def _execute_strategy(self):
        """RSI極端値戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        rsi_current = self.rsi[-1]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # 上昇レジーム + RSI極端値
            if (current_price > self.sma_200[-1] and rsi_current < self.rsi_oversold):
                size = self._calculate_position_size()
                self.buy(size=size)
                self.entry_day = len(self.data)  # エントリー日を記録
                
        # ロングポジションがある場合
        elif self.position.is_long:
            current_day = len(self.data)
            days_held = current_day - self.entry_day
            
            # 利確・損切条件
            exit_condition = (
                rsi_current > self.rsi_overbought or
                days_held >= self.time_stop_days
            )
            
            if exit_condition:
                self.position.close()
                self.entry_day = None

class BollingerBandsStrategy(BaseStrategy):
    """ボリンジャーバンド戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 20  # backtesting用
    n_slow = 20  # backtesting用（bb_std * 10）
    bb_period = 20
    bb_std = 2.0
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            self._bollinger_bands, close, self.bb_period, self.bb_std
        )
        
    def _execute_strategy(self):
        """ボリンジャーバンド戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        current_open = self.data.Open[-1]
        prev_close = self.data.Close[-2]
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # バンド下限下抜け → 翌日陽線で復帰
            if (prev_close < self.bb_lower[-2] and
                current_price > current_open and  # 陽線
                current_price > self.bb_lower[-1]):  # バンド内復帰
                
                size = self._calculate_position_size()
                self.buy(size=size)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # 利確・損切条件
            if (current_price >= self.bb_middle[-1] or  # 中心線到達
                current_price < self.bb_lower[-1]):     # 再度バンド外
                self.position.close()

class SqueezeStrategy(BaseStrategy):
    """スクイーズ戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 20  # backtesting用
    n_slow = 20  # backtesting用
    bb_period = 20
    bb_std = 2.0
    keltner_period = 20
    keltner_multiplier = 2.0
    volume_multiplier = 1.5
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume
        
        # ボリンジャーバンド
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            self._bollinger_bands, close, self.bb_period, self.bb_std
        )
        
        # ケルトナーチャネル
        self.keltner_upper, self.keltner_middle, self.keltner_lower = self.I(
            self._keltner_channels, high, low, close, self.keltner_period, self.keltner_multiplier
        )
        
        # ボラティリティ指標
        self.bb_width = self.bb_upper - self.bb_lower
        self.volume_sma = self.I(self._sma_indicator, volume, 20)
        
    def _execute_strategy(self):
        """スクイーズ戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # ボラティリティの6ヶ月分布を計算（簡易版）
        if len(self.bb_width) >= 120:  # 6ヶ月分のデータ
            recent_bb_width = self.bb_width[-120:]
            bb_width_20th = np.percentile(recent_bb_width, 20)
            current_bb_width = self.bb_width[-1]
            
            # ロングポジションがない場合
            if not self.position.is_long:
                # スクイーズ条件
                squeeze_condition = (
                    current_bb_width <= bb_width_20th and  # 低ボラ状態
                    current_price > self.keltner_upper[-1] and  # ケルトナー上抜け
                    current_volume > self.volume_sma[-1] * self.volume_multiplier
                )
                
                if squeeze_condition:
                    size = self._calculate_position_size()
                    self.buy(size=size)
                    
            # ロングポジションがある場合
            elif self.position.is_long:
                # ボラティリティ拡大で利確
                if current_bb_width > bb_width_20th * 1.5:
                    self.position.close()

class VolumeBreakoutStrategy(BaseStrategy):
    """出来高ブレイク戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 20  # backtesting用
    n_slow = 20  # backtesting用（volume_multiplier * 10）
    breakout_period = 20
    volume_multiplier = 2.0
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        volume = self.data.Volume
        
        self.volume_sma = self.I(self._sma_indicator, volume, 20)
        
    def _execute_strategy(self):
        """出来高ブレイク戦略の実行"""
        if not self._apply_common_filters():
            return
            
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # 20日高値の計算
        high_20 = max(self.data.High[-self.breakout_period:])
        
        # ロングポジションがない場合
        if not self.position.is_long:
            # 出来高スパイク同伴のブレイク
            breakout_condition = (
                current_price > high_20 and
                current_volume > self.volume_sma[-1] * self.volume_multiplier
            )
            
            if breakout_condition:
                size = self._calculate_position_size()
                self.buy(size=size)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # シンプルな利確条件（例：10%上昇）
            entry_price = self.position.entry_price
            if current_price >= entry_price * 1.1:
                self.position.close()

class OBVStrategy(BaseStrategy):
    """OBVトレンド戦略"""
    
    # パラメータ（クラス変数として定義）
    n_fast = 20  # backtesting用
    n_slow = 50  # backtesting用
    obv_period = 20
    
    def _init_strategy_specific_indicators(self):
        """指標の初期化"""
        close = self.data.Close
        volume = self.data.Volume
        
        self.obv = self.I(self._obv_indicator, close, volume)
        self.obv_sma = self.I(self._sma_indicator, self.obv, self.obv_period)
        
    def _execute_strategy(self):
        """OBVトレンド戦略の実行"""
        if not self._apply_common_filters():
            return
            
        # ロングポジションがない場合
        if not self.position.is_long:
            # OBVトレンド条件
            obv_trend_condition = (
                self.obv[-1] > self.obv_sma[-1] and  # OBV > SMA
                self.obv_sma[-1] > self.obv_sma[-5]  # SMA上向き
            )
            
            if obv_trend_condition:
                size = self._calculate_position_size()
                self.buy(size=size)
                
        # ロングポジションがある場合
        elif self.position.is_long:
            # OBVトレンド転換
            if self.obv[-1] < self.obv_sma[-1]:
                self.position.close()

class StrategyFactory:
    """戦略ファクトリークラス"""
    
    _strategies = {}
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """戦略を登録"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"戦略クラスはBaseStrategyを継承する必要があります: {strategy_class}")
        
        # 重複登録を防ぐ
        if name not in cls._strategies:
            cls._strategies[name] = strategy_class
        else:
            logger.debug(f"戦略は既に登録済み: {name}")
    
    @classmethod
    def get_strategy(cls, strategy_name: str) -> type:
        """戦略クラスを取得"""
        if strategy_name not in cls._strategies:
            raise ValueError(f"戦略が見つかりません: {strategy_name}")
        return cls._strategies[strategy_name]
        
    @classmethod
    def clear_strategies(cls):
        """戦略をクリア"""
        cls._strategies.clear()
        logger.debug("戦略登録をクリアしました")
        
    @classmethod
    def get_strategy_count(cls) -> int:
        """登録済み戦略数を取得"""
        return len(cls._strategies)

# 戦略の登録
def register_all_strategies():
    """全ての戦略を登録"""
    # 既に登録されている場合はスキップ
    if StrategyFactory._strategies:
        return
        
    strategies_to_register = [
        ("FixedSma", FixedSmaStrategy),
        ("SmaCross", SmaCrossStrategy),
        ("Momentum", MomentumStrategy),
        ("MovingAverageBreakout", MovingAverageBreakoutStrategy),
        ("DonchianChannel", DonchianChannelStrategy),
        ("MACD", MACDStrategy),
        ("RSIMomentum", RSIMomentumStrategy),
        ("RSIExtreme", RSIExtremeStrategy),
        ("BollingerBands", BollingerBandsStrategy),
        ("Squeeze", SqueezeStrategy),
        ("VolumeBreakout", VolumeBreakoutStrategy),
        ("OBV", OBVStrategy),
    ]
    
    for name, strategy_class in strategies_to_register:
        StrategyFactory.register_strategy(name, strategy_class)
    
    logger.info(f"戦略登録完了: {len(StrategyFactory._strategies)}戦略")

# 戦略を登録（一度だけ実行）
def _ensure_strategies_registered():
    """戦略が登録されていることを保証"""
    if not StrategyFactory._strategies:
        register_all_strategies()
    return StrategyFactory.get_strategy_count()

# モジュール読み込み時に戦略を登録
_strategy_count = _ensure_strategies_registered()
