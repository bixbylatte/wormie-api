param(
  [string]$ProjectId = "wormie-ingenuity",
  [string]$Account = "bob.bbvillarin@gmail.com",
  [string]$Region = "asia-east1",
  [string]$GithubOwner = "bixbylatte",
  [string]$GithubRepo = "wormie-api",
  [string]$ArtifactRepository = "wormie-api",
  [string]$ServiceName = "wormie-api",
  [string]$MigrationJobName = "wormie-api-migrate",
  [string]$WifPoolId = "github",
  [string]$WifProviderId = "github-actions",
  [string]$RuntimeServiceAccountName = "wormie-api-runtime",
  [string]$DeployerServiceAccountName = "wormie-api-deployer",
  [string]$CloudSqlInstanceName = "wormie-pg",
  [string]$CloudSqlDatabaseVersion = "POSTGRES_16",
  [string]$CloudSqlDbName = "wormie_prod",
  [string]$CloudSqlUserName = "wormie_app",
  [string]$CloudSqlTierCpu = "1",
  [string]$CloudSqlTierMemory = "3840MiB",
  [string]$CloudSqlStorageSizeGb = "10",
  [string]$CloudSqlRootPassword,
  [string]$CloudSqlUserPassword,
  [switch]$RotateRuntimeSecrets,
  [string]$CoverBucketName = "wormie-ingenuity-wormie-api-covers-prod",
  [string]$JwtSecretName = "wormie-api-jwt-secret",
  [string]$DatabaseUrlSecretName = "wormie-api-database-url"
)

$ErrorActionPreference = "Stop"

function Get-RequiredValue {
  param(
    [string]$Value,
    [string]$Message
  )

  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw $Message
  }

  return $Value
}

function Invoke-Gcloud {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Args
  )

  & gcloud @Args --project $ProjectId --account $Account
  if ($LASTEXITCODE -ne 0) {
    throw "gcloud command failed: gcloud $($Args -join ' ') --project $ProjectId --account $Account"
  }
}

function Invoke-GcloudStorage {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Args
  )

  & gcloud storage @Args --project $ProjectId --account $Account
  if ($LASTEXITCODE -ne 0) {
    throw "gcloud storage command failed: gcloud storage $($Args -join ' ') --project $ProjectId --account $Account"
  }
}

function Ensure-ServiceAccount {
  param(
    [string]$Name,
    [string]$DisplayName
  )

  $lookup = Invoke-Gcloud -Args @("iam", "service-accounts", "list", "--filter", "email~^$Name@$ProjectId\\.iam\\.gserviceaccount\\.com$", "--format", "value(email)")
  if (-not $lookup) {
    Invoke-Gcloud -Args @("iam", "service-accounts", "create", $Name, "--display-name", $DisplayName) | Out-Null
  }
}

function Ensure-ProjectRoleBinding {
  param(
    [string]$Member,
    [string]$Role
  )

  Invoke-Gcloud -Args @("projects", "add-iam-policy-binding", $ProjectId, "--member", $Member, "--role", $Role, "--quiet") | Out-Null
}

function Ensure-BucketRoleBinding {
  param(
    [string]$BucketName,
    [string]$Member,
    [string]$Role
  )

  Invoke-GcloudStorage -Args @("buckets", "add-iam-policy-binding", "gs://$BucketName", "--member", $Member, "--role", $Role) | Out-Null
}

function Ensure-SecretAccessor {
  param(
    [string]$SecretName,
    [string]$Member
  )

  Invoke-Gcloud -Args @(
    "secrets", "add-iam-policy-binding", $SecretName,
    "--member", $Member,
    "--role", "roles/secretmanager.secretAccessor",
    "--quiet"
  ) | Out-Null
}

$ProjectNumber = Get-RequiredValue -Value (
  & gcloud projects describe $ProjectId --account $Account --format "value(projectNumber)"
) -Message "Could not access project '$ProjectId' with account '$Account'. Re-authenticate gcloud first."

if (-not $CloudSqlRootPassword) {
  $CloudSqlRootPassword = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
}

$RuntimeServiceAccountEmail = "$RuntimeServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$DeployerServiceAccountEmail = "$DeployerServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$WifPoolResource = "projects/$ProjectNumber/locations/global/workloadIdentityPools/$WifPoolId"
$WifProviderResource = "$WifPoolResource/providers/$WifProviderId"
$RepoPrincipal = "principalSet://iam.googleapis.com/$WifPoolResource/attribute.repository/$GithubOwner/$GithubRepo"

Invoke-Gcloud -Args @(
  "services", "enable",
  "artifactregistry.googleapis.com",
  "cloudbuild.googleapis.com",
  "iam.googleapis.com",
  "iamcredentials.googleapis.com",
  "run.googleapis.com",
  "secretmanager.googleapis.com",
  "sqladmin.googleapis.com",
  "sts.googleapis.com",
  "--quiet"
) | Out-Null

$repoLookup = Invoke-Gcloud -Args @("artifacts", "repositories", "list", "--location", $Region, "--filter", "name~/$ArtifactRepository$", "--format", "value(name)")
if (-not $repoLookup) {
  Invoke-Gcloud -Args @(
    "artifacts", "repositories", "create", $ArtifactRepository,
    "--repository-format", "docker",
    "--location", $Region,
    "--description", "Docker images for Wormie API"
  ) | Out-Null
}

Ensure-ServiceAccount -Name $RuntimeServiceAccountName -DisplayName "Wormie API runtime"
Ensure-ServiceAccount -Name $DeployerServiceAccountName -DisplayName "Wormie API deployer"

$poolLookup = Invoke-Gcloud -Args @("iam", "workload-identity-pools", "list", "--location", "global", "--filter", "name~/$WifPoolId$", "--format", "value(name)")
if (-not $poolLookup) {
  Invoke-Gcloud -Args @(
    "iam", "workload-identity-pools", "create", $WifPoolId,
    "--location", "global",
    "--display-name", "GitHub Actions Pool"
  ) | Out-Null
}

$providerLookup = Invoke-Gcloud -Args @("iam", "workload-identity-pools", "providers", "list", "--location", "global", "--workload-identity-pool", $WifPoolId, "--filter", "name~/$WifProviderId$", "--format", "value(name)")
if (-not $providerLookup) {
  Invoke-Gcloud -Args @(
    "iam", "workload-identity-pools", "providers", "create-oidc", $WifProviderId,
    "--location", "global",
    "--workload-identity-pool", $WifPoolId,
    "--display-name", "GitHub Actions Provider",
    "--issuer-uri", "https://token.actions.githubusercontent.com",
    "--attribute-mapping", "google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner",
    "--attribute-condition", "assertion.repository_owner == '$GithubOwner'"
  ) | Out-Null
}

Invoke-Gcloud -Args @(
  "iam", "service-accounts", "add-iam-policy-binding", $DeployerServiceAccountEmail,
  "--role", "roles/iam.workloadIdentityUser",
  "--member", $RepoPrincipal,
  "--quiet"
) | Out-Null

Ensure-ProjectRoleBinding -Member "serviceAccount:$DeployerServiceAccountEmail" -Role "roles/run.admin"
Ensure-ProjectRoleBinding -Member "serviceAccount:$DeployerServiceAccountEmail" -Role "roles/artifactregistry.writer"
Invoke-Gcloud -Args @(
  "iam", "service-accounts", "add-iam-policy-binding", $RuntimeServiceAccountEmail,
  "--member", "serviceAccount:$DeployerServiceAccountEmail",
  "--role", "roles/iam.serviceAccountUser",
  "--quiet"
) | Out-Null

Ensure-ProjectRoleBinding -Member "serviceAccount:$RuntimeServiceAccountEmail" -Role "roles/cloudsql.client"

$instanceLookup = Invoke-Gcloud -Args @("sql", "instances", "list", "--filter", "name:$CloudSqlInstanceName", "--format", "value(name)")
if (-not $instanceLookup) {
  if (-not $CloudSqlUserPassword) {
    $CloudSqlUserPassword = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
  }
  Invoke-Gcloud -Args @(
    "sql", "instances", "create", $CloudSqlInstanceName,
    "--database-version", $CloudSqlDatabaseVersion,
    "--edition", "enterprise",
    "--cpu", $CloudSqlTierCpu,
    "--memory", $CloudSqlTierMemory,
    "--region", $Region,
    "--root-password", $CloudSqlRootPassword,
    "--availability-type", "zonal",
    "--backup-start-time", "03:00",
    "--storage-type", "SSD",
    "--storage-size", $CloudSqlStorageSizeGb,
    "--storage-auto-increase",
    "--deletion-protection",
    "--server-ca-mode", "GOOGLE_MANAGED_INTERNAL_CA",
    "--assign-ip"
  ) | Out-Null
}

$databaseLookup = Invoke-Gcloud -Args @("sql", "databases", "list", "--instance", $CloudSqlInstanceName, "--filter", "name:$CloudSqlDbName", "--format", "value(name)")
if (-not $databaseLookup) {
  Invoke-Gcloud -Args @("sql", "databases", "create", $CloudSqlDbName, "--instance", $CloudSqlInstanceName) | Out-Null
}

$userLookup = Invoke-Gcloud -Args @("sql", "users", "list", "--instance", $CloudSqlInstanceName, "--filter", "name:$CloudSqlUserName", "--format", "value(name)")
if (-not $userLookup) {
  if (-not $CloudSqlUserPassword) {
    $CloudSqlUserPassword = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
  }
  Invoke-Gcloud -Args @("sql", "users", "create", $CloudSqlUserName, "--instance", $CloudSqlInstanceName, "--password", $CloudSqlUserPassword) | Out-Null
}
elseif ($RotateRuntimeSecrets) {
  if (-not $CloudSqlUserPassword) {
    $CloudSqlUserPassword = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
  }
  Invoke-Gcloud -Args @("sql", "users", "set-password", $CloudSqlUserName, "--instance", $CloudSqlInstanceName, "--password", $CloudSqlUserPassword) | Out-Null
}

$instanceConnectionName = Get-RequiredValue -Value (
  Invoke-Gcloud -Args @("sql", "instances", "describe", $CloudSqlInstanceName, "--format", "value(connectionName)")
) -Message "Cloud SQL instance connection name was not returned."

$bucketExists = $true
try {
  Invoke-GcloudStorage -Args @("buckets", "describe", "gs://$CoverBucketName") | Out-Null
}
catch {
  $bucketExists = $false
}

if (-not $bucketExists) {
  Invoke-GcloudStorage -Args @(
    "buckets", "create", "gs://$CoverBucketName",
    "--location", $Region,
    "--uniform-bucket-level-access",
    "--no-public-access-prevention",
    "--soft-delete-duration", "0"
  ) | Out-Null
}

Ensure-BucketRoleBinding -BucketName $CoverBucketName -Member "serviceAccount:$RuntimeServiceAccountEmail" -Role "roles/storage.objectAdmin"
Ensure-BucketRoleBinding -BucketName $CoverBucketName -Member "allUsers" -Role "roles/storage.objectViewer"

$jwtSecretLookup = Invoke-Gcloud -Args @("secrets", "list", "--filter", "name~/$JwtSecretName$", "--format", "value(name)")
if (-not $jwtSecretLookup) {
  Invoke-Gcloud -Args @("secrets", "create", $JwtSecretName, "--replication-policy", "automatic") | Out-Null
}

$databaseSecretLookup = Invoke-Gcloud -Args @("secrets", "list", "--filter", "name~/$DatabaseUrlSecretName$", "--format", "value(name)")
if (-not $databaseSecretLookup) {
  Invoke-Gcloud -Args @("secrets", "create", $DatabaseUrlSecretName, "--replication-policy", "automatic") | Out-Null
}

$jwtVersionLookup = Invoke-Gcloud -Args @("secrets", "versions", "list", $JwtSecretName, "--format", "value(name)", "--limit", "1")
$databaseVersionLookup = Invoke-Gcloud -Args @("secrets", "versions", "list", $DatabaseUrlSecretName, "--format", "value(name)", "--limit", "1")

if ($RotateRuntimeSecrets -or -not $jwtVersionLookup) {
  $jwtSecretValue = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
  $jwtTempFile = New-TemporaryFile
  try {
    Set-Content -Path $jwtTempFile -Value $jwtSecretValue -NoNewline
    Invoke-Gcloud -Args @("secrets", "versions", "add", $JwtSecretName, "--data-file", $jwtTempFile) | Out-Null
  }
  finally {
    Remove-Item -LiteralPath $jwtTempFile -Force -ErrorAction SilentlyContinue
  }
}

if ($RotateRuntimeSecrets -or -not $databaseVersionLookup) {
  if (-not $CloudSqlUserPassword) {
    $CloudSqlUserPassword = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
    Invoke-Gcloud -Args @("sql", "users", "set-password", $CloudSqlUserName, "--instance", $CloudSqlInstanceName, "--password", $CloudSqlUserPassword) | Out-Null
  }

  $dbConnectionString = "postgresql+psycopg://${CloudSqlUserName}:${CloudSqlUserPassword}@/${CloudSqlDbName}?host=/cloudsql/${instanceConnectionName}"
  $dbTempFile = New-TemporaryFile
  try {
    Set-Content -Path $dbTempFile -Value $dbConnectionString -NoNewline
    Invoke-Gcloud -Args @("secrets", "versions", "add", $DatabaseUrlSecretName, "--data-file", $dbTempFile) | Out-Null
  }
  finally {
    Remove-Item -LiteralPath $dbTempFile -Force -ErrorAction SilentlyContinue
  }
}

Ensure-SecretAccessor -SecretName $JwtSecretName -Member "serviceAccount:$RuntimeServiceAccountEmail"
Ensure-SecretAccessor -SecretName $DatabaseUrlSecretName -Member "serviceAccount:$RuntimeServiceAccountEmail"

Write-Host ""
Write-Host "Wormie API GCP foundation is ready."
Write-Host "Project number: $ProjectNumber"
Write-Host "Workload Identity Provider: $WifProviderResource"
Write-Host "Runtime service account: $RuntimeServiceAccountEmail"
Write-Host "Deployer service account: $DeployerServiceAccountEmail"
Write-Host "Cloud SQL instance connection: $instanceConnectionName"
Write-Host "Cloud Storage bucket: gs://$CoverBucketName"
Write-Host "Secrets: $JwtSecretName, $DatabaseUrlSecretName"
