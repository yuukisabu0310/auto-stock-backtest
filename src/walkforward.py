import pandas as pd
from backtesting import Backtest

# --- WFO 窓の生成（年単位） ---
def walk_forward_slices(index, train_years=5, test_years=1, step_years=1):
    i0, i1 = index.min(), index.max()
    cur = pd.Timestamp(i0)
    out = []
    while True:
        train_end = cur + pd.DateOffset(years=train_years) - pd.Timedelta(days=1)
        test_end  = train_end + pd.DateOffset(years=test_years)
        if test_end > i1:
            break
        out.append((cur, train_end, train_end + pd.Timedelta(days=1), test_end))
        cur = cur + pd.DateOffset(years=step_years)
    return out

# --- OHLCVの安全整形 ---
def _prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    # MultiIndex -> 単層
    if isinstance(df.columns, pd.MultiIndex):
        # yfinanceの戻り値は ('Close', 'AAPL') のような形式
        # 最初の要素（OHLCV名）を取得
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    req = ['Open','High','Low','Close','Volume']
    for c in req:
        if c not in df.columns:
            df[c] = pd.NA

    df = df[req].copy()

    # Index を Datetime に
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]

    # 最小限の埋め（価格は前日補間、出来高は0埋め）
    df[['Open','High','Low','Close']] = df[['Open','High','Low','Close']].ffill()
    if 'Volume' in df.columns:
        df['Volume'] = df['Volume'].fillna(0)

    # 価格がまだNaNなら落とす
    df = df.dropna(subset=['Open','High','Low','Close'])

    return df

def run_walk_forward_fixed(
    df: pd.DataFrame,
    n_fast: int = 10,
    n_slow: int = 20,
    strategy_class=None,
    ticker: str = "UNKNOWN",
    cash: float = 100_000,
    commission: float = .002,
    train_years: int = 5,
    test_years: int = 1,
    step_years: int = 1
):
    """
    年次 Walk-Forward 検証。
    戻り値:
      res_df  : 各フォールドの Backtest.run() サマリーSeriesを行として結合した DataFrame
      equity  : OOSエクイティ曲線（DateIndex, 'Equity' 1列）。無ければ空DataFrame
    """
    if strategy_class is None:
        raise ValueError("strategy_class を指定してください")

    df = _prepare_ohlcv(df)
    print(f"[DEBUG] {ticker}: n_fast={n_fast}, n_slow={n_slow}, rows={len(df)}")

    if df.empty or len(df) < max(n_fast, n_slow) + 10:
        # 取引はできないが、空落ちしないよう最低限の行を返す
        meta = {
            "Ticker": ticker, "Trades": 0, "Return [%]": 0.0,
            "Sharpe Ratio": float("nan"), "Max. Drawdown [%]": float("nan"),
            "n_fast": n_fast, "n_slow": n_slow
        }
        return pd.DataFrame([meta]), pd.DataFrame(columns=["Equity"])

    # 窓の作成
    windows = walk_forward_slices(df.index, train_years, test_years, step_years)
    rows, equity_parts = [], []

    # run() に渡すパラメータ
    run_kwargs = dict(n_fast=n_fast, n_slow=n_slow)

    for (tr_s, tr_e, te_s, te_e) in windows:
        train = df.loc[tr_s:tr_e]
        test  = df.loc[te_s:te_e]
        if len(train) < max(n_fast, n_slow) + 10 or len(test) < 40:  # 最低限
            continue

        bt = Backtest(test, strategy_class, cash=cash, commission=commission, exclusive_orders=True, finalize_trades=True)
        stats = bt.run(**run_kwargs)  # pandas.Series（Sharpe Ratio, Return[%], Trades など）

        # サマリーSeries -> 1行にして蓄積
        row = stats.to_dict()
        row.update({
            "Ticker": ticker,
            "n_fast": n_fast,
            "n_slow": n_slow,
            "train_start": tr_s.date(), "train_end": tr_e.date(),
            "test_start": te_s.date(),  "test_end": te_e.date(),
        })
        rows.append(row)

        # エクイティ曲線の連結（存在すれば）
        try:
            eq = bt._equity_curve[['Equity']].copy()
            if not isinstance(eq.index, pd.DatetimeIndex):
                # 念のためテスト期間のindexを付け直す
                eq.index = test.index[:len(eq)]
            equity_parts.append(eq)
        except Exception:
            pass

    res_df = pd.DataFrame(rows)
    equity = pd.concat(equity_parts) if equity_parts else pd.DataFrame(columns=["Equity"])
    return res_df, equity
