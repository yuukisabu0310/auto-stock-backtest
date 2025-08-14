"""
設定管理モジュール
設定ファイルの読み込みと環境変数の処理を行います
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

class ConfigManager:
    """設定ファイルと環境変数を管理するクラス"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()
        
    def load_config(self):
        """設定ファイルを読み込み、環境変数を展開"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            
        # 環境変数を展開
        config_content = self._expand_environment_variables(config_content)
        
        # YAMLとして解析
        self.config = yaml.safe_load(config_content)
        
    def _expand_environment_variables(self, content: str) -> str:
        """文字列内の環境変数を展開"""
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(0)
            env_value = os.getenv(var_name)
            
            if env_value is None:
                # デフォルト値がある場合（${VAR:-default}形式）
                if ':-' in var_name:
                    var_name, default = var_name.split(':-', 1)
                    env_value = os.getenv(var_name, default)
                else:
                    return default_value
            
            # 数値型の環境変数を適切に変換
            if env_value.lower() in ['true', 'false']:
                return env_value.lower()
            elif env_value.lower() == 'null':
                return 'null'
            elif env_value.startswith('[') and env_value.endswith(']'):
                # リスト形式の場合はそのまま返す（YAMLが自動解析）
                return env_value
            else:
                # 数値の場合はそのまま返す（YAMLが自動変換）
                return env_value
            
        import re
        return re.sub(r'\$\{([^}]+)\}', replace_var, content)
        
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得（ドット記法対応）"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def get_backtest_config(self) -> Dict[str, Any]:
        """バックテスト設定を取得"""
        return self.config.get('backtest', {})
        
    def get_strategies_config(self) -> Dict[str, Any]:
        """戦略設定を取得"""
        return self.config.get('strategies', {})
        
    def get_universe_config(self) -> Dict[str, Any]:
        """銘柄リスト設定を取得"""
        return self.config.get('universe', {})
        
    def get_metrics_config(self) -> Dict[str, Any]:
        """評価指標設定を取得"""
        return self.config.get('metrics', {})
        
    def get_logging_config(self) -> Dict[str, Any]:
        """ログ設定を取得"""
        return self.config.get('logging', {})
        
    def get_notifications_config(self) -> Dict[str, Any]:
        """通知設定を取得"""
        return self.config.get('notifications', {})
        
    def get_output_config(self) -> Dict[str, Any]:
        """出力設定を取得"""
        return self.config.get('output', {})
        
    def get_enabled_strategies(self) -> List[str]:
        """有効な戦略のリストを取得"""
        strategies = self.get_strategies_config()
        return [name for name, config in strategies.items() 
                if config.get('enabled', False)]
                
    def get_strategy_params(self, strategy_name: str) -> Dict[str, Any]:
        """指定戦略のパラメータを取得"""
        strategies = self.get_strategies_config()
        if strategy_name not in strategies:
            raise ValueError(f"戦略 '{strategy_name}' が見つかりません")
        return strategies[strategy_name].get('parameters', {})
        
    def get_risk_management_config(self, strategy_name: str) -> Dict[str, Any]:
        """指定戦略のリスク管理設定を取得"""
        strategies = self.get_strategies_config()
        if strategy_name not in strategies:
            return {}
        return strategies[strategy_name].get('risk_management', {})
        
    def validate_config(self) -> List[str]:
        """設定の妥当性を検証"""
        errors = []
        
        # 必須設定のチェック
        required_sections = ['backtest', 'strategies', 'universe']
        for section in required_sections:
            if section not in self.config:
                errors.append(f"必須セクション '{section}' が見つかりません")
                
        # バックテスト設定の検証
        backtest = self.get_backtest_config()
        if not backtest.get('start_date'):
            errors.append("start_date が設定されていません")
            
        # 戦略設定の検証
        strategies = self.get_strategies_config()
        if not strategies:
            errors.append("有効な戦略が設定されていません")
            
        return errors

# グローバル設定インスタンス
config = ConfigManager()
