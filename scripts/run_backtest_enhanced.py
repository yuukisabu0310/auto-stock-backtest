"""
改善されたバックテスト実行スクリプト
設定ファイルベースで拡張性の高いバックテストシステム
"""

import os
import sys
import random
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.logger import get_logger
from src.data_manager import data_manager
from src.strategy_base import StrategyFactory
from src.enhanced_metrics import enhanced_metrics
from src.walkforward import run_walk_forward_fixed
from src.report import save_outputs, summarize
from src.universe import split_universe
from src.sampler import stratified_sample

logger = get_logger("backtest_runner")

class EnhancedBacktestRunner:
    """改善されたバックテスト実行クラス"""
    
    def __init__(self):
        self.backtest_config = config.get_backtest_config()
        self.strategies_config = config.get_strategies_config()
        self.universe_config = config.get_universe_config()
        self.output_config = config.get_output_config()
        
        # 設定の検証
        self._validate_config()
        
    def _validate_config(self):
        """設定の妥当性を検証"""
        errors = config.validate_config()
        if errors:
            for error in errors:
                logger.error(f"設定エラー: {error}")
            raise ValueError("設定ファイルにエラーがあります")
            
        logger.info("設定ファイルの検証完了")
        
    def run_backtest(self):
        """メインのバックテスト実行"""
        start_time = time.time()
        logger.info("バックテスト開始")
        
        try:
            # 銘柄リストの準備
            learn_list, oos_list = self._prepare_universe()
            
            # データの取得
            price_cache = self._load_data(learn_list + oos_list)
            
            # 有効な戦略の取得
            enabled_strategies = config.get_enabled_strategies()
            logger.info(f"実行戦略: {enabled_strategies}")
            
            # 戦略ごとの実行
            for strategy_name in enabled_strategies:
                logger.info(f"戦略 {strategy_name} の処理開始")
                self._run_strategy(strategy_name, learn_list, oos_list, price_cache)
                
            # 実行時間の記録
            execution_time = time.time() - start_time
            logger.info(f"バックテスト完了: {execution_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"バックテスト実行エラー: {e}")
            raise
            
    def _prepare_universe(self) -> Tuple[List[str], List[str]]:
        """銘柄リストの準備"""
        # 環境変数から追加銘柄を取得
        extra_tickers = os.getenv("EXTRA_TICKERS", "")
        extra_list = [t.strip() for t in extra_tickers.split(",") if t.strip()]
        
        # Slackから固定OOS銘柄を取得
        fixed_oos = os.getenv("OOS_FIXED_TICKERS", "")
        fixed_list = [t.strip() for t in fixed_oos.split(",") if t.strip()]
        
        # 銘柄リストの分割
        non_ai, ai = split_universe(extra_list)
        
        # サンプリング設定
        sample_size = self.backtest_config.get('sampling', {}).get('sample_size', 12)
        oos_random_size = self.backtest_config.get('sampling', {}).get('oos_random_size', 8)
        
        # シード設定
        seed = os.getenv("RANDOM_SEED", "")
        if seed:
            try:
                random.seed(int(seed))
            except:
                random.seed(seed)
        else:
            random.seed(pd.Timestamp.today().date().toordinal())
            
        # 学習用銘柄の選択
        learn_pool = sorted(set(non_ai) - set(fixed_list))
        learn_list = stratified_sample(learn_pool, sample_size, seed=random.random())
        
        # 検証用銘柄の選択
        oos_pool = sorted(set(learn_pool) - set(learn_list) - set(fixed_list))
        rand_oos = stratified_sample(oos_pool, oos_random_size, seed=random.random())
        oos_all = sorted(set(rand_oos).union(set(fixed_list)))
        
        logger.info(f"学習銘柄: {learn_list}")
        logger.info(f"検証銘柄（固定）: {fixed_list}")
        logger.info(f"検証銘柄（ランダム）: {rand_oos}")
        
        return learn_list, oos_all
        
    def _load_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """データの一括取得"""
        logger.info(f"データ取得開始: {len(tickers)}銘柄")
        
        # データ取得設定
        start_date = self.backtest_config.get('start_date', '2005-01-01')
        end_date = self.backtest_config.get('end_date')
        
        # 並列処理でデータ取得
        with Pool(min(max(1, cpu_count() - 1), 6)) as pool:
            args = [(ticker, start_date, end_date) for ticker in tickers]
            results = pool.starmap(self._load_single_ticker, args)
            
        # 結果を辞書に変換
        price_cache = {}
        for ticker, data in zip(tickers, results):
            if not data.empty:
                price_cache[ticker] = data
                
        logger.info(f"データ取得完了: {len(price_cache)}銘柄成功")
        return price_cache
        
    def _load_single_ticker(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """単一銘柄のデータ取得"""
        try:
            return data_manager.get_ohlcv_data(ticker, start_date, end_date)
        except Exception as e:
            logger.error(f"データ取得エラー {ticker}: {e}")
            return pd.DataFrame()
            
    def _run_strategy(self, strategy_name: str, learn_list: List[str], 
                     oos_list: List[str], price_cache: Dict[str, pd.DataFrame]):
        """個別戦略の実行"""
        try:
            # 戦略パラメータの取得
            strategy_params = config.get_strategy_params(strategy_name)
            
            # パラメータの組み合わせを生成
            param_combinations = self._generate_param_combinations(strategy_params)
            
            # 学習データでのパラメータ最適化
            best_params, best_score = self._optimize_parameters(
                strategy_name, learn_list, price_cache, param_combinations
            )
            
            if best_params is None:
                logger.error(f"パラメータ最適化失敗: {strategy_name}")
                return
                
            logger.info(f"最適パラメータ: {strategy_name} - {best_params} (スコア: {best_score:.4f})")
            
            # 検証データでの評価
            self._evaluate_strategy(strategy_name, oos_list, price_cache, best_params)
            
        except Exception as e:
            logger.error(f"戦略実行エラー {strategy_name}: {e}")
            
    def _generate_param_combinations(self, params: Dict[str, List]) -> List[Dict[str, Any]]:
        """パラメータの組み合わせを生成"""
        import itertools
        
        # パラメータ名と値のリストを取得
        param_names = list(params.keys())
        param_values = list(params.values())
        
        # 全組み合わせを生成
        combinations = []
        for values in itertools.product(*param_values):
            combination = dict(zip(param_names, values))
            combinations.append(combination)
            
        return combinations
        
    def _optimize_parameters(self, strategy_name: str, learn_list: List[str], 
                           price_cache: Dict[str, pd.DataFrame], 
                           param_combinations: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
        """パラメータの最適化"""
        logger.info(f"パラメータ最適化開始: {strategy_name} - {len(param_combinations)}組み合わせ")
        
        best_params = None
        best_score = -1e9
        
        # 並列処理でパラメータ評価
        with Pool(min(max(1, cpu_count() - 1), 6)) as pool:
            args = [(strategy_name, learn_list, price_cache, params) 
                   for params in param_combinations]
            results = pool.starmap(self._evaluate_parameters, args)
            
        # 最良のパラメータを選択
        for params, score in zip(param_combinations, results):
            if score > best_score:
                best_score = score
                best_params = params
                
        return best_params, best_score
        
    def _evaluate_parameters(self, strategy_name: str, learn_list: List[str], 
                           price_cache: Dict[str, pd.DataFrame], 
                           params: Dict[str, Any]) -> float:
        """パラメータの評価"""
        try:
            # 戦略クラスの取得
            strategy_class = StrategyFactory.get_strategy(strategy_name)
            
            # 各銘柄での評価
            scores = []
            for ticker in learn_list:
                if ticker not in price_cache:
                    continue
                    
                data = price_cache[ticker]
                if data.empty or len(data) < 20:
                    continue
                    
                # Walk-Forward検証（戦略に応じてパラメータを変換）
                wf_params = self._convert_params_for_walkforward(strategy_name, params)
                res_df, _ = run_walk_forward_fixed(
                    data, strategy_class=strategy_class, ticker=ticker, **wf_params
                )
                
                if not res_df.empty:
                    # 評価指標の計算
                    metrics = self._calculate_metrics_from_results(res_df)
                    score = enhanced_metrics.calculate_robust_score(metrics)
                    scores.append(score)
                    
            # 平均スコアを返す
            return np.mean(scores) if scores else -1e9
            
        except Exception as e:
            logger.error(f"パラメータ評価エラー: {e}")
            return -1e9
            
    def _evaluate_strategy(self, strategy_name: str, oos_list: List[str], 
                          price_cache: Dict[str, pd.DataFrame], 
                          best_params: Dict[str, Any]):
        """戦略の最終評価"""
        logger.info(f"戦略評価開始: {strategy_name}")
        
        # 出力ディレクトリの作成
        output_dir = Path("reports") / strategy_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 戦略クラスの取得
        strategy_class = StrategyFactory.get_strategy(strategy_name)
        
        # 各銘柄での評価
        results = []
        for ticker in oos_list:
            if ticker not in price_cache:
                continue
                
            data = price_cache[ticker]
            if data.empty or len(data) < 20:
                continue
                
            try:
                # Walk-Forward検証（戦略に応じてパラメータを変換）
                wf_params = self._convert_params_for_walkforward(strategy_name, best_params)
                res_df, equity = run_walk_forward_fixed(
                    data, strategy_class=strategy_class, ticker=ticker, **wf_params
                )
                
                if not res_df.empty:
                    # 結果の保存
                    save_outputs(f"{ticker}_OOS", res_df, equity, str(output_dir))
                    
                    # サマリーの作成
                    summary = summarize(res_df)
                    summary.update({
                        'ticker': ticker,
                        'strategy': strategy_name,
                        'params': best_params
                    })
                    results.append(summary)
                    
            except Exception as e:
                logger.error(f"銘柄評価エラー {ticker}: {e}")
                
        # 結果の保存
        if results:
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_dir / "_all_summary.csv", index=False)
            
            # パラメータファイルの保存
            self._save_parameters(output_dir, strategy_name, best_params)
            
            logger.info(f"戦略評価完了: {strategy_name} - {len(results)}銘柄")
            
    def _calculate_metrics_from_results(self, res_df: pd.DataFrame) -> Dict[str, float]:
        """結果から評価指標を計算"""
        if res_df.empty:
            return {}
            
        # 基本的な指標を計算
        metrics = {
            'sharpe_ratio': res_df.get('Sharpe Ratio', pd.Series([0])).median(),
            'total_return': res_df.get('Return [%]', pd.Series([0])).median(),
            'max_drawdown': res_df.get('Max. Drawdown [%]', pd.Series([0])).median(),
        }
        
        return metrics
        
    def _convert_params_for_walkforward(self, strategy_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """戦略に応じてパラメータをWalk-Forward用に変換"""
        if strategy_name == 'FixedSma':
            # FixedSma戦略: sma_period -> n_fast, n_slow
            sma_period = params.get('sma_period', 20)
            return {'n_fast': sma_period, 'n_slow': sma_period}
        elif strategy_name == 'SmaCross':
            # SmaCross戦略: n_fast, n_slowをそのまま使用
            return {k: v for k, v in params.items() if k in ['n_fast', 'n_slow']}
        else:
            # その他の戦略: デフォルト値
            return {'n_fast': 10, 'n_slow': 20}
            
    def _save_parameters(self, output_dir: Path, strategy_name: str, params: Dict[str, Any]):
        """パラメータファイルの保存"""
        param_file = output_dir / "_params.txt"
        
        with open(param_file, 'w', encoding='utf-8') as f:
            f.write(f"Strategy: {strategy_name}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\nParameters:\n")
            for key, value in params.items():
                f.write(f"{key} = {value}\n")
                
        logger.info(f"パラメータ保存: {param_file}")

def main():
    """メイン実行関数"""
    try:
        # バックテスト実行
        runner = EnhancedBacktestRunner()
        runner.run_backtest()
        
        logger.info("バックテスト正常完了")
        
    except Exception as e:
        logger.error(f"バックテスト失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
