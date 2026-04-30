# Wormie API

Backend service for Wormie. This repo is designed to stand on its own.

## Local setup

1. Run `.\scripts\setup.ps1`
2. Optional: run `.\scripts\seed-demo.ps1`
3. Start the API with `.\scripts\dev.ps1`
4. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

`.\scripts\setup.ps1` now installs dependencies and applies Alembic migrations locally.

## Docker

```bash
docker build -t wormie-api .
docker run --rm -p 8000:8080 -e JWT_SECRET=replace-me-with-a-long-random-string wormie-api
```

## Cloud Run

This repo is production-ready for a container-based Cloud Run deployment with:

- Alembic migrations
- PostgreSQL via `DATABASE_URL`
- Cloud Storage-backed cover uploads through `STORAGE_BACKEND=gcs`
- Secret Manager for runtime secrets
- GitHub Actions deployment from `main`

### Bootstrap GCP

Create the production foundation once:

```powershell
.\scripts\bootstrap-gcp.ps1
```

Before you run it, attach an active billing account to the `wormie-ingenuity` project. Cloud Run, Artifact Registry, Cloud SQL, and Secret Manager cannot be enabled without billing.

That script creates or updates:

- Artifact Registry repo `wormie-api`
- runtime and deployer service accounts
- GitHub Workload Identity Federation pool/provider
- Cloud SQL PostgreSQL instance, database, and app user
- Cloud Storage bucket for covers
- Secret Manager secrets for JWT and `DATABASE_URL`

### Configure GitHub Actions

After GCP bootstrap, configure repository variables:

```powershell
.\scripts\configure-github-repo.ps1 -WebServiceName "wormie-web"
```

That resolves both public Cloud Run URLs for the `wormie-web` service and adds them to `API_ALLOWED_ORIGINS` alongside localhost origins.

### Manual fallback deploy

Deploy this repo manually as its own Cloud Run service:

```powershell
.\scripts\deploy-cloud-run.ps1 `
  -ProjectId wormie-ingenuity `
  -Account bob.bbvillarin@gmail.com `
  -RuntimeServiceAccount "wormie-api-runtime@wormie-ingenuity.iam.gserviceaccount.com" `
  -CloudSqlInstance "wormie-ingenuity:asia-east1:wormie-pg" `
  -GcsBucketName "wormie-ingenuity-wormie-api-covers-prod" `
  -WebServiceName "wormie-web" `
  -AllowUnauthenticated
```

### Protect `main`

Once CI has run successfully at least once, protect the production branch:

```powershell
.\scripts\enable-branch-protection.ps1
```

That script also configures the repository to use squash merges only.

## PR To Production

Production changes should flow through GitHub only:

1. Branch from `main`.
2. Open a PR and wait for the `ci` workflow to pass.
3. Get one approval and resolve review comments.
4. Squash merge to `main`.
5. Let `deploy-prod` publish to Cloud Run automatically.

If a change spans both repos, merge and deploy `wormie-api` first, then merge `wormie-web` after the API deployment smoke checks pass.

## Notes

- Local development still defaults to `wormie.db` and `storage/covers/`.
- Production should use Cloud SQL and Cloud Storage only.
- `seed_demo.py` intentionally supports local storage only.
- Cloud Run assigns two public URLs to a service. CORS needs to allow both the regional `...asia-east1.run.app` URL and the `...a.run.app` URL for the web service.
- PRs validate tests and Docker build. Pushes to `main` deploy production.
- Use `workflow_dispatch` as break-glass only. Avoid direct `gcloud` production hotfixes; if one is unavoidable, merge the matching repo fix immediately after.
