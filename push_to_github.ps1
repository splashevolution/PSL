# push_to_github.ps1
# Run from D:\Projects\Products\sanskrit_sandbox\

$ErrorActionPreference = "Stop"

$REPO_URL = "https://github.com/splashevolution/paninian-systems-language.git"

Write-Host "=== Initialising git repo ===" -ForegroundColor Cyan
git init -b main
git config user.name "Praveen Kumar"
git config user.email "pravkr@hotmail.com"

Write-Host "=== Adding remote ===" -ForegroundColor Cyan
git remote add origin $REPO_URL

Write-Host "=== Staging all files ===" -ForegroundColor Cyan
git add .

Write-Host "=== Creating initial commit ===" -ForegroundColor Cyan
git commit -m "Initial release: PSL v1.0 - 15 proof sprints, 206 checks, Lean 4 formal proof"

Write-Host "=== Pushing to GitHub ===" -ForegroundColor Cyan
git push -u origin main

Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "Repo live at: https://github.com/splashevolution/paninian-systems-language" -ForegroundColor Green
