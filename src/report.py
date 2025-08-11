import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def summarize(res_df: pd.DataFrame):
    if res_df.empty:
        return {"folds": 0, "avg_sharpe": None, "avg_return_%": None, "avg_max_dd_%": None, "trades_sum": 0}
    fields = res_df.columns
    def med(col):  # ロバストのため中央値
        return float(res_df[col].median()) if col in fields else None
    def total(col):
        return int(res_df[col].sum()) if col in fields else 0
    return {
        "folds": int(len(res_df)),
        "avg_sharpe": med("Sharpe Ratio"),
        "avg_return_%": med("Return [%]"),
        "avg_max_dd_%": med("Max. Drawdown [%]"),
        "trades_sum": total("Trades"),
    }

def save_outputs(ticker:str, res_df:pd.DataFrame, equity:pd.DataFrame, out_dir="reports"):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base = ticker.replace(".","_")

    res_path = out / f"{base}_walkforward_result.csv"
    res_df.to_csv(res_path, index=False)

    summary = summarize(res_df)
    summary_path = out / f"{base}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    png_path = out / f"{base}_equity.png"
    if not equity.empty:
        plt.figure()
        equity['Equity'].plot()  # 色指定なし
        plt.title(f"OOS Equity Curve - {ticker}")
        plt.xlabel("Date"); plt.ylabel("Equity")
        plt.tight_layout(); plt.savefig(png_path, dpi=150); plt.close()

    return str(res_path), str(summary_path), str(png_path)
