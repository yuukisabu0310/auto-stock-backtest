import pandas as pd
from backtesting import Backtest


def run_walk_forward_fixed(df, n_fast=10, n_slow=20, strategy_class=None,
                           cash=10_000, commission=.002):
    """
    与えられた DataFrame に対して Walk Forward 検証を行う関数
    - 複数銘柄対応
    - MultiIndex解除
    - 必須カラム不足時は補完して欠損行を削除
    - 複数戦略に対応（strategy_class を引数で指定）
    """
    if strategy_class is None:
        raise ValueError("strategy_class を指定してください")

    # MultiIndex（階層化カラム）の場合は解除
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # 必須カラムを揃える（欠けていれば補完）
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # 必須カラム順に並び替えて NaN 行を削除
    df = df[required_cols].dropna()

    # データ不足なら空で返す
    if df.empty or len(df) < 50:
        return pd.DataFrame(), pd.DataFrame()

    # Backtest 実行
    bt_test = Backtest(df, strategy_class,
                       cash=cash, commission=commission, exclusive_orders=True)
    stats = bt_test.run(n_fast=n_fast, n_slow=n_slow)

    # トレード履歴と損益曲線を返す
    trades = stats._trades if hasattr(stats, "_trades") else pd.DataFrame()
    equity = stats._equity_curve if hasattr(stats, "_equity_curve") else pd.DataFrame()

    return trades, equity
