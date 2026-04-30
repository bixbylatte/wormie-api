from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_auth import router as auth_router
from app.api.routes_books import router as books_router
from app.api.routes_requests import router as requests_router
from app.core.config import get_settings
from app.models import BookListing, ShareRequest, TradeRequestOffer, User  # noqa: F401

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(books_router, prefix=settings.api_prefix)
app.include_router(requests_router, prefix=settings.api_prefix)
if settings.storage_backend == "local":
    app.mount("/media", StaticFiles(directory=settings.cover_storage_dir), name="media")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
