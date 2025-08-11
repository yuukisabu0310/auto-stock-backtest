import os, re, requests

TOKEN = os.getenv("SLACK_BOT_TOKEN")
CHAN  = os.getenv("SLACK_CONFIG_CHANNEL")
LIMIT = int(os.getenv("SLACK_FETCH_LIMIT", "50"))

def resolve_channel_id(token, chan):
    if chan and chan.startswith("C") and len(chan) > 8:
        return chan
    if not chan:
        raise RuntimeError("SLACK_CONFIG_CHANNEL is empty")
    name = chan[1:] if chan.startswith("#") else chan
    url = "https://slack.com/api/conversations.list"
    cursor = None
    while True:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                         params={"limit": 1000, **({"cursor":cursor} if cursor else {})})
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"conversations.list failed: {data}")
        for c in data.get("channels", []):
            if c.get("name") == name:
                return c.get("id")
        cursor = data.get("response_metadata",{}).get("next_cursor")
        if not cursor:
            break
    raise RuntimeError(f"Channel not found: {chan}")

def latest_oos_line(token, channel_id, limit=50):
    url = "https://slack.com/api/conversations.history"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                     params={"channel": channel_id, "limit": limit})
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"conversations.history failed: {data}")
    pat = re.compile(r'^\s*OOS\s*:\s*(.+)$', re.IGNORECASE)
    for msg in data.get("messages", []):
        text = msg.get("text","")
        for line in text.splitlines():
            m = pat.match(line.strip())
            if m:
                return m.group(1).strip()
    return ""

def normalize_tickers(s):
    s = re.sub(r'[;｜|]', ',', s)
    parts = [p.strip() for p in re.split(r'[,\s]+', s) if p.strip()]
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p); out.append(p)
    return ",".join(out)

def main():
    if not TOKEN or not CHAN:
        print("", end=""); return
    try:
        cid = resolve_channel_id(TOKEN, CHAN)
        raw = latest_oos_line(TOKEN, cid, LIMIT)
        tickers = normalize_tickers(raw) if raw else ""
        print(tickers, end="")
        os.makedirs("reports", exist_ok=True)
        with open("reports/_oos_from_slack.txt","w",encoding="utf-8") as f:
            f.write((tickers or "") + "\n")
    except Exception as e:
        print("", end="")
        os.makedirs("reports", exist_ok=True)
        with open("reports/_oos_from_slack_error.txt","w",encoding="utf-8") as f:
            f.write(str(e))

if __name__ == "__main__":
    main()
