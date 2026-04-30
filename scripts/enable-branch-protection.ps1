param(
  [string]$Owner = "bixbylatte",
  [string]$Repo = "wormie-api",
  [string]$Branch = "main",
  [string]$RequiredCheck = "ci",
  [int]$RequiredApprovingReviewCount = 0
)

$ErrorActionPreference = "Stop"

$payload = @{
  required_status_checks = @{
    strict = $true
    contexts = @($RequiredCheck)
  }
  enforce_admins = $true
  required_pull_request_reviews = @{
    dismiss_stale_reviews = $true
    require_code_owner_reviews = $false
    required_approving_review_count = [Math]::Max($RequiredApprovingReviewCount, 1)
    require_last_push_approval = $false
  }
  restrictions = $null
  required_linear_history = $true
  allow_force_pushes = $false
  allow_deletions = $false
  block_creations = $false
  required_conversation_resolution = $true
  lock_branch = $false
  allow_fork_syncing = $true
}

$payload = $payload | ConvertTo-Json -Depth 6

$tempFile = New-TemporaryFile
try {
  Set-Content -Path $tempFile -Value $payload -Encoding utf8
  & 'C:\Program Files\GitHub CLI\gh.exe' api `
    --method PUT `
    -H "Accept: application/vnd.github+json" `
    "/repos/$Owner/$Repo/branches/$Branch/protection" `
    --input $tempFile | Out-Null

  if ($RequiredApprovingReviewCount -le 0) {
    & 'C:\Program Files\GitHub CLI\gh.exe' api `
      --method DELETE `
      -H "Accept: application/vnd.github+json" `
      "/repos/$Owner/$Repo/branches/$Branch/protection/required_pull_request_reviews" | Out-Null
  }
}
finally {
  Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Branch protection is enabled for ${Owner}/${Repo}:$Branch."
