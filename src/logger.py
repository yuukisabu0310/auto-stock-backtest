"""
ログ管理モジュール
詳細なログ機能とエラー追跡を提供します
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import traceback
from src.config import config

class BacktestLogger:
    """バックテスト専用のログ管理クラス"""
    
    def __init__(self, name: str = "backtest"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.setup_logger()
        
    def setup_logger(self):
        """ログ設定を初期化"""
        log_config = config.get_logging_config()
        
        # ログレベルを設定
        level = getattr(logging, log_config.get('level', 'INFO').upper())
        self.logger.setLevel(level)
        
        # 既存のハンドラーをクリア
        self.logger.handlers.clear()
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # ファイルハンドラー
        log_file = log_config.get('file', 'logs/backtest.log')
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ローテーティングファイルハンドラー
        max_size = self._parse_size(log_config.get('max_size', '10MB'))
        backup_count = log_config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
    def _parse_size(self, size_str: str) -> int:
        """サイズ文字列をバイト数に変換"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
            
    def info(self, message: str):
        """情報ログ"""
        self.logger.info(message)
        
    def warning(self, message: str):
        """警告ログ"""
        self.logger.warning(message)
        
    def error(self, message: str, exc_info: bool = True):
        """エラーログ"""
        self.logger.error(message, exc_info=exc_info)
        
    def debug(self, message: str):
        """デバッグログ"""
        self.logger.debug(message)
        
    def critical(self, message: str, exc_info: bool = True):
        """重大エラーログ"""
        self.logger.critical(message, exc_info=exc_info)
        
    def log_data_fetch(self, ticker: str, success: bool, data_points: int = 0, error: str = ""):
        """データ取得ログ"""
        if success:
            self.info(f"データ取得成功: {ticker} ({data_points}件)")
        else:
            self.error(f"データ取得失敗: {ticker} - {error}")
            
    def log_strategy_execution(self, strategy_name: str, ticker: str, params: dict, success: bool):
        """戦略実行ログ"""
        if success:
            self.info(f"戦略実行成功: {strategy_name} - {ticker} - パラメータ: {params}")
        else:
            self.error(f"戦略実行失敗: {strategy_name} - {ticker} - パラメータ: {params}")
            
    def log_parameter_optimization(self, strategy_name: str, best_params: dict, score: float):
        """パラメータ最適化ログ"""
        self.info(f"パラメータ最適化完了: {strategy_name} - 最適パラメータ: {best_params} - スコア: {score:.4f}")
        
    def log_backtest_completion(self, strategy_name: str, total_tickers: int, successful_tickers: int):
        """バックテスト完了ログ"""
        success_rate = (successful_tickers / total_tickers * 100) if total_tickers > 0 else 0
        self.info(f"バックテスト完了: {strategy_name} - 成功率: {success_rate:.1f}% ({successful_tickers}/{total_tickers})")
        
    def log_error_with_context(self, error: Exception, context: str = ""):
        """コンテキスト付きエラーログ"""
        error_msg = f"エラー発生: {context} - {type(error).__name__}: {str(error)}"
        self.error(error_msg)
        
    def log_performance_metrics(self, strategy_name: str, ticker: str, metrics: dict):
        """パフォーマンス指標ログ"""
        sharpe = metrics.get('sharpe_ratio', 'N/A')
        return_pct = metrics.get('total_return', 'N/A')
        max_dd = metrics.get('max_drawdown', 'N/A')
        self.info(f"パフォーマンス: {strategy_name} - {ticker} - Sharpe: {sharpe:.3f}, Return: {return_pct:.2f}%, MaxDD: {max_dd:.2f}%")

# グローバルロガーインスタンス
logger = BacktestLogger()

def get_logger(name: str = None) -> BacktestLogger:
    """ロガーインスタンスを取得"""
    if name:
        return BacktestLogger(name)
    return logger
