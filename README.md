# Wormie API

Backend service for Wormie. This repo is designed to stand on its own.

## Local setup

1. Run `.\scripts\setup.ps1`
2. Optional: run `.\scripts\seed-demo.ps1`
3. Start the API with `.\scripts\dev.ps1`
4. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Docker

```bash
docker build -t wormie-api .
docker run --rm -p 8000:8080 -e JWT_SECRET=replace-me-with-a-long-random-string wormie-api
```

## Cloud Run

Deploy this repo as its own Cloud Run service:

```powershell
.\scripts\deploy-cloud-run.ps1 -ProjectId wormie-ingenuity -Account bob.bbvillarin@gmail.com -JwtSecret "<long-random-secret>"
```

If the frontend is already deployed, pass its URL to `-AllowedOrigins` so browser requests are allowed from the web app.

## Notes

- Local storage uses `wormie.db` and `storage/covers/`.
- Cloud Run local storage is ephemeral, so SQLite and uploaded covers are only suitable for smoke tests and early demos.
