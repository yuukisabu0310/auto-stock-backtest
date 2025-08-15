# GitHub Token Setup Script
# GitHubワークフローチェック用のトークン設定スクリプト

Write-Host "=== GitHub Token Setup ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "GitHubワークフローチェック機能を使用するには、GitHub Personal Access Tokenが必要です。" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. GitHub Personal Access Tokenの作成方法:" -ForegroundColor Green
Write-Host "   - GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)" -ForegroundColor Gray
Write-Host "   - 'Generate new token (classic)' をクリック" -ForegroundColor Gray
Write-Host "   - 必要な権限:" -ForegroundColor Gray
Write-Host "     ✓ repo (Full control of private repositories)" -ForegroundColor Gray
Write-Host "     ✓ workflow (Update GitHub Action workflows)" -ForegroundColor Gray
Write-Host "     ✓ actions (Read and write permissions in Actions)" -ForegroundColor Gray
Write-Host ""

Write-Host "2. 環境変数の設定:" -ForegroundColor Green
Write-Host "   以下のコマンドを実行してトークンを設定してください:" -ForegroundColor Gray
Write-Host ""

$token = Read-Host "GitHub Personal Access Tokenを入力してください" -AsSecureString
$tokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))

if ($tokenPlain) {
    # 環境変数として設定
    [Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $tokenPlain, "User")
    
    # 現在のセッションにも設定
    $env:GITHUB_TOKEN = $tokenPlain
    
    Write-Host ""
    Write-Host "✅ GitHub Tokenが設定されました" -ForegroundColor Green
    Write-Host "環境変数: GITHUB_TOKEN" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "❌ トークンが入力されませんでした" -ForegroundColor Red
    exit 1
}

# リポジトリ情報の設定
Write-Host ""
Write-Host "3. リポジトリ情報の設定:" -ForegroundColor Green

$repoOwner = Read-Host "GitHubユーザー名またはOrganization名を入力してください"
$repoName = Read-Host "リポジトリ名を入力してください (例: auto-stock-backtest)"

if ($repoOwner -and $repoName) {
    # 環境変数として設定
    [Environment]::SetEnvironmentVariable("GITHUB_REPOSITORY_OWNER", $repoOwner, "User")
    [Environment]::SetEnvironmentVariable("GITHUB_REPOSITORY_NAME", $repoName, "User")
    
    # 現在のセッションにも設定
    $env:GITHUB_REPOSITORY_OWNER = $repoOwner
    $env:GITHUB_REPOSITORY_NAME = $repoName
    
    Write-Host ""
    Write-Host "✅ リポジトリ情報が設定されました" -ForegroundColor Green
    Write-Host "リポジトリ: $repoOwner/$repoName" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "⚠️ リポジトリ情報が不完全です" -ForegroundColor Yellow
    Write-Host "手動で環境変数を設定してください:" -ForegroundColor Gray
    Write-Host "  GITHUB_REPOSITORY_OWNER=your-username" -ForegroundColor Gray
    Write-Host "  GITHUB_REPOSITORY_NAME=auto-stock-backtest" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== 設定完了 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用方法:" -ForegroundColor Green
Write-Host "  .\scripts\git_push_with_workflow_check.ps1" -ForegroundColor Gray
Write-Host "  .\scripts\git_push_with_workflow_check.ps1 -CommitMessage 'カスタムメッセージ'" -ForegroundColor Gray
Write-Host "  .\scripts\git_push_with_workflow_check.ps1 -SkipWorkflowCheck" -ForegroundColor Gray
Write-Host ""
Write-Host "手動チェック:" -ForegroundColor Green
Write-Host "  python -m scripts.check_workflows" -ForegroundColor Gray
