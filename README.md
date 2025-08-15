# Auto Stock Backtest

自動株式バックテストシステム

## 概要

このプロジェクトは、複数のトレーディング戦略を使用した自動株式バックテストシステムです。Walk-Forward Optimization (WFO) を使用して過学習を防ぎ、AI改善ループシステムにより自動的に戦略を最適化します。

## 機能

### 基本機能
- 複数のトレーディング戦略のバックテスト
- Walk-Forward Optimization (WFO)
- 包括的な評価指標
- HTMLレポート生成

### 拡張版機能
- **AI改善ループシステム**: 自動的な戦略最適化
- **多様な戦略**: 12種類のトレーディング戦略
- **リスク管理**: 統合されたリスク管理機能
- **設定管理**: 環境変数による動的設定
- **ログ機能**: 構造化されたログシステム
- **データ管理**: キャッシュ機能付きデータ取得

### AI改善ループシステム
- **検証モード**: 別ブランチでテスト、成功時のみマージ
- **採用モード**: 成功時自動的にmainブランチにマージ
- **改善履歴**: 全改善の履歴管理とロールバック機能
- **無限ループ防止**: 類似改善の検出
- **Slack通知**: 改善結果と詳細の通知
- **自動PR作成**: 検証モードでの自動PR作成

## 実行方法

### 動作確認モード（推奨）
```powershell
# 動作確認モード設定
.\scripts\setup_test_mode.ps1

# バックテスト実行
python -m scripts.run_backtest_enhanced
```

### 本番モード
```powershell
# 本番モード設定
.\scripts\setup_production_mode.ps1

# バックテスト実行
python -m scripts.run_backtest_enhanced
```

### GitHub Push with Workflow Check
```powershell
# 初回設定（GitHub Token設定）
.\scripts\setup_github_token.ps1

# プッシュとワークフローチェック
.\scripts\git_push_with_workflow_check.ps1

# カスタムメッセージ付き
.\scripts\git_push_with_workflow_check.ps1 -CommitMessage "機能追加: 新戦略実装"

# ワークフローチェックをスキップ
.\scripts\git_push_with_workflow_check.ps1 -SkipWorkflowCheck
```

## 戦略一覧

### 基本戦略
1. **FixedSma**: 固定SMA戦略
2. **SmaCross**: SMAクロス戦略

### 追加戦略
3. **MovingAverageBreakout**: 移動平均ブレイクアウト
4. **DonchianChannel**: ドンチャンチャンネル
5. **MACDStrategy**: MACD戦略
6. **RSIMomentum**: RSIモメンタム
7. **RSIExtreme**: RSI極値
8. **BollingerBands**: ボリンジャーバンド
9. **SqueezeStrategy**: スクイーズ戦略
10. **VolumeBreakout**: ボリュームブレイクアウト
11. **OBVStrategy**: OBV戦略

## 設定

### 環境変数
- `BACKTEST_START_DATE`: バックテスト開始日
- `BACKTEST_END_DATE`: バックテスト終了日
- `BACKTEST_CASH`: 初期資金
- `SAMPLE_SIZE`: サンプルサイズ
- `AI_IMPROVEMENT_ENABLED`: AI改善有効/無効

### Slack通知設定
```bash
# AI改善専用
SLACK_WEBHOOK_URL_AI_IMPROVEMENT=https://hooks.slack.com/services/...

# バックテスト結果
SLACK_WEBHOOK_URL_BACKTEST_RESULTS=https://hooks.slack.com/services/...

# 開発通知
SLACK_WEBHOOK_URL_DEV_NOTIFICATIONS=https://hooks.slack.com/services/...
```

## ファイル構成

```
auto-stock-backtest/
├── README.md
├── requirements.txt
├── config.yaml
├── scripts/
│   ├── run_backtest.py
│   ├── run_backtest_enhanced.py
│   ├── check_workflows.py
│   ├── git_push_with_workflow_check.ps1
│   ├── setup_github_token.ps1
│   ├── setup_test_mode.ps1
│   └── setup_production_mode.ps1
├── src/
│   ├── config.py
│   ├── logger.py
│   ├── data_manager.py
│   ├── strategy_base.py
│   ├── enhanced_metrics.py
│   ├── improvement_history.py
│   ├── ai_improver.py
│   └── walkforward.py
├── .github/workflows/
│   ├── backtest.yml
│   └── ai_improvement_loop.yml
├── reports/
├── data/
└── logs/
```

## GitHub Actions

### Daily Backtest
- 毎日自動実行
- 全戦略のバックテスト
- 結果をSlackに通知

### AI Improvement Loop
- 検証モード: 毎日自動実行
- 採用モード: 手動実行
- 改善提案生成・テスト・評価
- 成功時自動マージ

## ワークフローチェック機能

プッシュ後にワークフローの実行状況を自動チェックします：

```powershell
# 手動チェック
python -m scripts.check_workflows

# 自動チェック付きプッシュ
.\scripts\git_push_with_workflow_check.ps1
```

### チェック対象
- Daily Backtest
- AI Improvement Loop

### 機能
- ワークフロー実行状況の監視
- 完了待機（最大30分）
- 成功/失敗の判定
- 詳細レポート生成

## インストール

```bash
pip install -r requirements.txt
```

## 使用方法

1. 設定ファイル `config.yaml` を編集
2. 環境変数を設定（必要に応じて）
3. バックテストを実行
4. 結果を確認

## ライセンス

MIT License
