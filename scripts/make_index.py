# scripts/make_index.py
import os
from pathlib import Path
from html import escape

ROOT = Path("reports")
ROOT.mkdir(exist_ok=True, parents=True)

def li(path: Path) -> str:
    href = path.as_posix()
    return f"<li><a href='{escape(href)}'>{escape(path.name)}</a></li>"

def build():
    parts = []
    parts.append("<!doctype html><html><head>")
    parts.append("<meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    parts.append("<title>Backtest Reports</title>")
    parts.append("<style>body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:16px;line-height:1.5} h1{font-size:20px} h2{font-size:18px;margin-top:18px} ul{padding-left:18px} a{word-break:break-all}</style>")
    parts.append("</head><body>")
    parts.append("<h1>Backtest Reports</h1>")

    # 戦略ごとのディレクトリ（例: reports/FixedSma, reports/SmaCross）
    for strat_dir in sorted([p for p in ROOT.iterdir() if p.is_dir()]):
        files = sorted(strat_dir.glob("*"))
        if not files:
            continue
        parts.append(f"<h2>{escape(strat_dir.name)}</h2><ul>")
        # まず概要ファイルを先に
        for name in ["_params.txt", "_all_summary.csv"]:
            fp = strat_dir / name
            if fp.exists():
                parts.append(li(fp))
        # そのほかのファイル
        for f in files:
            if f.name in ["_params.txt", "_all_summary.csv"]:
                continue
            parts.append(li(f))
        parts.append("</ul>")

    # ルート直下のログなど
    root_files = [p for p in ROOT.iterdir() if p.is_file()]
    if root_files:
        parts.append("<h2>Others</h2><ul>")
        for f in sorted(root_files):
            parts.append(li(f))
        parts.append("</ul>")

    parts.append("</body></html>")
    (ROOT / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print("reports/index.html generated")

if __name__ == "__main__":
    build()
