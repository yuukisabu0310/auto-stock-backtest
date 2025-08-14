"""
データ管理モジュール
データ取得、キャッシュ、品質チェック機能を提供します
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import time
import os
from pathlib import Path
import pickle
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from src.config import config
from src.logger import get_logger

logger = get_logger("data_manager")

class DataManager:
    """データ取得と管理を行うクラス"""
    
    def __init__(self):
        self.backtest_config = config.get_backtest_config()
        self.data_config = self.backtest_config.get('data', {})
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_ohlcv_data(self, ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """OHLCVデータを取得（キャッシュ対応）"""
        if start_date is None:
            start_date = self.backtest_config.get('start_date', '2005-01-01')
        if end_date is None:
            end_date = self.backtest_config.get('end_date')
            
        # キャッシュチェック
        cached_data = self._load_from_cache(ticker, start_date, end_date)
        if cached_data is not None:
            logger.debug(f"キャッシュからデータ読み込み: {ticker}")
            return cached_data
            
        # データ取得
        data = self._fetch_data_with_retry(ticker, start_date, end_date)
        
        if data is not None and not data.empty:
            # データ品質チェック
            data = self._validate_and_clean_data(data, ticker)
            
            # キャッシュに保存
            self._save_to_cache(ticker, start_date, end_date, data)
            
        return data if data is not None else pd.DataFrame()
        
    def _fetch_data_with_retry(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """リトライ機能付きデータ取得"""
        max_attempts = self.data_config.get('retry_attempts', 3)
        retry_delay = self.data_config.get('retry_delay', 60)
        rate_limit_delay = self.data_config.get('rate_limit_delay', 1)
        
        for attempt in range(max_attempts):
            try:
                logger.debug(f"データ取得試行 {attempt + 1}/{max_attempts}: {ticker}")
                
                # レート制限対応
                time.sleep(rate_limit_delay)
                
                df = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    auto_adjust=True,
                    progress=False,
                    threads=False
                )
                
                if df is not None and not df.empty:
                    df = self._normalize_ohlcv_columns(df)
                    logger.log_data_fetch(ticker, True, len(df))
                    return df
                else:
                    logger.log_data_fetch(ticker, False, 0, "データが空")
                    return None
                    
            except Exception as e:
                error_msg = str(e)
                logger.log_data_fetch(ticker, False, 0, error_msg)
                
                # レート制限エラーの場合は待機
                if "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                    logger.warning(f"レート制限検出: {ticker} - {retry_delay}秒待機")
                    time.sleep(retry_delay)
                elif attempt < max_attempts - 1:
                    logger.warning(f"データ取得失敗: {ticker} - 再試行します")
                    time.sleep(retry_delay)
                    
        logger.error(f"データ取得最終失敗: {ticker} - {max_attempts}回試行")
        return None
        
    def _normalize_ohlcv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """OHLCV列の正規化"""
        if df is None or df.empty:
            return pd.DataFrame()
            
        # MultiIndex -> 単層
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            
        # 列名の正規化
        column_mapping = {
            'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume',
            'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 必要な列の存在確認
        required_columns = ['Open', 'High', 'Low', 'Close']
        for col in required_columns:
            if col not in df.columns:
                df[col] = df['Close'] if 'Close' in df.columns else np.nan
                
        if 'Volume' not in df.columns:
            df['Volume'] = 0
            
        # 列の順序を統一
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # インデックスをDatetimeに変換
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, errors='coerce')
        df = df[~df.index.isna()]
        
        # 欠損値の処理
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].ffill()
        df['Volume'] = df['Volume'].fillna(0)
        
        # 最終的な品質チェック
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        return df
        
    def _validate_and_clean_data(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """データの品質チェックとクリーニング"""
        if df.empty:
            return df
            
        original_length = len(df)
        
        # 異常値の検出と処理
        df = self._remove_outliers(df)
        
        # 価格の妥当性チェック
        df = self._validate_prices(df)
        
        # 出来高の妥当性チェック
        df = self._validate_volume(df)
        
        # 最小データポイントチェック
        min_points = self.backtest_config.get('walkforward', {}).get('min_data_points', 20)
        if len(df) < min_points:
            logger.warning(f"データ不足: {ticker} - {len(df)}件 < {min_points}件")
            return pd.DataFrame()
            
        if len(df) != original_length:
            logger.info(f"データクリーニング完了: {ticker} - {original_length}件 → {len(df)}件")
            
        return df
        
    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """異常値の除去"""
        # 価格の異常値検出（前日比±50%以上）
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in df.columns:
                returns = df[col].pct_change().abs()
                outliers = returns > 0.5
                if outliers.any():
                    df.loc[outliers, col] = np.nan
                    
        # 欠損値を前日値で補完
        df[price_cols] = df[price_cols].ffill()
        
        return df
        
    def _validate_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """価格の妥当性チェック"""
        # High >= Low のチェック
        if 'High' in df.columns and 'Low' in df.columns:
            invalid_high_low = df['High'] < df['Low']
            if invalid_high_low.any():
                df.loc[invalid_high_low, 'High'] = df.loc[invalid_high_low, 'Low']
                
        # Open, Close が High, Low の範囲内かチェック
        if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            invalid_open = (df['Open'] > df['High']) | (df['Open'] < df['Low'])
            invalid_close = (df['Close'] > df['High']) | (df['Close'] < df['Low'])
            
            if invalid_open.any():
                df.loc[invalid_open, 'Open'] = df.loc[invalid_open, 'Close']
            if invalid_close.any():
                df.loc[invalid_close, 'Close'] = df.loc[invalid_close, 'Open']
                
        return df
        
    def _validate_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """出来高の妥当性チェック"""
        if 'Volume' in df.columns:
            # 負の出来高を0に
            df.loc[df['Volume'] < 0, 'Volume'] = 0
            
            # 極端に大きな出来高を制限
            volume_99th = df['Volume'].quantile(0.99)
            if volume_99th > 0:
                df.loc[df['Volume'] > volume_99th * 10, 'Volume'] = volume_99th * 10
                
        return df
        
    def _get_cache_key(self, ticker: str, start_date: str, end_date: str) -> str:
        """キャッシュキーの生成"""
        return f"{ticker}_{start_date}_{end_date}.pkl"
        
    def _get_cache_path(self, ticker: str, start_date: str, end_date: str) -> Path:
        """キャッシュファイルパスの取得"""
        cache_key = self._get_cache_key(ticker, start_date, end_date)
        return self.cache_dir / cache_key
        
    def _load_from_cache(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """キャッシュからデータを読み込み"""
        cache_path = self._get_cache_path(ticker, start_date, end_date)
        
        if not cache_path.exists():
            return None
            
        # キャッシュの有効期限チェック
        cache_duration = self.data_config.get('cache_duration', 86400)  # 24時間
        cache_age = time.time() - cache_path.stat().st_mtime
        
        if cache_age > cache_duration:
            logger.debug(f"キャッシュ期限切れ: {ticker}")
            cache_path.unlink()
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            logger.warning(f"キャッシュ読み込み失敗: {ticker} - {e}")
            cache_path.unlink()
            return None
            
    def _save_to_cache(self, ticker: str, start_date: str, end_date: str, data: pd.DataFrame):
        """データをキャッシュに保存"""
        cache_path = self._get_cache_path(ticker, start_date, end_date)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"キャッシュ保存: {ticker}")
        except Exception as e:
            logger.warning(f"キャッシュ保存失敗: {ticker} - {e}")
            
    def get_multiple_tickers(self, tickers: List[str], start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """複数銘柄のデータを一括取得"""
        results = {}
        
        for ticker in tickers:
            try:
                data = self.get_ohlcv_data(ticker, start_date, end_date)
                if not data.empty:
                    results[ticker] = data
                else:
                    logger.warning(f"データ取得失敗: {ticker}")
            except Exception as e:
                logger.error(f"データ取得エラー: {ticker} - {e}")
                
        return results
        
    def clear_cache(self, older_than_days: int = 7):
        """古いキャッシュを削除"""
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            if cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
                deleted_count += 1
                
        logger.info(f"キャッシュクリア完了: {deleted_count}ファイル削除")
        
    def get_data_summary(self, ticker: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """データのサマリー情報を取得"""
        data = self.get_ohlcv_data(ticker, start_date, end_date)
        
        if data.empty:
            return {"ticker": ticker, "status": "no_data"}
            
        summary = {
            "ticker": ticker,
            "status": "success",
            "data_points": len(data),
            "date_range": {
                "start": data.index.min().strftime("%Y-%m-%d"),
                "end": data.index.max().strftime("%Y-%m-%d")
            },
            "price_stats": {
                "min_price": data['Close'].min(),
                "max_price": data['Close'].max(),
                "avg_price": data['Close'].mean(),
                "volatility": data['Close'].pct_change().std() * np.sqrt(252)
            },
            "volume_stats": {
                "avg_volume": data['Volume'].mean(),
                "max_volume": data['Volume'].max()
            }
        }
        
        return summary

# グローバルデータマネージャーインスタンス
data_manager = DataManager()
