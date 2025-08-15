import os, random
import yfinance as yf
import pandas as pd
from multiprocessing import Pool, cpu_count

from src.walkforward import run_walk_forward_fixed
from src.report import save_outputs, summarize
from src.universe import split_universe
from src.sampler import stratified_sample
from src.metrics import robust_score, is_stable

HOLDOUT_MONTHS = int(os.getenv("HOLDOUT_MONTHS", "12"))

def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinanceの戻りの列を正規化（MultiIndex解除、大小文字揺れ、最小補完）"""
    if df is None or df.empty:
        return pd.DataFrame()

    # MultiIndex -> 単層
    if isinstance(df.columns, pd.MultiIndex):
        # yfinanceの戻り値は ('Close', 'AAPL') のような形式
        # 最初の要素（OHLCV名）を取得
        try:
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        except Exception:
            # ドロップできなくても後続の正規化で対応
            pass

    # 列名の大小文字ゆれを吸収
    ren = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=ren)

    # 期待キー
    has_close = "close" in df.columns
    has_open  = "open"  in df.columns
    has_high  = "high"  in df.columns
    has_low   = "low"   in df.columns
    has_vol   = "volume" in df.columns

    # Close が無い場合は致命的 → ゼロ件扱い
    if not has_close:
        return pd.DataFrame()

    # OHLC の欠損は Close で補完（最低限動かすためのフォールバック）
    if not has_open: df["open"] = df["close"]
    if not has_high: df["high"] = df["close"]
    if not has_low:  df["low"]  = df["close"]
    if not has_vol:  df["volume"] = 0

    # 列の並びを保証
    df = df[["open","high","low","close","volume"]].copy()

    # Index を Datetime に
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]

    # 価格の前日補間（念のため）
    df[["open","high","low","close"]] = df[["open","high","low","close"]].ffill()
    # volume 欠損は 0
    df["volume"] = df["volume"].fillna(0)

    # タイトルケースに戻す（以降の処理が ['Open',...] 前提のため）
    df = df.rename(columns={
        "open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"
    })
    return df

def load_ohlcv(ticker, start="2005-01-01", end=None):
    """yfinanceで価格取得 + 列正規化 + 最小補完 + ログ出力"""
    try:
        df = yf.download(
            ticker, start=start, end=end,
            auto_adjust=True, progress=False, threads=False
        )
    except Exception as e:
        print(f"[ERROR] {ticker} データ取得失敗: {e}")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    if df is None or df.empty:
        print(f"[ERROR] {ticker} → データ取得0件")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    df = _normalize_ohlcv_columns(df)

    if df.empty:
        print(f"[ERROR] {ticker} → 列正規化後もデータ0件（Close 欠損など）")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    # ごく基本の品質フィルタ（価格が still NaN のものは落とす）
    df = df.dropna(subset=['Open','High','Low','Close'])
    if df.empty:
        print(f"[ERROR] {ticker} → 欠損除去後データ0件")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    print(f"[INFO] {ticker} データ取得成功: {len(df)}件")
    return df

def split_holdout(df: pd.DataFrame, months=12):
    if df.empty: 
        return pd.DataFrame(), pd.DataFrame()
    cutoff = (df.index.max() - pd.DateOffset(months=months)).normalize()
    in_sample = df[df.index <= cutoff]
    holdout   = df[df.index >  cutoff]
    return in_sample, holdout

def grid_candidates():
    fast = [5,10,15,20]
    slow = [40,60,80,100]
    return [(f,s) for f in fast for s in slow if f < s]

def eval_params_on_ticker(args):
    tkr, df, nf, ns, strategy_class = args
    if df.empty or len(df) < 20:  # 最低20営業日
        print(f"[SKIP] {tkr} データ不足（{len(df)}件）")
        return (tkr, (nf,ns), None)
    res_df, _ = run_walk_forward_fixed(
        df, n_fast=nf, n_slow=ns,
        strategy_class=strategy_class, ticker=tkr
    )
    return (tkr, (nf,ns), res_df)

def main():
    from src.strategies import FixedSma, SmaCross
    strategies = [("FixedSma", FixedSma), ("SmaCross", SmaCross)]

    # Slackから来る固定OOS（学習には含めない）
    fixed = [t.strip() for t in os.getenv("OOS_FIXED_TICKERS","").split(",") if t.strip()]
    extra = [t.strip() for t in os.getenv("EXTRA_TICKERS","").split(",") if t.strip()]

    non_ai, ai = split_universe(extra)

    SAMPLE_SIZE   = int(os.getenv("SAMPLE_SIZE", "12"))
    OOS_RANDOM_SZ = int(os.getenv("OOS_RANDOM_SIZE", "8"))
    SEED = os.getenv("RANDOM_SEED","")
    if SEED:
        try: random.seed(int(SEED))
        except: random.seed(SEED)
    else:
        random.seed(pd.Timestamp.today().date().toordinal())

    # 学習: 非AIから層化ランダム
    learn_pool = sorted(set(non_ai) - set(fixed))
    learn_list = stratified_sample(learn_pool, SAMPLE_SIZE, seed=random.random())

    # 検証: ランダム + 固定
    oos_pool = sorted(set(learn_pool) - set(learn_list) - set(fixed))
    rand_oos = stratified_sample(oos_pool, OOS_RANDOM_SZ, seed=random.random())
    oos_all = sorted(set(rand_oos).union(set(fixed)))

    print(f"[learn(non-AI stratified)] {learn_list}")
    print(f"[OOS fixed] {fixed}")
    print(f"[OOS random] {rand_oos}")

    # 価格のロード & ホールドアウト分割
    price_cache_in, price_cache_ho = {}, {}
    for t in sorted(set(learn_list + oos_all)):
        full = load_ohlcv(t)
        ins, ho = split_holdout(full, HOLDOUT_MONTHS)
        price_cache_in[t] = ins
        price_cache_ho[t] = ho

    # 戦略ごとに実行
    for strat_name, strat_class in strategies:
        print(f"\n===== 戦略 {strat_name} の処理開始 =====")

        # パラメータ探索（walk-forwardで評価）
        cand = grid_candidates()
        tasks = []
        for t in learn_list:
            df_in = price_cache_in[t]
            if df_in.empty or len(df_in) < 20:
                print(f"[WARN] {t} はデータ不足のためスキップ ({len(df_in)}件)")
                continue
            for nf, ns in cand:
                tasks.append((t, df_in, nf, ns, strat_class))

        if not tasks:
            print(f"[ERROR] 学習用データがありません ({strat_name})")
            continue

        with Pool(min(max(1,cpu_count()-1), 6)) as p:
            results = p.map(eval_params_on_ticker, tasks)

        df_map = {}
        for (tkr, param, res_df) in results:
            if res_df is None or res_df.empty: 
                continue
            df_map.setdefault(param, []).append(res_df)

        scored = []
        for param, dfs in df_map.items():
            all_df = pd.concat(dfs, ignore_index=True)
            scored.append((param, robust_score(all_df), all_df))

        if not scored:
            print(f"[ERROR] スコア計算できません ({strat_name})")
            continue

        def neighbors(p):
            nf, ns = p
            hood = []
            for d in (-5,0,5):
                for e in (-20,0,20):
                    nf2, ns2 = nf+d, ns+e
                    if nf2<1 or ns2<=nf2: continue
                    hood.append((nf2,ns2))
            return hood

        score_dict = {p:s for (p,s,_) in scored}
        best_tuple = None
        for (p, s, df_all) in sorted(scored, key=lambda x: x[1], reverse=True):
            if is_stable(p, df_all, neighbors(p), score_dict):
                best_tuple = p
                best_score = s
                best_df_all = df_all
                break
        if best_tuple is None:
            best_tuple, best_score, best_df_all = max(scored, key=lambda x:x[1])[0:3]

        best_nf, best_ns = best_tuple
        print(f"[best params] n_fast={best_nf}, n_slow={best_ns}, score={best_score:.4f} (stable)")

        # 戦略別フォルダ作成
        strat_dir = os.path.join("reports", strat_name)
        os.makedirs(strat_dir, exist_ok=True)

        def eval_group(tickers, label, use_holdout=False):
            rows = []
            for t in tickers:
                df = price_cache_ho[t] if use_holdout else price_cache_in[t]
                if df.empty or len(df) < 20:
                    rows.append({"ticker":t, "label":label, "folds":0})
                    continue
                res_df, eq = run_walk_forward_fixed(
                    df, n_fast=best_nf, n_slow=best_ns,
                    strategy_class=strat_class, ticker=t
                )
                # eq は必ず DataFrame（空でOK）
                save_outputs(f"{t}_{label}", res_df, eq, out_dir=strat_dir)
                rows.append({**summarize(res_df), "ticker":t, "label":label})
            return pd.DataFrame(rows)

        df_oos_nonai = eval_group(rand_oos, "OOS_nonAI", use_holdout=False)
        df_oos_fixed = eval_group(fixed,    "OOS_fixed",   use_holdout=False)
        df_ho_nonai  = eval_group(rand_oos, "HOLDOUT_nonAI", use_holdout=True)
        df_ho_fixed  = eval_group(fixed,    "HOLDOUT_fixed",  use_holdout=True)

        # 空のDataFrameを除外してからconcat
        dfs_to_concat = []
        for df, name in [(df_oos_nonai, "df_oos_nonai"), (df_oos_fixed, "df_oos_fixed"), 
                         (df_ho_nonai, "df_ho_nonai"), (df_ho_fixed, "df_ho_fixed")]:
            if df is not None and not df.empty:
                dfs_to_concat.append(df)
        
        if dfs_to_concat:
            out = pd.concat(dfs_to_concat, ignore_index=True)
        else:
            # 全て空の場合は空のDataFrameを作成
            out = pd.DataFrame()
        out.to_csv(os.path.join(strat_dir, "_all_summary.csv"), index=False)

        with open(os.path.join(strat_dir, "_params.txt"),"w",encoding="utf-8") as f:
            f.write(f"best_n_fast={best_nf}\nbest_n_slow={best_ns}\nscore={best_score:.6f}\n")
            f.write(f"learn_nonAI={learn_list}\nOOS_fixed={fixed}\nOOS_random={rand_oos}\n")
            f.write(f"holdout_months={HOLDOUT_MONTHS}\n")

        print(f"[{strat_name}] Backtest done. Reports in {strat_dir}")

if __name__ == "__main__":
    main()
