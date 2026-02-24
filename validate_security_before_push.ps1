# Pre-push validation script - Run this before git push
# Prevents accidental commits of sensitive data

Write-Host "[CHECK] Running pre-push security validation..." -ForegroundColor Cyan

$issues = @()
$warnings = @()

# Check 1: Is .env in git tracking?
Write-Host "  [1/5] Checking if .env is tracked by git..." -ForegroundColor Gray
$tracked = try { 
    & git ls-files | Select-String "^\\.env`$"
} catch { 
    $null 
}
if ($tracked) {
    $issues += ".env file is being tracked by git! This is a security risk."
}

# Check 2: Is .env in gitignore?
Write-Host "  [2/5] Verifying .env is in .gitignore..." -ForegroundColor Gray
$ignored = try {
    & git check-ignore ".env" 2>$null
} catch {
    $null
}
if (-not $ignored) {
    $issues += ".env is NOT in .gitignore! Add it immediately."
}

# Check 3: Are there API keys in commit history?
Write-Host "  [3/5] Scanning commit history for API key patterns..." -ForegroundColor Gray
$history = try {
    & git log --all --source -p -S "sk-or-v1-" 2>$null | Select-String "sk-or-v1-"
} catch {
    $null
}
if ($history) {
    $issues += "Found API key pattern in git history! This is critical."
}

# Check 4: Are there API keys in staged changes?
Write-Host "  [4/5] Checking staged files for secrets..." -ForegroundColor Gray
$staged = try {
    & git diff --cached -U0 2>$null | Select-String "sk-or-v1-"
} catch {
    $null
}
if ($staged) {
    $issues += "Found API key in staged files! Do NOT commit."
}

# Check 5: Are there API keys in uncommitted changes?
Write-Host "  [5/5] Checking working directory for secrets..." -ForegroundColor Gray
$uncommitted = try {
    & git diff -U0 2>$null | Select-String "sk-or-v1-"
} catch {
    $null
}
if ($uncommitted) {
    $warnings += "Found API key in uncommitted working changes (this is OK in .env file)"
}

# Report results
Write-Host ""
if ($issues.Count -gt 0) {
    Write-Host "[FAIL] SECURITY CHECKS FAILED" -ForegroundColor Red
    Write-Host ""
    foreach ($issue in $issues) {
        Write-Host "  [ERROR] $issue" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "DO NOT PUSH with these issues!" -ForegroundColor Red
    Write-Host ""
    exit 1
}

if ($warnings.Count -gt 0) {
    Write-Host "[WARN] WARNINGS" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "  [WARN] $warning" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "[OK] SECURITY CHECKS PASSED" -ForegroundColor Green
Write-Host "   .env is protected and not in git history" -ForegroundColor Green
Write-Host "   Safe to push to GitHub" -ForegroundColor Green
Write-Host ""
