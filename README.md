# byteforge-converse-backend

Flask REST API server for ByteforgeConverse. Exposes endpoints for conversations, messages, chat turns, and session handshakes. Auth is delegated to the consuming application via an upstream gateway header.

## Endpoints (preliminary)

- `POST /api/sessions` — issue a handshake session for the frontend
- `GET /api/sessions/<id>` / `DELETE /api/sessions/<id>` — fetch / revoke
- `GET /api/conversations` / `POST /api/conversations` — list / create
- `GET /api/conversations/<id>` / `DELETE /api/conversations/<id>`
- `GET /api/conversations/<id>/messages` / `POST /api/conversations/<id>/messages`
- `POST /api/conversations/<id>/chat` — submit a user message, receive assistant reply

Swagger UI is exposed at `/swagger` when the server is running.

## Setup

```bash
cp example.env .env       # then edit .env with real values

python -m venv .
source bin/activate

# Internal libraries are pulled from public GitHub repos — no token needed
pip install --upgrade -r requirements.txt
```

## Running

```bash
source bin/activate

# Development
python byteforge_converse_backend.py

# Production
gunicorn -w 4 -b 0.0.0.0:5252 'byteforge_converse_backend:create_app()'
```

## Environment Variables

**Server:**
- `PORT` — server port (default: 5252)
- `DEBUG` — enable Flask debug mode (default: False)

**Database:**
- `BYTEFORGE_CONVERSE_DB_HOST` — host (default: `localhost`)
- `BYTEFORGE_CONVERSE_DB_PORT` — port (default: `5432`)
- `BYTEFORGE_CONVERSE_DB_NAME` — database name (default: `byteforge_converse`)
- `BYTEFORGE_CONVERSE_DB_USER` — user (default: `byteforge_converse`)
- `BYTEFORGE_CONVERSE_DB_PASSWORD` — **required**

**LLM (OpenRouter proxy):**
- `BYTEFORGE_CONVERSE_OPENROUTER_API_KEY` — **required** for the chat turn
- `BYTEFORGE_CONVERSE_LLM_MODEL` — default model (default: `anthropic/claude-3.5-sonnet`); overridable per-conversation

**Other:**
- `ALLOWED_ORIGINS` — comma-separated CORS allow-list for embedding frontends

## Database Setup

Schema lives in `database/schema.sql`. The bootstrap script creates the role, database, and applies the schema:

```bash
source bin/activate
export BYTEFORGE_CONVERSE_DB_PASSWORD="<app_user_password>"   # picked up from .env if present
python dev_scripts/setup_database.py --pg-password "<postgres_superuser_password>"
```

The script is idempotent — safe to re-run. It uses the same `BYTEFORGE_CONVERSE_DB_*` env vars as the running app.

Tables created: `conversations`, `messages`, `sessions` — all using UUID primary keys and `BIGINT` unix timestamps for date/time fields.

## Logging

Logging is configured via `byteforge-loki-logging` inside `create_app()` (post-fork in gunicorn workers, so the Loki handler's SSL session is valid in each worker). The application tag is `byteforge-converse-backend`.

**Local development** — set `DEBUG_LOCAL=true` (default). Logs go to the console in human-readable form, no Loki connection needed.

**Production** — set `DEBUG_LOCAL=false` and supply `LOKI_ENDPOINT`, `LOKI_USER`, `LOKI_PASSWORD`. If Loki uses a private CA, mount it into the container (e.g., via docker-compose) and set `LOKI_CA_BUNDLE_PATH=/app/certs/loki-ca.pem`.

Flask/werkzeug/gunicorn loggers are forced to propagate to root inside `create_app()` so route exceptions and access logs reach Loki — without this, Flask catches exceptions internally and only the container stdout sees them.

## Docker Build & Publish

The container is published to **`ghcr.io/jmazzahacks/byteforge-converse-backend`**. Internal libraries are pulled from public GitHub repos at build time, so no token is baked into the image.

```bash
# One-time: log in to GHCR (needs a PAT with write:packages to push the image)
echo $GHCR_TOKEN | docker login ghcr.io -u jmazzahacks --password-stdin

# Build, version-bump, and push (uses VERSION file at repo root)
./build-publish.sh

# Force a clean rebuild (no layer cache)
./build-publish.sh --no-cache
```

Run the image locally:
```bash
docker run --rm -p 5252:5252 --env-file .env ghcr.io/jmazzahacks/byteforge-converse-backend:latest
```

To wire the service into an existing docker-compose admin stack (Postgres already provided), see [`docker-compose.example.yaml`](./docker-compose.example.yaml) — a teaching snippet to merge into your own compose file.

## API Documentation

Once running, open: `http://localhost:5252/swagger`
