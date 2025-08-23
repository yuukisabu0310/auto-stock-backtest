# scripts/make_index.py
import os
from pathlib import Path
from html import escape

ROOT = Path("reports")
ROOT.mkdir(exist_ok=True, parents=True)



def build():
    """メインのビルド関数"""
    # Enhanced Dashboardのみを生成
    try:
        import sys
        import os
        # scriptsディレクトリをパスに追加
        scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        sys.path.insert(0, scripts_dir)
        
        from enhanced_dashboard import generate_enhanced_dashboard_data
        from create_enhanced_dashboard import generate_enhanced_dashboard
        
        print("Generating enhanced dashboard data...")
        generate_enhanced_dashboard_data()
        
        print("Generating enhanced dashboard HTML...")
        generate_enhanced_dashboard()
        
        # enhanced_index.htmlをindex.htmlにコピー
        import shutil
        enhanced_file = ROOT / "enhanced_index.html"
        index_file = ROOT / "index.html"
        if enhanced_file.exists():
            shutil.copy2(enhanced_file, index_file)
            print("reports/index.html generated (Enhanced Dashboard)")
        else:
            print("Enhanced dashboard file not found")
            
    except Exception as e:
        print(f"Enhanced dashboard generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # ファイルリストも生成
    generate_file_list()

def generate_file_list():
    """従来のファイルリストを生成"""
    parts = []
    parts.append("<!doctype html><html><head>")
    parts.append("<meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    parts.append("<title>Backtest Reports - File List</title>")
    parts.append("<style>body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:16px;line-height:1.5} h1{font-size:20px} h2{font-size:18px;margin-top:18px} ul{padding-left:18px} a{word-break:break-all}</style>")
    parts.append("</head><body>")
    parts.append("<h1>Backtest Reports - File List</h1>")
    parts.append('<p><a href="index.html">← ダッシュボードに戻る</a></p>')

    # 戦略ごとのディレクトリ
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
    (ROOT / "files.html").write_text("\n".join(parts), encoding="utf-8")
    print("reports/files.html generated (File List)")

def li(path: Path) -> str:
    href = path.as_posix()
    return f"<li><a href='{escape(href)}'>{escape(path.name)}</a></li>"

if __name__ == "__main__":
    build()
