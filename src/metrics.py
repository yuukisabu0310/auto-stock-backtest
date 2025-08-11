import numpy as np
import pandas as pd

def robust_score(df: pd.DataFrame):
    if df.empty: return -1e9
    med_sharpe = df.get("Sharpe Ratio", pd.Series([np.nan])).median()
    med_ret    = df.get("Return [%]", pd.Series([np.nan])).median()
    med_dd     = df.get("Max. Drawdown [%]", pd.Series([np.nan])).median()
    trades     = df.get("Trades", pd.Series([0])).median()
    iqr_sharpe = df.get("Sharpe Ratio", pd.Series([np.nan])).quantile(0.75) - \
                 df.get("Sharpe Ratio", pd.Series([np.nan])).quantile(0.25)
    trade_pen  = 0 if (pd.notna(trades) and trades >= 10) else -0.5
    score =  (med_sharpe if pd.notna(med_sharpe) else 0) \
             + 0.01*(med_ret if pd.notna(med_ret) else 0) \
             - 0.005*(med_dd if pd.notna(med_dd) else 0) \
             + trade_pen \
             - 0.2*(iqr_sharpe if np.isfinite(iqr_sharpe) else 0)
    return float(score)

def is_stable(best_tuple, candidate_folds_df, neighborhood, all_scores_dict):
    if candidate_folds_df.empty: return False
    best_score = all_scores_dict.get(best_tuple, -1e9)
    neigh_scores = [all_scores_dict.get(p,-1e9) for p in neighborhood]
    if not neigh_scores: return True
    ok = np.median(neigh_scores) >= 0.7 * best_score
    return bool(ok)
