param(
  [string]$Owner = "bixbylatte",
  [string]$Repo = "wormie-api",
  [string]$ProjectId = "wormie-ingenuity",
  [string]$ProjectNumber,
  [string]$Account = "bob.bbvillarin@gmail.com",
  [string]$Region = "asia-east1",
  [string]$ArtifactRepository = "wormie-api",
  [string]$ServiceName = "wormie-api",
  [string]$MigrationJobName = "wormie-api-migrate",
  [string]$WifPoolId = "github",
  [string]$WifProviderId = "github-actions",
  [string]$RuntimeServiceAccountName = "wormie-api-runtime",
  [string]$DeployerServiceAccountName = "wormie-api-deployer",
  [string]$CloudSqlInstanceConnectionName,
  [string]$GcsBucketName = "wormie-ingenuity-wormie-api-covers-prod",
  [string]$AllowedOrigins = "http://127.0.0.1:5173,http://localhost:5173",
  [string]$DatabaseUrlSecretName = "wormie-api-database-url",
  [string]$JwtSecretName = "wormie-api-jwt-secret"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectNumber) {
  $ProjectNumber = & gcloud projects describe $ProjectId --account $Account --format "value(projectNumber)"
}

if (-not $ProjectNumber) {
  throw "Could not resolve project number for '$ProjectId'. Re-authenticate gcloud first."
}

if (-not $CloudSqlInstanceConnectionName) {
  $CloudSqlInstanceConnectionName = "$ProjectId`:$Region`:wormie-pg"
}

$providerResource = "projects/$ProjectNumber/locations/global/workloadIdentityPools/$WifPoolId/providers/$WifProviderId"
$runtimeServiceAccount = "$RuntimeServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$deployerServiceAccount = "$DeployerServiceAccountName@$ProjectId.iam.gserviceaccount.com"

$vars = @{
  "GCP_PROJECT_ID" = $ProjectId
  "GCP_PROJECT_NUMBER" = $ProjectNumber
  "GCP_REGION" = $Region
  "ARTIFACT_REPOSITORY" = $ArtifactRepository
  "CLOUD_RUN_SERVICE" = $ServiceName
  "CLOUD_RUN_JOB" = $MigrationJobName
  "WIF_PROVIDER" = $providerResource
  "DEPLOYER_SERVICE_ACCOUNT" = $deployerServiceAccount
  "RUNTIME_SERVICE_ACCOUNT" = $runtimeServiceAccount
  "CLOUD_SQL_INSTANCE" = $CloudSqlInstanceConnectionName
  "GCS_BUCKET_NAME" = $GcsBucketName
  "API_ALLOWED_ORIGINS" = $AllowedOrigins
  "DATABASE_URL_SECRET_NAME" = $DatabaseUrlSecretName
  "JWT_SECRET_NAME" = $JwtSecretName
}

foreach ($item in $vars.GetEnumerator()) {
  & 'C:\Program Files\GitHub CLI\gh.exe' variable set $item.Key --repo "$Owner/$Repo" --body $item.Value
}

Write-Host ""
Write-Host "Configured GitHub Actions variables for $Owner/$Repo."
