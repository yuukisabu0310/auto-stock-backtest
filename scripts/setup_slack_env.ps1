# Slack通知環境変数設定スクリプト
# このスクリプトを実行してSlack通知の環境変数を設定してください

Write-Host "=== Slack通知環境変数設定 ===" -ForegroundColor Green

# 現在の設定を確認
Write-Host "`n現在の設定:" -ForegroundColor Yellow
Write-Host "SLACK_WEBHOOK_URL: $env:SLACK_WEBHOOK_URL"
Write-Host "SLACK_CHANNEL: $env:SLACK_CHANNEL"
Write-Host "SLACK_BOT_TOKEN: $env:SLACK_BOT_TOKEN"

# 設定方法の説明
Write-Host "`n=== 設定手順 ===" -ForegroundColor Cyan
Write-Host "1. Slack Appを作成し、Webhook URLを取得"
Write-Host "2. 以下のコマンドで環境変数を設定してください："
Write-Host ""

Write-Host "=== 設定コマンド ===" -ForegroundColor Yellow
Write-Host "# 一時的な設定（現在のセッションのみ）"
Write-Host '$env:SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"'
Write-Host '$env:SLACK_CHANNEL="#your-channel-name"'
Write-Host '$env:SLACK_BOT_TOKEN="xoxb-your-bot-token"'
Write-Host ""

Write-Host "# 永続的な設定（システム全体）"
Write-Host '[Environment]::SetEnvironmentVariable("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL", "User")'
Write-Host '[Environment]::SetEnvironmentVariable("SLACK_CHANNEL", "#your-channel-name", "User")'
Write-Host '[Environment]::SetEnvironmentVariable("SLACK_BOT_TOKEN", "xoxb-your-bot-token", "User")'
Write-Host ""

Write-Host "=== 推奨チャンネル名 ===" -ForegroundColor Yellow
Write-Host "#ai-improvements    - AI改善専用"
Write-Host "#trading-bot        - トレーディングボット全般"
Write-Host "#backtest-results   - バックテスト結果"
Write-Host "#alerts             - アラート全般"
Write-Host "#dev-notifications  - 開発通知"
Write-Host ""

Write-Host "=== テスト方法 ===" -ForegroundColor Yellow
Write-Host "環境変数設定後、以下のコマンドでテストしてください："
Write-Host "python scripts/notify_ai_improvement.py"
Write-Host ""

Write-Host "=== 注意事項 ===" -ForegroundColor Red
Write-Host "• Webhook URLは機密情報です。Gitにコミットしないでください"
Write-Host "• チャンネル名は # で始まる必要があります"
Write-Host "• Bot Tokenはオプションですが、より詳細な通知には必要です"
Write-Host ""

Write-Host "設定が完了したら、Enterキーを押してテストを実行してください..."
Read-Host

# テスト実行
if ($env:SLACK_WEBHOOK_URL -and $env:SLACK_CHANNEL) {
    Write-Host "`n=== テスト実行 ===" -ForegroundColor Green
    python scripts/notify_ai_improvement.py
} else {
    Write-Host "`n環境変数が設定されていません。先に設定してください。" -ForegroundColor Red
}
