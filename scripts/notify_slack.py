import os, json, time, mimetypes
import requests

def post_webhook(text: str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return False
    payload = {"text": text}
    requests.post(url, headers={"Content-Type":"application/json"}, data=json.dumps(payload))
    return True

def post_files(token: str, channel: str, filepaths: list, initial_comment: str):
    if not token or not channel or not filepaths:
        return False
    api = "https://slack.com/api/files.upload"
    ok_any = False
    for p in filepaths:
        if not os.path.exists(p):
            continue
        with open(p, "rb") as f:
            filename = os.path.basename(p)
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            r = requests.post(api,
                headers={"Authorization": f"Bearer {token}"},
                data={"channels": channel, "initial_comment": initial_comment if not ok_any else ""},
                files={"file": (filename, f, mime)})
            try:
                data = r.json()
                ok_any = ok_any or bool(data.get("ok"))
            except Exception:
                pass
            time.sleep(0.7)
    return ok_any

if __name__ == "__main__":
    msg = os.getenv("SLACK_MESSAGE", "Backtest finished.")
    try:
        if os.path.exists("reports/_all_summary.csv"):
            import pandas as pd
            df = pd.read_csv("reports/_all_summary.csv")
            lines = []
            for _, r in df.iterrows():
                lines.append(
                    f"• {r.get('ticker','?')} [{r.get('label','')}] "
                    f"folds={int(r.get('folds',0))}, "
                    f"Sharpe_med={round(float(r.get('avg_sharpe')),2) if pd.notna(r.get('avg_sharpe')) else 'NA'}, "
                    f"Ret_med%={round(float(r.get('avg_return_%')),2) if pd.notna(r.get('avg_return_%')) else 'NA'}, "
                    f"DD_med%={round(float(r.get('avg_max_dd_%')),2) if pd.notna(r.get('avg_max_dd_%')) else 'NA'}"
                )
            msg += "\n" + "\n".join(lines)
    except Exception as e:
        msg += f"\n(summary parse error: {e})"

    post_webhook(msg)

    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL")
    file_list = []
    if os.path.isdir("reports"):
        for f in os.listdir("reports"):
            if f.endswith((".png",".csv",".json",".txt")):
                file_list.append(os.path.join("reports", f))

    if token and channel and file_list:
        post_files(token, channel, file_list, "Backtest artifacts")

    print("Slack notification done.")
