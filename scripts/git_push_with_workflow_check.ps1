# Git Push with Workflow Check Script
# GitHubにプッシュした後にワークフローの実行状況をチェックするスクリプト

param(
    [string]$CommitMessage = "Auto commit and push with workflow check",
    [switch]$SkipWorkflowCheck = $false,
    [int]$WaitMinutes = 30
)

Write-Host "=== Git Push with Workflow Check ===" -ForegroundColor Cyan
Write-Host ""

# 1. Git ステータス確認
Write-Host "1. Git ステータス確認中..." -ForegroundColor Yellow
git status

# 変更があるかチェック
$hasChanges = git diff --name-only
if (-not $hasChanges) {
    Write-Host "変更がありません。スキップします。" -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# 2. 変更をステージング
Write-Host "2. 変更をステージング中..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ステージングに失敗しました" -ForegroundColor Red
    exit 1
}
Write-Host "ステージング完了" -ForegroundColor Green

# 3. コミット
Write-Host "3. コミット中..." -ForegroundColor Yellow
git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "コミットに失敗しました" -ForegroundColor Red
    exit 1
}
Write-Host "コミット完了" -ForegroundColor Green

# 4. プッシュ
Write-Host "4. GitHubにプッシュ中..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "プッシュに失敗しました" -ForegroundColor Red
    exit 1
}
Write-Host "プッシュ完了" -ForegroundColor Green

# 5. ワークフローチェック（スキップ指定がない場合）
if (-not $SkipWorkflowCheck) {
    Write-Host ""
    Write-Host "5. ワークフロー実行状況チェック中..." -ForegroundColor Yellow
    
    # 少し待機してワークフローが開始されるのを待つ
    Write-Host "ワークフロー開始を待機中... (10秒)" -ForegroundColor Gray
    Start-Sleep -Seconds 10
    
    # Pythonスクリプトを実行
    try {
        python -m scripts.check_workflows
        if ($LASTEXITCODE -eq 0) {
            Write-Host "全ワークフローが正常完了しました！" -ForegroundColor Green
        } else {
            Write-Host "一部のワークフローで問題が発生しました" -ForegroundColor Yellow
            Write-Host "詳細はログを確認してください" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "ワークフローチェック実行エラー: $_" -ForegroundColor Red
        Write-Host "手動でGitHub Actionsを確認してください" -ForegroundColor Yellow
    }
} else {
    Write-Host "ワークフローチェックをスキップしました" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== 完了 ===" -ForegroundColor Cyan
