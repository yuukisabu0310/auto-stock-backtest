import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from dataclasses import dataclass, asdict
from enum import Enum

from src.config import config
from src.logger import get_logger

logger = get_logger("improvement_history")

class ImprovementMode(Enum):
    VERIFICATION = "verification"
    ADOPTION = "adoption"

@dataclass
class ImprovementRecord:
    """改善記録のデータクラス"""
    id: str
    timestamp: str
    mode: str
    strategy_name: str
    old_params: Dict[str, Any]
    new_params: Dict[str, Any]
    performance_metrics: Dict[str, float]
    improvement_score: float
    description: str
    branch_name: str
    commit_hash: str
    status: str  # "pending", "success", "failed", "adopted", "rejected"
    rollback_to: Optional[str] = None

class ImprovementHistoryManager:
    """改善履歴を管理するクラス"""
    
    def __init__(self, history_file: str = "data/improvement_history.json"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[ImprovementRecord] = []
        self.load_history()
    
    def load_history(self):
        """履歴ファイルから改善記録を読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [ImprovementRecord(**record) for record in data]
                logger.info(f"改善履歴を読み込みました: {len(self.history)}件")
            except Exception as e:
                logger.error(f"履歴ファイルの読み込みエラー: {e}")
                self.history = []
        else:
            self.history = []
    
    def save_history(self):
        """改善記録を履歴ファイルに保存"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(record) for record in self.history], f, 
                         indent=2, ensure_ascii=False, default=str)
            logger.info("改善履歴を保存しました")
        except Exception as e:
            logger.error(f"履歴ファイルの保存エラー: {e}")
    
    def _generate_id(self, strategy_name: str, params: Dict[str, Any]) -> str:
        """改善記録のIDを生成"""
        param_str = json.dumps(params, sort_keys=True)
        content = f"{strategy_name}_{param_str}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def add_improvement(self, 
                       mode: ImprovementMode,
                       strategy_name: str,
                       old_params: Dict[str, Any],
                       new_params: Dict[str, Any],
                       performance_metrics: Dict[str, float],
                       improvement_score: float,
                       description: str,
                       branch_name: str,
                       commit_hash: str) -> str:
        """新しい改善記録を追加"""
        
        improvement_id = self._generate_id(strategy_name, new_params)
        
        record = ImprovementRecord(
            id=improvement_id,
            timestamp=datetime.now().isoformat(),
            mode=mode.value,
            strategy_name=strategy_name,
            old_params=old_params,
            new_params=new_params,
            performance_metrics=performance_metrics,
            improvement_score=improvement_score,
            description=description,
            branch_name=branch_name,
            commit_hash=commit_hash,
            status="pending"
        )
        
        self.history.append(record)
        self.save_history()
        
        logger.info(f"改善記録を追加: {improvement_id} ({strategy_name})")
        return improvement_id
    
    def update_status(self, improvement_id: str, status: str):
        """改善記録のステータスを更新"""
        for record in self.history:
            if record.id == improvement_id:
                record.status = status
                self.save_history()
                logger.info(f"改善記録のステータスを更新: {improvement_id} -> {status}")
                return
        logger.warning(f"改善記録が見つかりません: {improvement_id}")
    
    def get_latest_improvement(self, strategy_name: str) -> Optional[ImprovementRecord]:
        """指定戦略の最新改善記録を取得"""
        strategy_records = [r for r in self.history if r.strategy_name == strategy_name]
        if strategy_records:
            return max(strategy_records, key=lambda x: x.timestamp)
        return None
    
    def get_adopted_improvements(self, strategy_name: str) -> List[ImprovementRecord]:
        """採用された改善記録を取得"""
        return [r for r in self.history 
                if r.strategy_name == strategy_name and r.status == "adopted"]
    
    def check_similar_improvements(self, 
                                 strategy_name: str, 
                                 new_params: Dict[str, Any], 
                                 threshold: float = 0.9) -> List[ImprovementRecord]:
        """類似の改善履歴をチェック（無限ループ防止）"""
        similar_records = []
        
        for record in self.history:
            if record.strategy_name != strategy_name:
                continue
            
            similarity = self._calculate_param_similarity(record.new_params, new_params)
            if similarity >= threshold:
                similar_records.append(record)
        
        return similar_records
    
    def _calculate_param_similarity(self, params1: Dict[str, Any], params2: Dict[str, Any]) -> float:
        """パラメータの類似度を計算"""
        if not params1 or not params2:
            return 0.0
        
        # 共通のキーを取得
        common_keys = set(params1.keys()) & set(params2.keys())
        if not common_keys:
            return 0.0
        
        # 数値パラメータの類似度を計算
        similarities = []
        for key in common_keys:
            val1 = params1[key]
            val2 = params2[key]
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # 数値の場合は相対的な差を計算
                if val1 == 0 and val2 == 0:
                    similarity = 1.0
                elif val1 == 0 or val2 == 0:
                    similarity = 0.0
                else:
                    diff = abs(val1 - val2) / max(abs(val1), abs(val2))
                    similarity = 1.0 - min(diff, 1.0)
            else:
                # その他の場合は完全一致かどうか
                similarity = 1.0 if val1 == val2 else 0.0
            
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def get_improvement_summary(self) -> Dict[str, Any]:
        """改善履歴のサマリーを取得"""
        if not self.history:
            return {"total": 0, "strategies": {}}
        
        summary = {
            "total": len(self.history),
            "strategies": {},
            "recent_improvements": []
        }
        
        # 戦略別の統計
        for record in self.history:
            strategy = record.strategy_name
            if strategy not in summary["strategies"]:
                            summary["strategies"][strategy] = {
                "total": 0,
                "adopted": 0,
                "failed": 0,
                "pending": 0,
                "success": 0,
                "best_score": float('-inf')
            }
            
            summary["strategies"][strategy]["total"] += 1
            summary["strategies"][strategy][record.status] += 1
            summary["strategies"][strategy]["best_score"] = max(
                summary["strategies"][strategy]["best_score"], 
                record.improvement_score
            )
        
        # 最近の改善（最新10件）
        recent = sorted(self.history, key=lambda x: x.timestamp, reverse=True)[:10]
        summary["recent_improvements"] = [
            {
                "id": r.id,
                "strategy": r.strategy_name,
                "timestamp": r.timestamp,
                "status": r.status,
                "score": r.improvement_score
            }
            for r in recent
        ]
        
        return summary
    
    def can_rollback(self, strategy_name: str) -> bool:
        """ロールバック可能かチェック"""
        adopted_records = self.get_adopted_improvements(strategy_name)
        return len(adopted_records) > 1  # 最低2つの採用記録が必要
    
    def get_rollback_target(self, strategy_name: str) -> Optional[ImprovementRecord]:
        """ロールバック対象の改善記録を取得（最新の採用記録の前の記録）"""
        adopted_records = self.get_adopted_improvements(strategy_name)
        if len(adopted_records) < 2:
            return None
        
        # 採用記録を時系列順にソート
        sorted_adopted = sorted(adopted_records, key=lambda x: x.timestamp)
        return sorted_adopted[-2]  # 最新の前の記録
    
    def export_history_report(self, output_file: str = "reports/improvement_history.html"):
        """改善履歴のレポートを生成"""
        summary = self.get_improvement_summary()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>改善履歴レポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .strategy {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .record {{ margin: 5px 0; padding: 5px; background: #f9f9f9; }}
                .status-adopted {{ color: green; }}
                .status-failed {{ color: red; }}
                .status-pending {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>改善履歴レポート</h1>
            <div class="summary">
                <h2>サマリー</h2>
                <p>総改善回数: {summary['total']}</p>
                <p>対象戦略数: {len(summary['strategies'])}</p>
            </div>
            
            <h2>戦略別統計</h2>
            {self._generate_strategy_summary_html(summary['strategies'])}
            
            <h2>最近の改善</h2>
            {self._generate_recent_improvements_html(summary['recent_improvements'])}
            
            <h2>詳細履歴</h2>
            {self._generate_detailed_history_html()}
        </body>
        </html>
        """
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"改善履歴レポートを生成: {output_file}")

    def _generate_strategy_summary_html(self, strategies: Dict[str, Any]) -> str:
        """戦略別サマリーのHTML生成"""
        html = ""
        for strategy, stats in strategies.items():
            html += f"""
            <div class="strategy">
                <h3>{strategy}</h3>
                <p>総改善回数: {stats['total']}</p>
                <p>採用: {stats['adopted']} | 失敗: {stats['failed']} | 保留: {stats['pending']}</p>
                <p>最高スコア: {stats['best_score']:.4f}</p>
            </div>
            """
        return html
    
    def _generate_recent_improvements_html(self, recent: List[Dict[str, Any]]) -> str:
        """最近の改善のHTML生成"""
        html = ""
        for record in recent:
            status_class = f"status-{record['status']}"
            html += f"""
            <div class="record">
                <span class="{status_class}">{record['status']}</span>
                {record['strategy']} - {record['timestamp']} (スコア: {record['score']:.4f})
            </div>
            """
        return html
    
    def _generate_detailed_history_html(self) -> str:
        """詳細履歴のHTML生成"""
        html = ""
        for record in sorted(self.history, key=lambda x: x.timestamp, reverse=True):
            status_class = f"status-{record.status}"
            html += f"""
            <div class="record">
                <h4>ID: {record.id} - {record.strategy_name}</h4>
                <p><span class="{status_class}">{record.status}</span> | {record.timestamp}</p>
                <p>説明: {record.description}</p>
                <p>スコア: {record.improvement_score:.4f}</p>
                <p>ブランチ: {record.branch_name}</p>
            </div>
            """
        return html

# グローバルインスタンス
improvement_history = ImprovementHistoryManager()
