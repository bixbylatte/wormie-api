param(
  [string]$ProjectId = "wormie-ingenuity",
  [string]$Account = "bob.bbvillarin@gmail.com",
  [string]$Region = "asia-east1",
  [string]$Repository = "wormie-api",
  [string]$ServiceName = "wormie-api",
  [string]$MigrationJobName = "wormie-api-migrate",
  [string]$RuntimeServiceAccount,
  [string]$CloudSqlInstance,
  [string]$DatabaseUrlSecretName = "wormie-api-database-url",
  [string]$JwtSecretName = "wormie-api-jwt-secret",
  [string]$GcsBucketName,
  [string]$AllowedOrigins,
  [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

if (-not $RuntimeServiceAccount) {
  throw "Provide -RuntimeServiceAccount with the API Cloud Run runtime service account email."
}
if (-not $CloudSqlInstance) {
  throw "Provide -CloudSqlInstance with the Cloud SQL instance connection name."
}
if (-not $GcsBucketName) {
  throw "Provide -GcsBucketName with the production cover bucket."
}
if (-not $AllowedOrigins) {
  throw "Provide -AllowedOrigins with the production web origin and any allowed localhost origins."
}

& gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com sqladmin.googleapis.com `
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
$imageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/${ServiceName}:$imageTag"
$secretRefs = "DATABASE_URL=${DatabaseUrlSecretName}:latest,JWT_SECRET=${JwtSecretName}:latest"
$envFile = New-TemporaryFile

try {
  @"
STORAGE_BACKEND: "gcs"
GCS_BUCKET_NAME: "$GcsBucketName"
ALLOWED_ORIGINS: "$AllowedOrigins"
"@ | Set-Content -Path $envFile -Encoding utf8

  & gcloud builds submit `
    --tag $imageUri `
    --project $ProjectId `
    --account $Account `
    .

  & gcloud run jobs deploy $MigrationJobName `
    --image $imageUri `
    --region $Region `
    --project $ProjectId `
    --account $Account `
    --service-account $RuntimeServiceAccount `
    --cpu 1 `
    --memory 1Gi `
    --task-timeout 10m `
    --max-retries 0 `
    --tasks 1 `
    --parallelism 1 `
    --set-cloudsql-instances $CloudSqlInstance `
    --set-secrets $secretRefs `
    --env-vars-file $envFile `
    --command alembic `
    --args upgrade,head `
    --execute-now `
    --wait

  $deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $imageUri,
    "--region", $Region,
    "--platform", "managed",
    "--project", $ProjectId,
    "--account", $Account,
    "--service-account", $RuntimeServiceAccount,
    "--memory", "1Gi",
    "--cpu", "1",
    "--concurrency", "40",
    "--min-instances", "0",
    "--execution-environment", "gen2",
    "--set-cloudsql-instances", $CloudSqlInstance,
    "--set-secrets", $secretRefs,
    "--env-vars-file", $envFile
  )

  if ($AllowUnauthenticated) {
    $deployArgs += "--allow-unauthenticated"
  }
  else {
    $deployArgs += "--no-allow-unauthenticated"
  }

  & gcloud @deployArgs

  $serviceUrl = & gcloud run services describe $ServiceName `
    --region $Region `
    --project $ProjectId `
    --account $Account `
    --format "value(status.url)"

  Invoke-WebRequest -Uri "$serviceUrl/health" -UseBasicParsing | Out-Null

  Write-Host ""
  Write-Host "Deployed $ServiceName to Cloud Run."
  Write-Host "Image: $imageUri"
  Write-Host "Service URL: $serviceUrl"
}
finally {
  Remove-Item -LiteralPath $envFile -Force -ErrorAction SilentlyContinue
}
