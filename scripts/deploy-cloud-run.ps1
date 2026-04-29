$ErrorActionPreference = "Stop"

param(
  [string]$ProjectId = "wormie-ingenuity",
  [string]$Account = "bob.bbvillarin@gmail.com",
  [string]$ServiceName = "wormie-api",
  [string]$Region = "asia-east1",
  [string]$Repository = "wormie-api",
  [string]$JwtSecret,
  [string]$AllowedOrigins = "",
  [switch]$AllowUnauthenticated
)

if (-not $JwtSecret) {
  throw "Provide -JwtSecret with a long random value before deploying."
}

$projectNumber = & gcloud projects describe $ProjectId --account $Account --format="value(projectNumber)"
if (-not $projectNumber) {
  throw "Could not access project '$ProjectId' with account '$Account'. Run 'gcloud auth login $Account' first, or confirm the project id."
}

& gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com `
  --project $ProjectId `
  --account $Account

$repositoryLookup = & gcloud artifacts repositories list `
  --project $ProjectId `
  --account $Account `
  --location $Region `
  --filter "name~/$Repository$" `
  --format "value(name)"

if (-not $repositoryLookup) {
  & gcloud artifacts repositories create $Repository `
    --repository-format docker `
    --location $Region `
    --description "Docker images for Wormie API" `
    --project $ProjectId `
    --account $Account
}

$imageTag = Get-Date -Format "yyyyMMdd-HHmmss"
$imageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ServiceName:$imageTag"

& gcloud builds submit `
  --tag $imageUri `
  --project $ProjectId `
  --account $Account `
  .

$envVars = @("JWT_SECRET=$JwtSecret")
if ($AllowedOrigins) {
  $envVars += "ALLOWED_ORIGINS=$AllowedOrigins"
}

$deployArgs = @(
  "run", "deploy", $ServiceName,
  "--image", $imageUri,
  "--region", $Region,
  "--platform", "managed",
  "--project", $ProjectId,
  "--account", $Account,
  "--set-env-vars", ($envVars -join ",")
)

if ($AllowUnauthenticated) {
  $deployArgs += "--allow-unauthenticated"
}
else {
  $deployArgs += "--no-allow-unauthenticated"
}

& gcloud @deployArgs

Write-Host ""
Write-Host "Deployed $ServiceName to Cloud Run."
Write-Host "Image: $imageUri"
