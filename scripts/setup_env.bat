@echo off
REM GitHubワークフローチェック用環境変数設定

echo Setting up GitHub environment variables...

REM 環境変数を設定（トークンは手動で設定してください）
set GITHUB_REPOSITORY_OWNER=yuukisabu0310
set GITHUB_REPOSITORY_NAME=auto-stock-backtest

echo Environment variables set successfully!
echo.
echo Please set GITHUB_TOKEN manually:
echo   set GITHUB_TOKEN=your_token_here
echo.
echo Usage:
echo   python -m scripts.check_workflows
echo.
