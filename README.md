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
.\scripts\configure-github-repo.ps1
```

### Manual fallback deploy

Deploy this repo manually as its own Cloud Run service:

```powershell
.\scripts\deploy-cloud-run.ps1 `
  -ProjectId wormie-ingenuity `
  -Account bob.bbvillarin@gmail.com `
  -RuntimeServiceAccount "wormie-api-runtime@wormie-ingenuity.iam.gserviceaccount.com" `
  -CloudSqlInstance "wormie-ingenuity:asia-east1:wormie-pg" `
  -GcsBucketName "wormie-ingenuity-wormie-api-covers-prod" `
  -AllowedOrigins "http://127.0.0.1:5173,http://localhost:5173" `
  -AllowUnauthenticated
```

### Protect `main`

Once CI has run successfully at least once, protect the production branch:

```powershell
.\scripts\enable-branch-protection.ps1
```

## Notes

- Local development still defaults to `wormie.db` and `storage/covers/`.
- Production should use Cloud SQL and Cloud Storage only.
- Production `cover_url` values should resolve to public `https://storage.googleapis.com/<bucket>/<object-key>` URLs.
- Public HTTPS deployments now reject `STORAGE_BACKEND=local` at startup to avoid broken ephemeral cover uploads on Cloud Run.
- `GCS_PUBLIC_BASE_URL` remains reserved for future CDN/custom-domain work and is not part of the current production URL contract.
- `seed_demo.py` intentionally supports local storage only.
- PRs validate tests and Docker build. Pushes to `main` deploy production.
