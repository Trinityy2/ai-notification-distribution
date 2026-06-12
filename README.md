# AI Notification Distribution

A provider-agnostic, multi-channel notification server built with **FastAPI** and Python. Designed as an MCP (Multi-Channel Platform) service — broadcast messages to Telegram, WhatsApp, and other platforms through a single unified API.

## Features

- **Provider-agnostic** — swap or add messaging providers without changing the API (ABC pattern throughout)
- **API key auth with RBAC** — scoped API keys with implication rules
- **Concurrent batch dispatch** — send to multiple targets in parallel via `asyncio.gather`
- **Audit log** — every send attempt (success or failure) is logged
- **Target validation** — each provider validates identifiers before attempting a send
- **Swappable backends** — repositories, hashers, and rate limiters are all ABCs; swap SQLAlchemy for anything else without touching business logic
- **Structured logging** — JSON in production, plain in development; OTel-bridge ready

---

## Project Structure

```
app/
├── config.py               # pydantic-settings config (env vars / .env files)
├── container.py            # DI container — wires ABCs to concrete implementations
├── dependencies.py         # FastAPI shared dependencies (auth, rate limiting)
├── logging_config.py       # Logging setup (JSON prod / plain dev)
├── main.py                 # App factory, middleware, routers
├── models/                 # Pydantic domain models
│   ├── api_key.py
│   ├── message.py
│   ├── result.py
│   └── target.py
├── providers/              # Messaging provider implementations
│   ├── base.py             # MessagingProvider ABC
│   ├── registry.py         # ProviderRegistry
│   ├── telegram.py
│   └── whatsapp.py         # Stub (not yet implemented)
├── repositories/           # Data access layer
│   ├── base.py             # APIKeyRepository + NotificationLogRepository ABCs
│   ├── in_memory.py        # In-memory implementations (dev / tests)
│   └── sqlalchemy/         # SQLAlchemy implementations (production)
├── routers/
│   ├── health.py
│   ├── keys.py             # API key CRUD
│   └── notify.py           # Single + batch notification dispatch
└── security/
    ├── hashing/            # KeyHasher ABC + SHA256 / BCrypt impls
    ├── rate_limiting/      # RateLimiter ABC + InMemory / SlowAPI impls
    └── rbac.py             # Scopes, implication rules, require_scope()

tests/
├── conftest.py             # Shared fixtures (InMemory repos, mock provider)
├── unit/                   # Pure unit tests (no HTTP)
└── integration/            # Full HTTP tests via ASGI test client
```

---

## API Endpoints

| Method | Path | Scope required | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | — | Health check (unauthenticated) |
| `POST` | `/notify` | `notify:send` | Send a message to a single target |
| `POST` | `/notify/batch` | `notify:send` | Send a message to multiple targets concurrently |
| `GET` | `/keys` | `keys:read` | List all API keys |
| `POST` | `/keys` | `keys:write` | Create a new API key |
| `GET` | `/keys/{id}` | `keys:read` | Get an API key by ID |
| `PATCH` | `/keys/{id}` | `keys:write` | Update an API key |
| `DELETE` | `/keys/{id}` | `keys:write` | Delete an API key |

### Authentication

Pass your API key in the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

### RBAC Scopes

| Scope | Implies | Description |
|-------|---------|-------------|
| `notify:send` | — | Send notifications |
| `keys:read` | — | Read API key records |
| `keys:write` | `keys:read` | Create / update / delete API keys |
| `admin` | `notify:send`, `keys:read`, `keys:write` | Full access |

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone the repo
git clone https://github.com/Trinityy2/ai-notification-distribution
cd ai-notification-distribution

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Copy and edit the environment config
cp .env.example .env
# Edit .env — set ADMIN_ROOT_KEY, DATABASE_URL, TELEGRAM__BOT_TOKEN, etc.
```

### Running the Server

```bash
uvicorn app.main:app --reload        # development
uvicorn app.main:app --host 0.0.0.0  # production (set ENVIRONMENT=production)
```

Interactive docs are available at `http://localhost:8000/docs` (development only).

### Running with Docker

```bash
# Copy and configure secrets
cp .env.example .env
# Edit .env — set ADMIN_ROOT_KEY, TELEGRAM__BOT_TOKEN, etc.

# Build and start
docker compose up -d

# View logs
docker compose logs -f app
```

**Persistent volumes created automatically:**

| Volume | Mounted at | Contains |
|--------|-----------|----------|
| `logs` | `/app/logs` | Rotating log files |
| `data` | `/app/data` | SQLite database file |

---

## Configuration

All config is via environment variables (or a `.env` / `.env.local` file). See `.env.example` for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` or `production` |
| `ADMIN_ROOT_KEY` | — | Bootstrap admin API key (created on first startup) |
| `REPOSITORY_BACKEND` | `sqlalchemy` | `sqlalchemy` or `in_memory` |
| `DATABASE_URL` | — | SQLAlchemy async DB URL (required for sqlalchemy backend) |
| `HASHER_BACKEND` | `sha256` | `sha256` (deterministic) or `bcrypt` (salted) |
| `HASHER_SECRET` | — | HMAC secret for SHA256 hashing |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window per API key |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window size |
| `TELEGRAM__BOT_TOKEN` | — | Telegram Bot API token (enables telegram provider) |

---

## Example Usage

### Send a notification (Telegram)

```bash
curl -X POST http://localhost:8000/notify \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "target": { "provider": "telegram", "identifier": "@mychannel" },
    "message": { "text": "Hello from the notification server!" }
  }'
```

### Batch send

```bash
curl -X POST http://localhost:8000/notify/batch \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": [
      { "provider": "telegram", "identifier": "@channel1" },
      { "provider": "telegram", "identifier": "123456789" }
    ],
    "message": { "text": "Broadcast message" }
  }'
```

Batch dispatch is **best-effort** — all targets are attempted concurrently and individual failures do not abort the rest.

---

## Development

### Running Tests

```bash
# All tests with coverage report
python -m pytest

# Specific file
python -m pytest tests/integration/test_notify.py -v
```

Coverage is reported to the terminal and to `htmlcov/index.html` after each run. Current coverage: **93%**.

### Adding a New Provider

1. Create `app/providers/myprovider.py` implementing the `MessagingProvider` ABC:

```python
from app.providers.base import MessagingProvider
from app.models.target import Target
from app.models.message import Message
from app.models.result import SendResult

class MyProvider(MessagingProvider):
    async def send(self, target: Target, message: Message) -> SendResult:
        # your implementation
        ...

    def validate_target(self, target: Target) -> None:
        # raise InvalidTargetError if identifier is invalid
        ...
```

2. Register it in `app/container.py` inside the `provider_registry` property.

That's it — no changes to any router or auth logic required.

---

## Security Notes

- API keys are stored as hashes (never in plain text)
- `SecretStr` is used for all sensitive config values — they never appear in logs or tracebacks
- Request body size is capped at 64 KB
- OpenAPI docs (`/docs`, `/openapi.json`) are disabled in production
- HTTPS redirect middleware is enabled in production
