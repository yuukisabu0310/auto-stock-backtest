import pandas as pd
from backtesting import Backtest
from .strategy import SmaCross

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

def run_walk_forward_fixed(df, n_fast:int, n_slow:int, cash=100_000, commission=0.001):
    class FixedSma(SmaCross):
        pass
    FixedSma.n_fast = n_fast
    FixedSma.n_slow = n_slow

    windows = walk_forward_slices(df.index)
    rows, equity_parts = [], []

    for (tr_s, tr_e, te_s, te_e) in windows:
        train = df.loc[tr_s:tr_e].copy()
        test  = df.loc[te_s:te_e].copy()
        if len(train) < 200 or len(test) < 50:
            continue

        bt_test = Backtest(test, FixedSma, cash=cash, commission=commission, exclusive_orders=True)
        st = bt_test.run()
        st['train_start'], st['train_end'] = tr_s.date(), tr_e.date()
        st['test_start'],  st['test_end']  = te_s.date(), te_e.date()
        st['n_fast'], st['n_slow'] = n_fast, n_slow
        rows.append(st)

        eq = st['_equity_curve'][['Equity']].copy()
        eq.index = test.index[:len(eq)]
        equity_parts.append(eq)

    res_df = pd.DataFrame(rows) if rows else pd.DataFrame()
    equity = pd.concat(equity_parts) if equity_parts else pd.DataFrame()
    return res_df, equity
