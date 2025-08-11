import pandas as pd
from backtesting import Backtest

def run_walk_forward_fixed(df, n_fast=10, n_slow=20, strategy_class=None, cash=10_000, commission=.002):
    """
    与えられた DataFrame に対して Walk Forward 検証を行う関数
    複数銘柄対応 & 戦略クラスを外部から指定可能
    """
    if strategy_class is None:
        raise ValueError("strategy_class を指定してください")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame に必要なカラムが不足しています: {missing_cols}")

    df = df[required_cols]

    bt_test = Backtest(df, strategy_class, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt_test.run(n_fast=n_fast, n_slow=n_slow)
    return stats['_trades'], stats['_equity_curve']
