import pandas as pd
from backtesting import Backtest
from src.strategies import FixedSma  # デフォルト戦略

def run_walk_forward_fixed(df, n_fast=10, n_slow=20, cash=10_000, commission=.002, strategy_class=None):
    """
    与えられた DataFrame に対して Walk Forward 検証を行う関数
    複数銘柄対応（1銘柄ずつ処理前提）
    strategy_class を指定すれば任意の戦略を使用可能
    """

    if strategy_class is None:
        strategy_class = FixedSma

    # MultiIndex（階層化カラム）の場合は解除
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # 必要カラムをチェック
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame に必要なカラムが不足しています: {missing_cols}")

    df = df[required_cols]

    # 戦略パラメータを設定
    strategy_class.n_fast = n_fast
    strategy_class.n_slow = n_slow

    # Walk Forward 検証
    bt_test = Backtest(df, strategy_class, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt_test.run()
    return stats

def run_walk_forward_params(df, params_list, cash=10_000, commission=.002, strategy_class=None):
    """
    複数のパラメータセットに対して Walk Forward 検証を行う
    strategy_class を指定すれば任意の戦略を使用可能
    """
    results = []
    for params in params_list:
        n_fast = params.get("n_fast", 10)
        n_slow = params.get("n_slow", 20)
        stats = run_walk_forward_fixed(
            df, n_fast=n_fast, n_slow=n_slow, cash=cash, commission=commission, strategy_class=strategy_class
        )
        results.append({
            "n_fast": n_fast,
            "n_slow": n_slow,
            **stats
        })
    return pd.DataFrame(results)
