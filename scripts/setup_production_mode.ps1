# 本番モード環境変数設定スクリプト
# このスクリプトを実行すると、本番用の完全設定でバックテストが実行されます

Write-Host "=== 本番モード設定 ===" -ForegroundColor Green

# バックテスト基本設定（本番）
$env:BACKTEST_START_DATE = "2005-01-01"
$env:BACKTEST_END_DATE = "null"
$env:BACKTEST_CASH = "100000"
$env:BACKTEST_COMMISSION = "0.002"

# サンプリング設定（本番）
$env:SAMPLE_SIZE = "12"
$env:OOS_RANDOM_SIZE = "8"

# AI改善有効化
$env:AI_IMPROVEMENT_ENABLED = "true"

# 戦略パラメータ（本番）
$env:FIXEDSMA_PERIODS = "[8, 18, 30, 50]"
$env:SMACROSS_FAST = "[15, 30, 40]"
$env:SMACROSS_SLOW = "[45, 60, 80, 100]"

# 全戦略を有効化
$env:MA_BREAKOUT_ENABLED = "true"
$env:DONCHIAN_ENABLED = "true"
$env:RSI_MOMENTUM_ENABLED = "true"
$env:RSI_EXTREME_ENABLED = "true"
$env:BB_ENABLED = "true"
$env:SQUEEZE_ENABLED = "true"
$env:VOLUME_BREAKOUT_ENABLED = "true"
$env:OBV_ENABLED = "true"

Write-Host "本番モード設定完了！" -ForegroundColor Green
Write-Host ""
Write-Host "設定内容:" -ForegroundColor Yellow
Write-Host "  期間: 2005-01-01 ～ 現在 (18年)" -ForegroundColor White
Write-Host "  資金: $100,000" -ForegroundColor White
Write-Host "  学習銘柄: 12銘柄" -ForegroundColor White
Write-Host "  検証銘柄: 8銘柄" -ForegroundColor White
Write-Host "  実行戦略: 全11戦略" -ForegroundColor White
Write-Host "  AI改善: 有効" -ForegroundColor White
Write-Host ""
Write-Host "バックテスト実行コマンド:" -ForegroundColor Cyan
Write-Host "  python -m scripts.run_backtest_enhanced" -ForegroundColor White
Write-Host ""
Write-Host "動作確認モードに戻す場合は以下を実行:" -ForegroundColor Yellow
Write-Host "  .\scripts\setup_test_mode.ps1" -ForegroundColor White
