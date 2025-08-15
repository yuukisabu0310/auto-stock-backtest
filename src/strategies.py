from backtesting import Strategy
from backtesting.test import SMA
from backtesting.lib import crossover
import numpy as np

# ATR（Average True Range）の計算
def atr(h, l, c, n=14):
    # backtestingの_Arrayオブジェクトに対応したATR計算
    h_array = np.array(h)
    l_array = np.array(l)
    c_array = np.array(c)
    
    # 前日終値を計算（1つシフト）
    c_shifted = np.roll(c_array, 1)
    c_shifted[0] = c_array[0]  # 最初の値は同じにする
    
    # True Range計算
    tr1 = h_array - l_array
    tr2 = np.abs(h_array - c_shifted)
    tr3 = np.abs(l_array - c_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # 移動平均計算
    atr_values = np.zeros_like(tr)
    for i in range(len(tr)):
        if i < n - 1:
            atr_values[i] = np.nan
        else:
            atr_values[i] = np.mean(tr[i-n+1:i+1])
    
    return atr_values

# ===== 固定SMA戦略 =====
class FixedSma(Strategy):
    n_fast = 10
    n_slow = 20

    def init(self):
        close = self.data.Close
        self.sma_fast = self.I(SMA, close, self.n_fast)
        self.sma_slow = self.I(SMA, close, self.n_slow)

    def next(self):
        if crossover(self.sma_fast, self.sma_slow):
            self.position.close()
            self.buy()
        elif crossover(self.sma_slow, self.sma_fast):
            self.position.close()
            self.sell()

# ===== SMA + ATR リスク管理戦略 =====
class SmaCross(Strategy):
    n_fast = 20
    n_slow = 50
    target_vol_yr = 0.15   # 年間目標ボラティリティ
    risk_cap = 0.25        # 資金の最大リスク割合
    atr_n = 14             # ATR期間
    slip_k_atr = 0.05      # ATRスリッページ係数

    def init(self):
        close = self.data.Close
        self.sma_fast = self.I(SMA, close, self.n_fast)
        self.sma_slow = self.I(SMA, close, self.n_slow)
        self._atr = self.I(atr, self.data.High, self.data.Low, self.data.Close, self.atr_n)

    def next(self):
        atr_val = self._atr[-1]
        if not np.isfinite(atr_val) or atr_val <= 0:
            size = 0
        else:
            daily_vol = atr_val / self.data.Close[-1]
            if daily_vol and daily_vol > 0:
                target_pos_vol = self.target_vol_yr / (daily_vol * (252 ** 0.5))
                max_size = self.equity * self.risk_cap / self.data.Close[-1]
                size = max(0, min(max_size, self.equity * target_pos_vol / self.data.Close[-1]))
            else:
                size = 0

        px = self.data.Close[-1] * (
            1 + self.slip_k_atr * (atr_val / self.data.Close[-1] if self.data.Close[-1] else 0)
        )

        if crossover(self.sma_fast, self.sma_slow):
            if not self.position.is_long and size > 0:
                self.position.close()
                self.buy(size=size)
        elif crossover(self.sma_slow, self.sma_fast):
            if self.position.is_long:
                self.position.close()
