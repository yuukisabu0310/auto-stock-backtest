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

def load_ohlcv(ticker, start="2005-01-01", end=None):
    """yfinanceで価格取得 + 必須カラム揃える + ログ出力"""
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    except Exception as e:
        print(f"[ERROR] {ticker} データ取得失敗: {e}")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    if df.empty:
        print(f"[ERROR] {ticker} → データ取得0件")
        return pd.DataFrame(columns=['Open','High','Low','Close','Volume'])

    # 必須カラム補完
    for col in ['Open','High','Low','Close','Volume']:
        if col not in df.columns:
            print(f"[WARN] {ticker} → 欠損カラム {col} をNaNで補完")
            df[col] = pd.NA

    # カラム順を保証し、欠損を削除
    df = df[['Open','High','Low','Close','Volume']].dropna()

    if df.empty:
        print(f"[ERROR] {ticker} → 欠損除去後データ0件")
    else:
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
    res_df, _ = run_walk_forward_fixed(df, n_fast=nf, n_slow=ns, strategy_class=strategy_class)
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

        # 検証 & ホールドアウトの評価
        def eval_group(tickers, label, use_holdout=False):
            rows = []
            for t in tickers:
                df = price_cache_ho[t] if use_holdout else price_cache_in[t]
                if df.empty or len(df) < 20:
                    rows.append({"ticker":t, "label":label, "folds":0})
                    continue
                res_df, eq = run_walk_forward_fixed(df, n_fast=best_nf, n_slow=best_ns, strategy_class=strat_class)
                save_outputs(f"{t}_{label}_{strat_name}", res_df, eq)
                rows.append({**summarize(res_df), "ticker":t, "label":label})
            return pd.DataFrame(rows)

        df_oos_nonai = eval_group(rand_oos, "OOS_nonAI", use_holdout=False)
        df_oos_fixed = eval_group(fixed,    "OOS_fixed",   use_holdout=False)
        df_ho_nonai  = eval_group(rand_oos, "HOLDOUT_nonAI", use_holdout=True)
        df_ho_fixed  = eval_group(fixed,    "HOLDOUT_fixed",  use_holdout=True)

        out = pd.concat([df_oos_nonai, df_oos_fixed, df_ho_nonai, df_ho_fixed], ignore_index=True)
        os.makedirs("reports", exist_ok=True)
        out.to_csv(f"reports/{strat_name}_all_summary.csv", index=False)
        with open(f"reports/{strat_name}_params.txt","w",encoding="utf-8") as f:
            f.write(f"best_n_fast={best_nf}\nbest_n_slow={best_ns}\nscore={best_score:.6f}\n")
            f.write(f"learn_nonAI={learn_list}\nOOS_fixed={fixed}\nOOS_random={rand_oos}\n")
            f.write(f"holdout_months={HOLDOUT_MONTHS}\n")

        print(f"[{strat_name}] Backtest done. Reports in ./reports")

if __name__ == "__main__":
    main()
