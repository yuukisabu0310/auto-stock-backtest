# 動作確認用環境変数設定スクリプト
# このスクリプトを実行すると、動作確認用の軽量設定でバックテストが実行されます

Write-Host "=== 動作確認モード設定 ===" -ForegroundColor Green

# バックテスト基本設定（軽量）
$env:BACKTEST_START_DATE = "2020-01-01"
$env:BACKTEST_END_DATE = "2023-12-31"
$env:BACKTEST_CASH = "10000"
$env:BACKTEST_COMMISSION = "0.001"

# サンプリング設定（軽量）
$env:SAMPLE_SIZE = "4"
$env:OOS_RANDOM_SIZE = "3"

# AI改善有効化（テスト用）
$env:AI_IMPROVEMENT_ENABLED = "true"
$env:DYNAMIC_OPTIMIZATION_ENABLED = "true"

# 戦略パラメータ（軽量）
$env:FIXEDSMA_PERIODS = "[8, 20]"
$env:SMACROSS_FAST = "[20, 40]"
$env:SMACROSS_SLOW = "[50, 100]"

# 全戦略を有効化（12戦略）
$env:MA_BREAKOUT_ENABLED = "true"
$env:DONCHIAN_ENABLED = "true"
$env:RSI_MOMENTUM_ENABLED = "true"
$env:RSI_EXTREME_ENABLED = "true"
$env:BB_ENABLED = "true"
$env:SQUEEZE_ENABLED = "true"
$env:VOLUME_BREAKOUT_ENABLED = "true"
$env:OBV_ENABLED = "true"
$env:TREND_FOLLOWING_ENABLED = "true"  # 新しい戦略

Write-Host "動作確認モード設定完了！" -ForegroundColor Green
Write-Host ""
Write-Host "設定内容:" -ForegroundColor Yellow
Write-Host "  期間: 2020-01-01 ～ 2023-12-31 (4年)" -ForegroundColor White
Write-Host "  資金: $10,000" -ForegroundColor White
Write-Host "  学習銘柄: 4銘柄" -ForegroundColor White
Write-Host "  検証銘柄: 3銘柄" -ForegroundColor White
Write-Host "  実行戦略: 全12戦略（TrendFollowing追加）" -ForegroundColor White
Write-Host "  AI改善: 有効（テスト用）" -ForegroundColor White
Write-Host "  動的最適化: 有効" -ForegroundColor White
Write-Host ""
Write-Host "バックテスト実行コマンド:" -ForegroundColor Cyan
Write-Host "  python -m scripts.run_backtest_enhanced" -ForegroundColor White
Write-Host ""
Write-Host "本番モードに戻す場合は以下を実行:" -ForegroundColor Yellow
Write-Host "  .\scripts\setup_production_mode.ps1" -ForegroundColor White
