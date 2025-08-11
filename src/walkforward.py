import pandas as pd
from backtesting import Backtest
from src.strategies import FixedSma

def run_walk_forward_fixed(df, n_fast=10, n_slow=20, cash=10_000, commission=.002):
    """
    与えられた DataFrame に対して Walk Forward 検証を行う関数
    複数銘柄対応（1銘柄ずつ処理前提）、MultiIndex解除とカラム整形を追加
    """

    # MultiIndex（階層化カラム）の場合は解除（例：yfinanceでgroup_by='ticker'取得時）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # 必要カラムのみに揃える（順番保証）
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame に必要なカラムが不足しています: {missing_cols}")

    df = df[required_cols]

    # Walk Forward 検証本体
    bt_test = Backtest(df, FixedSma, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt_test.run()
    return stats

def run_walk_forward_params(df, params_list, cash=10_000, commission=.002):
    """
    複数のパラメータセットに対して Walk Forward 検証を行う
    """
    results = []
    for params in params_list:
        n_fast = params.get("n_fast", 10)
        n_slow = params.get("n_slow", 20)
        stats = run_walk_forward_fixed(df, n_fast=n_fast, n_slow=n_slow, cash=cash, commission=commission)
        results.append({
            "n_fast": n_fast,
            "n_slow": n_slow,
            **stats
        })
    return pd.DataFrame(results)
