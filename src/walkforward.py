import pandas as pd
from backtesting import Backtest

def walk_forward_slices(index, train_years=5, test_years=1, step_years=1):
    """年単位で WFO のトレイン/テスト窓を作成"""
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

def _prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    # MultiIndex -> 単層化
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)
    # 必須カラムを揃える
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    for c in required:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[required].dropna()
    # backtesting.py は DatetimeIndex を期待
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass
    return df

def run_walk_forward_fixed(df: pd.DataFrame,
                           n_fast: int = 10,
                           n_slow: int = 20,
                           strategy_class=None,
                           cash: float = 100_000,
                           commission: float = .002,
                           train_years: int = 5,
                           test_years: int = 1,
                           step_years: int = 1):
    """
    与えられた日足DFに対して Walk-Forward（OOS）検証を実行し、
    各フォールドの stats を縦結合した DataFrame と、OOSのエクイティ曲線を返す。

    戻り値:
      res_df: 各フォールドの backtesting.Stats を行として結合した DataFrame
      equity: OOS期間を連結した資産曲線（DateIndex, 'Equity' の1列）
    """
    if strategy_class is None:
        raise ValueError("strategy_class を指定してください")

    df = _prepare_ohlcv(df)
    if df.empty or len(df) < 50:
        return pd.DataFrame(), pd.DataFrame()

    # ← 重要：stats を返す前提。トレードが0でも stats は返る。
    windows = walk_forward_slices(df.index, train_years, test_years, step_years)
    rows, equity_parts = [], []

    # backtesting.run の kwargs でパラメータを渡す（インスタンス属性に反映される）
    run_kwargs = dict(n_fast=n_fast, n_slow=n_slow)

    for (tr_s, tr_e, te_s, te_e) in windows:
        train = df.loc[tr_s:tr_e]
        test  = df.loc[te_s:te_e]
        # 最低限の長さを確保
        if len(train) < 200 or len(test) < 50:
            continue

        bt = Backtest(test, strategy_class, cash=cash, commission=commission, exclusive_orders=True)
        st = bt.run(**run_kwargs)  # <- Sharpe/Return[%]/Trades 等を含む Stats

        # 行に識別用メタを付与
        st['train_start'], st['train_end'] = tr_s.date(), tr_e.date()
        st['test_start'],  st['test_end']  = te_s.date(), te_e.date()
        st['n_fast'], st['n_slow'] = n_fast, n_slow
        rows.append(st)

        # OOSエクイティ（存在すれば）
        eq = getattr(st, "_equity_curve", None)
        if eq is None:
            # backtesting>=0.4 では bt._equity_curve にある
            try:
                eq = bt._equity_curve[['Equity']].copy()
            except Exception:
                eq = None
        if eq is not None and not eq.empty:
            # テスト期間の index を付け直す（安全のため）
            eq = eq[['Equity']].copy()
            if not isinstance(eq.index, pd.DatetimeIndex):
                eq.index = test.index[:len(eq)]
            equity_parts.append(eq)

    res_df = pd.DataFrame(rows) if rows else pd.DataFrame()
    equity = pd.concat(equity_parts) if equity_parts else pd.DataFrame()
    return res_df, equity
