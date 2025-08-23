#!/usr/bin/env python3
"""
OOSファイルから正しいトレード数と指標を再計算して_all_summary.csvを修正するスクリプト
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
import glob

def fix_summary_data():
    """各戦略の_all_summary.csvをOOSファイルから正しく再計算"""
    
    reports_dir = Path("reports")
    if not reports_dir.exists():
        print("reportsディレクトリが見つかりません")
        return
    
    for strategy_dir in reports_dir.iterdir():
        if not strategy_dir.is_dir():
            continue
            
        strategy_name = strategy_dir.name
        print(f"処理中: {strategy_name}")
        
        # OOSファイルを検索
        oos_files = list(strategy_dir.glob("*_OOS_walkforward_result.csv"))
        if not oos_files:
            print(f"  OOSファイルが見つかりません: {strategy_name}")
            continue
        
        # 各OOSファイルからデータを集計
        all_data = []
        for oos_file in oos_files:
            try:
                df = pd.read_csv(oos_file)
                if df.empty:
                    continue
                    
                # ファイル名からtickerを抽出
                ticker = oos_file.stem.replace("_OOS_walkforward_result", "")
                
                # 基本統計を計算
                row_data = {
                    'ticker': ticker,
                    'strategy': strategy_name,
                    'folds': len(df),
                    'avg_sharpe': float(df['Sharpe Ratio'].median()) if 'Sharpe Ratio' in df.columns else 0.0,
                    'avg_return_%': float(df['Return [%]'].median()) if 'Return [%]' in df.columns else 0.0,
                    'avg_max_dd_%': float(df['Max. Drawdown [%]'].median()) if 'Max. Drawdown [%]' in df.columns else 0.0,
                    'trades_sum': int(df['# Trades'].sum()) if '# Trades' in df.columns else 0,
                    'avg_win_rate': float(df['Win Rate [%]'].median()) if 'Win Rate [%]' in df.columns else 50.0,
                    'avg_profit_factor': float(df['Profit Factor'].median()) if 'Profit Factor' in df.columns else 1.0
                }
                all_data.append(row_data)
                
            except Exception as e:
                print(f"  エラー: {oos_file} - {e}")
                continue
        
        if not all_data:
            print(f"  データが見つかりません: {strategy_name}")
            continue
        
        # DataFrameに変換して保存
        summary_df = pd.DataFrame(all_data)
        summary_file = strategy_dir / "_all_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        
        print(f"  修正完了: {len(all_data)}銘柄, 総トレード数: {summary_df['trades_sum'].sum()}")
    
    print("すべての戦略のサマリーデータを修正しました")

if __name__ == "__main__":
    fix_summary_data()
