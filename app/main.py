import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config import Settings, get_settings
from app.container import Container
from app.logging_config import configure_logging
from app.routers import health, keys, notify

logger = logging.getLogger(__name__)

MAX_REQUEST_BODY_BYTES = 1024 * 64  # 64 KB


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings)

    container = Container(settings)
    app.state.container = container

    # Initialise DB schema first (SQLAlchemy backend only)
    if settings.repository_backend == "sqlalchemy" and settings.database_url:
        from app.repositories.sqlalchemy.session import init_db

        await init_db(settings.database_url.get_secret_value())
        logger.info("Database schema initialised")

    # Bootstrap admin root key if configured
    if settings.admin_root_key:
        raw_key = settings.admin_root_key.get_secret_value()
        key_hash = container.hasher.hash(raw_key)
        existing = await container.key_repo.get_by_hash(key_hash)
        if existing is None:
            from app.models.api_key import APIKey
            from datetime import datetime, timezone

            root_key = APIKey(
                id="root",
                name="admin-root",
                scopes=["admin"],
                created_at=datetime.now(timezone.utc),
            )
            await container.key_repo.create(root_key, key_hash)
            logger.info("Admin root key bootstrapped", extra={"key_id": "root"})

    logger.info("Application startup complete", extra={"environment": settings.environment})
    yield
    logger.info("Application shutdown")


def create_app(settings: "Settings | None" = None) -> FastAPI:
    _settings = settings or get_settings()

    app = FastAPI(
        title="AI Notification Distribution",
        description="Provider-agnostic multi-channel notification MCP server.",
        version="0.1.0",
        openapi_url="/openapi.json" if _settings.environment != "production" else None,
        docs_url="/docs" if _settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # Store settings so lifespan can read them without relying on lru_cache
    app.state.settings = _settings

    # ── Middleware ──────────────────────────────────────────────────────────────

    # Force HTTP→HTTPS in production. We do this at the app level because there is
    # currently no TLS-terminating reverse proxy in front of the service.
    # NOTE: If a reverse proxy (nginx, ALB, Cloud Run, etc.) is ever added to
    # terminate TLS, REMOVE this — the proxy forwards plain HTTP internally and
    # this middleware will cause redirect loops / broken health checks unless
    # X-Forwarded-Proto is handled. See README "Security Notes".
    if _settings.environment == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
        return await call_next(request)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", exc_info=exc)
        if _settings.environment == "production":
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )
        raise exc

    # ── Routers ────────────────────────────────────────────────────────────────

    app.include_router(health.router)
    app.include_router(notify.router)
    app.include_router(keys.router)

    return app


app = create_app()
