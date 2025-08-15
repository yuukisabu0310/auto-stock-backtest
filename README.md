# Auto Stock Backtest Bot (Enhanced Version)

このプロジェクトは、テクニカル指標やファンダメンタル条件を元に株式売買戦略を検証し、Slack通知まで自動化する仕組みです。  
GitHub Actionsを利用して、定期的に日本株・米国株を対象としたバックテストを実行します。

## 🚀 新機能・改善点

### **🤖 AI改善ループシステム**
- **自動改善提案**: パフォーマンス分析に基づくAI改善提案生成
- **検証モード/採用モード**: 安全な改善検証と本格導入の分離
- **改善履歴管理**: 全改善の履歴保存とロールバック機能
- **無限ループ防止**: 類似改善の検出と重複防止
- **Slack通知**: 改善結果と詳細レポートの自動通知

### **拡張性の高いアーキテクチャ**
- **設定ファイルベース**: `config.yaml`で全パラメータを管理
- **戦略ファクトリー**: 新しい戦略を簡単に追加可能
- **モジュラー設計**: 各機能が独立したモジュールとして実装

### **高度なデータ管理**
- **キャッシュ機能**: データ取得の高速化
- **品質チェック**: 異常値検出と自動修正
- **リトライ機能**: ネットワークエラーの自動復旧

### **包括的な評価指標**
- **基本指標**: シャープレシオ、ソルティノレシオ、カルマーレシオ
- **リスク指標**: VaR、CVaR、潰瘍指数
- **取引指標**: 勝率、利益因子、連続勝敗
- **安定性指標**: パラメータ安定性、正規性検定

### **強化されたリスク管理**
- **ポジションサイズ制御**: 資金の最大リスク割合制限
- **ストップロス/利確**: 自動損益管理
- **ドローダウン制限**: 最大損失制限
- **ボラティリティ調整**: ATRベースのポジションサイズ

### **詳細なログ・監視**
- **構造化ログ**: 詳細な実行ログとエラー追跡
- **ログローテーション**: 自動ログファイル管理
- **パフォーマンス監視**: 実行時間とリソース使用量

## 機能概要

- **株価データ取得**: yfinance を利用して日本株・米国株のOHLCVデータを取得
- **学習/検証分離**: 学習用銘柄はランダム抽出、検証用銘柄はランダム＋Slack指定銘柄
- **複数戦略対応**: `FixedSma` と `SmaCross` の2種類の売買戦略を並列評価
- **Walk-Forward 検証**: 過去データを分割して順次評価し、過学習を回避
- **Slack連携**: 実行結果やパラメータをSlackチャンネルに通知
- **GitHub Actions自動化**: 定期的にバックテストを実行し、レポートを出力

## 🚀 実行方法

### 動作確認（軽量設定）

動作確認時は軽量設定で素早くテストできます：

```powershell
# 動作確認モード設定
.\scripts\setup_test_mode.ps1

# バックテスト実行
python -m scripts.run_backtest_enhanced
```

**動作確認設定内容:**
- 期間: 2020-01-01 ～ 2023-12-31 (4年)
- 資金: $10,000
- 学習銘柄: 4銘柄
- 検証銘柄: 3銘柄
- 実行戦略: 全11戦略
- AI改善: 無効

### 本番実行（完全設定）

本番実行時は完全設定で詳細な分析を行います：

```powershell
# 本番モード設定
.\scripts\setup_production_mode.ps1

# バックテスト実行
python -m scripts.run_backtest_enhanced
```

**本番設定内容:**
- 期間: 2005-01-01 ～ 現在 (18年)
- 資金: $100,000
- 学習銘柄: 12銘柄
- 検証銘柄: 8銘柄
- 実行戦略: 全11戦略
- AI改善: 有効

### 従来の実行方法

従来の実行方法も引き続き利用可能です：

```bash
# 従来のバックテスト実行
python -m scripts.run_backtest

# 改善されたバックテスト実行
python -m scripts.run_backtest_enhanced
```

## ディレクトリ構成

```
.
├── scripts/
│   ├── run_backtest.py          # メイン実行スクリプト
│   ├── fetch_oos_from_slack.py  # Slackから検証銘柄を取得
│   ├── notify_slack.py          # Slack通知
│   └── make_index.py            # インデックス生成(オプション)
├── src/
│   ├── walkforward.py           # Walk-forward 検証ロジック
│   ├── strategies.py            # 売買戦略クラス (FixedSma, SmaCross等)
│   ├── metrics.py               # 評価指標計算
│   ├── report.py                # レポート出力
│   ├── sampler.py               # 層化ランダムサンプリング
│   ├── universe.py              # 銘柄リスト管理
├── .github/workflows/
│   └── backtest.yml             # GitHub Actions設定
└── README.md
```

## 必要環境

- Python 3.11+
- 必須パッケージ（`requirements.txt`参照）
- GitHub Actions 実行環境
- Slack Bot Token (通知用)

## セットアップ手順

1. **リポジトリ作成**  
   GitHubに新規リポジトリを作成し、本プロジェクトのファイルを配置。

2. **Slackアプリ作成**  
   - Slack API から新規アプリを作成
   - `chat:write` 権限を付与
   - Bot Tokenを発行し、GitHub Secretsに保存（例: `SLACK_BOT_TOKEN`）

3. **GitHub Secrets設定**  
   リポジトリ設定 → `Secrets and variables` → `Actions` にて以下を登録
   - `SLACK_BOT_TOKEN`: Slack Botのトークン
   - `SLACK_CHANNEL`: 通知先チャンネル名
   - `SLACK_WEBHOOK_URL`: Slack Webhook URL（AI改善通知用）
   - その他必要な環境変数（銘柄リスト、サンプル数など）

4. **ワークフロー有効化**  
   - `.github/workflows/backtest.yml` のスケジュールを設定し、自動実行を有効化
   - `.github/workflows/ai_improvement_loop.yml` のAI改善ループを有効化

5. **ローカルテスト（任意）**  
   ```bash
   python -m scripts.run_backtest_enhanced
   ```

## 実行結果

### **通常のバックテスト**
- 実行後、`reports/` フォルダに以下が生成されます
  - `{戦略名}_all_summary.csv` : 銘柄別検証結果一覧
  - `{戦略名}_params.txt` : ベストパラメータと実行条件
  - Slackに結果概要が通知されます

### **AI改善ループ**
- **改善提案**: `improvement_proposals.json`
- **テスト結果**: `test_results.json`
- **改善履歴**: `data/improvement_history.json`
- **履歴レポート**: `reports/improvement_history.html`
- **Slack通知**: 改善結果と詳細レポートが自動通知

## 注意事項

- yfinanceの仕様変更や銘柄コード不一致によりデータ取得に失敗する場合があります
- 日本株は `.T`（東証）を付与したコードを使用してください（例: `7203.T`）
- 学習データが不足している場合はスキップされます
- GitHub Actionsのストレージは一時的です。成果物を長期保存する場合は外部ストレージやSlackファイル送信を利用してください

## ライセンス

MIT License

## 更新履歴

- 2025-08-15: ドキュメント微修正（モバイルからのコミット検証）
