param(
  [string]$Owner = "bixbylatte",
  [string]$Repo = "wormie-api",
  [string]$Branch = "main",
  [string]$RequiredCheck = "ci"
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
    required_approving_review_count = 1
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
} | ConvertTo-Json -Depth 6

$tempFile = New-TemporaryFile
$repoSettingsFile = New-TemporaryFile
try {
  [System.IO.File]::WriteAllText(
    $tempFile,
    $payload,
    [System.Text.UTF8Encoding]::new($false)
  )

  $repoSettingsPayload = @{
    allow_squash_merge = $true
    allow_merge_commit = $false
    allow_rebase_merge = $false
  } | ConvertTo-Json -Depth 4

  [System.IO.File]::WriteAllText(
    $repoSettingsFile,
    $repoSettingsPayload,
    [System.Text.UTF8Encoding]::new($false)
  )

  & 'C:\Program Files\GitHub CLI\gh.exe' api `
    --method PUT `
    -H "Accept: application/vnd.github+json" `
    -H "X-GitHub-Api-Version: 2022-11-28" `
    "/repos/$Owner/$Repo/branches/$Branch/protection" `
    --input $tempFile | Out-Null

  if ($LASTEXITCODE -ne 0) {
    throw "gh api failed with exit code $LASTEXITCODE"
  }

  & 'C:\Program Files\GitHub CLI\gh.exe' api `
    --method PATCH `
    -H "Accept: application/vnd.github+json" `
    -H "X-GitHub-Api-Version: 2022-11-28" `
    "/repos/$Owner/$Repo" `
    --input $repoSettingsFile | Out-Null

  if ($LASTEXITCODE -ne 0) {
    throw "gh api failed with exit code $LASTEXITCODE"
  }
}
finally {
  Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $repoSettingsFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Branch protection and squash-only merge settings are enabled for ${Owner}/${Repo}:$Branch."
