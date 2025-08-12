import pandas as pd
from backtesting import Backtest

def run_walk_forward_fixed(
    df,
    n_fast=10,
    n_slow=20,
    cash=10_000,
    commission=.002,
    strategy_class=None,
    ticker="UNKNOWN"
):
    """
    与えられた DataFrame に対して Walk Forward 検証を行う関数
    複数銘柄対応 / カラム補完 / 取引ゼロでも返却
    """

    # MultiIndex（階層化カラム）の場合は解除（例：yfinance group_by='ticker'）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # 必要カラムの補完
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[required_cols].dropna()

    print(f"[DEBUG] {ticker}: n_fast={n_fast}, n_slow={n_slow}, rows={len(df)}")

    if df.empty or len(df) < max(n_fast, n_slow) + 10:
        print(f"[WARN] {ticker}: データ不足でスキップ ({len(df)}行)")
        return pd.DataFrame([{"ticker": ticker, "n_fast": n_fast, "n_slow": n_slow, "trades": 0}]), None

    # Walk Forward 検証本体
    try:
        bt_test = Backtest(
            df,
            strategy_class,
            cash=cash,
            commission=commission,
            exclusive_orders=True
        )
        stats = bt_test.run(n_fast=n_fast, n_slow=n_slow)

        # 取引がない場合の対応
        trades = getattr(stats, "_trades", None)
        if trades is None or trades.empty:
            print(f"[INFO] {ticker}: 取引なし ({n_fast},{n_slow})")
            return pd.DataFrame([{
                "ticker": ticker,
                "n_fast": n_fast,
                "n_slow": n_slow,
                "trades": 0
            }]), bt_test.equity_curve

        # tradesがある場合はDataFrame化
        trades_df = trades.copy()
        trades_df["ticker"] = ticker
        trades_df["n_fast"] = n_fast
        trades_df["n_slow"] = n_slow
        trades_df["trades"] = len(trades_df)

        return trades_df, bt_test.equity_curve

    except Exception as e:
        print(f"[ERROR] {ticker}: Backtest失敗 ({n_fast},{n_slow}) - {e}")
        return pd.DataFrame([{
            "ticker": ticker,
            "n_fast": n_fast,
            "n_slow": n_slow,
            "trades": 0,
            "error": str(e)
        }]), None
