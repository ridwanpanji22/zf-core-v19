# Stream 1: Infrastructure & Foundation

> Stream ini HARUS selesai sebelum stream lain dimulai.

---

## S1-T01: Git Init & Project Root Files

**Files:**
- `/home/ridwan/zf-core-v19/.gitignore`
- `/home/ridwan/zf-core-v19/.env.example`

**Dependencies:** Tidak ada

**Deskripsi:**
1. Inisialisasi git repo di `/home/ridwan/zf-core-v19/`
2. Buat `.gitignore` dengan rules untuk: Python (`__pycache__`, `*.pyc`, `.venv`, `*.egg-info`), Node.js (`node_modules`, `.next`, `out`), environment (`.env`, `.env.local`), IDE (`.vscode`, `.idea`), Docker (`*.log`), OS (`.DS_Store`, `Thumbs.db`)
3. Buat `.env.example` dengan semua variabel berikut (value kosong atau contoh):
```env
# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=zfcore
DB_USER=zfcore
DB_PASSWORD=changeme

# Redis
REDIS_URL=redis://redis:6379/0

# OKX API (system-level, untuk data ingestion)
OKX_API_KEY=
OKX_SECRET_KEY=
OKX_PASSPHRASE=

# Google OAuth 2.0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://zf.yourdomain.com/api/auth/google/callback

# Super Admin
SUPER_ADMIN_EMAIL=admin@example.com

# API Key Encryption
API_KEY_ENCRYPTION_SECRET=changeme-32-byte-random-string

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Auth
JWT_SECRET=changeme-to-random-string
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=7

# App
APP_ENV=production
LOG_LEVEL=INFO
ASSET_SWARM_SIZE=200
DEMO_ENABLED=true
DEMO_INITIAL_BALANCE=10000
DEMO_MAX_LEVERAGE=10
```

**Acceptance Criteria:**
- `git status` berjalan tanpa error
- `.gitignore` mencakup semua pattern di atas
- `.env.example` berisi semua 22 variabel

---

## S1-T02: Docker Compose & Dockerfiles

**Files:**
- `/home/ridwan/zf-core-v19/docker-compose.yml`
- `/home/ridwan/zf-core-v19/backend/Dockerfile`
- `/home/ridwan/zf-core-v19/frontend/Dockerfile`

**Dependencies:** Tidak ada

**Deskripsi:**

### docker-compose.yml
6 services:

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, redis]
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build: ./backend
    command: celery -A app.services.celery_app worker --loglevel=info --concurrency=4
    depends_on: [db, redis]
    env_file: .env
    restart: unless-stopped

  celery-beat:
    build: ./backend
    command: celery -A app.services.celery_app beat --loglevel=info
    depends_on: [redis]
    env_file: .env
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env
    restart: unless-stopped

  db:
    image: timescale/timescaledb:latest-pg16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: zfcore
      POSTGRES_USER: zfcore
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["127.0.0.1:5432:5432"]
    restart: unless-stopped
    shm_size: '256mb'

  redis:
    image: redis:7-alpine
    volumes: ["redisdata:/data"]
    ports: ["127.0.0.1:6379:6379"]
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

volumes:
  pgdata:
  redisdata:
```

### backend/Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### frontend/Dockerfile
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
EXPOSE 3000
```

**Acceptance Criteria:**
- `docker compose config` valid tanpa error
- Kedua Dockerfile ada dan syntactically correct

---

## S1-T03: Backend Boilerplate (FastAPI + Config + DB)

**Files:**
- `/home/ridwan/zf-core-v19/backend/requirements.txt`
- `/home/ridwan/zf-core-v19/backend/app/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/main.py`
- `/home/ridwan/zf-core-v19/backend/app/config.py`
- `/home/ridwan/zf-core-v19/backend/app/database.py`

**Dependencies:** Tidak ada

**Deskripsi:**

### requirements.txt
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy[asyncio]==2.0.*
asyncpg==0.30.*
alembic==1.14.*
pydantic-settings==2.7.*
redis==5.2.*
celery==5.4.*
ccxt==4.*
authlib==1.3.*
httpx==0.28.*
python-jose[cryptography]==3.3.*
cryptography==44.*
structlog==24.*
numpy==2.*
scipy==1.*
scikit-learn==1.*
```

### app/config.py
Gunakan `pydantic-settings` `BaseSettings` dengan `model_config = SettingsConfigDict(env_file=".env")`.
Field sesuai semua env vars di `.env.example`. Semua field harus ada type hint.
Buat singleton `settings = Settings()`.

### app/database.py
- Buat async engine: `create_async_engine(settings.database_url)` dimana `database_url` = `postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}`
- Buat `async_session_maker` = `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
- Buat async generator `get_db()` untuk dependency injection

### app/main.py
- Buat FastAPI app dengan `title="ZF-Core V19.0"`, `version="19.0.0"`
- Tambah CORS middleware (allow origins from env atau `["*"]` dev)
- Mount health endpoint: `GET /api/health` → return `{"status": "healthy", "version": "19.0.0"}`
- Lifespan: on startup print "ZF-Core starting", on shutdown print "ZF-Core shutting down"
- Placeholder: `# TODO: Include routers here`

**Acceptance Criteria:**
- `python -c "from app.config import settings; print(settings.DB_HOST)"` jalan
- `python -c "from app.main import app; print(app.title)"` jalan
- Health endpoint accessible

---

## S1-T04: Database Models (SQLAlchemy)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/models/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/models/base.py`
- `/home/ridwan/zf-core-v19/backend/app/models/asset.py`
- `/home/ridwan/zf-core-v19/backend/app/models/prediction.py`
- `/home/ridwan/zf-core-v19/backend/app/models/session.py`
- `/home/ridwan/zf-core-v19/backend/app/models/user.py`
- `/home/ridwan/zf-core-v19/backend/app/models/api_key.py`
- `/home/ridwan/zf-core-v19/backend/app/models/demo.py`
- `/home/ridwan/zf-core-v19/backend/app/models/config.py`

**Dependencies:** S1-T03

**Deskripsi:**

### base.py
- `Base = declarative_base()` (SQLAlchemy 2.0 style, gunakan `DeclarativeBase`)

### Model per file — mapping ke tabel:

#### asset.py
- `AssetRegistry`: id (PK serial), symbol (varchar 50 unique), base_currency (varchar 20), inst_type (varchar 10 default 'SWAP'), is_active (bool default true), cluster_id (int nullable), dampening_factor (float default 1.0), dampening_expires_at (timestamptz nullable), created_at (timestamptz default now), updated_at (timestamptz default now)
- `AssetSnapshot`: time (timestamptz PK), symbol (varchar 50), price (decimal 20,8), zf_score (float), psi_total (float), d_res (float), oi (decimal 20,2 nullable), funding_rate (float nullable), volume_24h (decimal 20,2 nullable), bid_depth_ratio (float nullable), ofi (float nullable), mode (varchar 20), status (varchar 20), predicted_change_pct (float nullable)

#### prediction.py
- `PredictionLog`: time (timestamptz), symbol (varchar 50), prediction_type (varchar 30), predicted_value (float), actual_value (float nullable), error (float nullable), omega_w1 (float), omega_w2 (float), omega_w3 (float)
- `CalibrationLog`: id (PK serial), calibrated_at (timestamptz default now), omega_w1_old, omega_w2_old, omega_w3_old, omega_w1_new, omega_w2_new, omega_w3_new (semua float), avg_error_before (float nullable), avg_error_after (float nullable), samples_used (int nullable)

#### session.py
- `CodeRedTracker`: symbol (varchar 50 PK), consecutive_sessions (int default 0), first_triggered_at (timestamptz nullable), last_triggered_at (timestamptz nullable), is_active (bool default false)
- `SessionJournal`: id (PK serial), started_at (timestamptz), ended_at (timestamptz), avg_zf_score (float nullable), code_red_count (int nullable), alerts_sent (int nullable), errors_count (int nullable), omega_changes (JSONB nullable), summary (text nullable)
- `SystemEvent`: time (timestamptz), event_type (varchar 50), severity (varchar 20), symbol (varchar 50 nullable), details (JSONB nullable), resolved_at (timestamptz nullable)

#### user.py
- `User`: id (PK serial), google_id (varchar 255 unique nullable), email (varchar 255 unique), display_name (varchar 255 nullable), avatar_url (text nullable), role (varchar 20 default 'architect'), status (varchar 20 default 'active'), created_at (timestamptz default now), last_login (timestamptz nullable)

#### api_key.py
- `UserApiKey`: id (PK serial), user_id (int FK users.id ON DELETE CASCADE), label (varchar 100 nullable), api_key_encrypted (LargeBinary), secret_key_encrypted (LargeBinary), passphrase_encrypted (LargeBinary), nonce (LargeBinary), api_key_last4 (varchar 4), permission_level (varchar 20 nullable), is_valid (bool default true), created_at (timestamptz default now), last_tested_at (timestamptz nullable)

#### demo.py
- `DemoWallet`: id (PK serial), user_id (int FK users.id unique ON DELETE CASCADE), balance (decimal 20,2 default 10000), initial_balance (decimal 20,2 default 10000), total_pnl (decimal 20,2 default 0), total_trades (int default 0), win_trades (int default 0), created_at (timestamptz default now), last_reset_at (timestamptz default now)
- `DemoPosition`: id (PK serial), user_id (int FK users.id ON DELETE CASCADE), symbol (varchar 50), side (varchar 10), size_usdt (decimal 20,2), leverage (int default 1), entry_price (decimal 20,8), exit_price (decimal 20,8 nullable), margin (decimal 20,2), pnl (decimal 20,2 nullable), fee (decimal 20,4 nullable), status (varchar 20 default 'open'), close_reason (varchar 20 nullable), opened_at (timestamptz default now), closed_at (timestamptz nullable)

#### config.py
- `SystemConfig`: key (varchar 100 PK), value (JSONB), updated_at (timestamptz default now), updated_by (int FK users.id nullable)

### __init__.py
Import semua model dari sub-files agar Alembic bisa detect.

**Acceptance Criteria:**
- `python -c "from app.models import *"` jalan tanpa error
- Semua 13 model class importable
- Column types dan constraints cocok dengan spec di atas

---

## S1-T05: Database Migration Setup (Alembic)

**Files:**
- `/home/ridwan/zf-core-v19/backend/alembic.ini`
- `/home/ridwan/zf-core-v19/backend/alembic/env.py`
- `/home/ridwan/zf-core-v19/backend/alembic/versions/001_initial_schema.py`

**Dependencies:** S1-T04

**Deskripsi:**
1. Init Alembic: `alembic init alembic`
2. Edit `alembic.ini`: set `sqlalchemy.url` dari env var (atau pakai env.py override)
3. Edit `alembic/env.py`:
   - Import `Base` dari `app.models.base`
   - Import semua models dari `app.models`
   - Set `target_metadata = Base.metadata`
   - Support async (gunakan `run_async_migrations`)
4. Generate initial migration: `alembic revision --autogenerate -m "initial schema"`
5. Dalam migration, setelah table creation, tambahkan raw SQL untuk:
   - `SELECT create_hypertable('asset_snapshots', 'time');`
   - `SELECT add_retention_policy('asset_snapshots', INTERVAL '30 days');`
   - `SELECT create_hypertable('prediction_log', 'time');`
   - `SELECT add_retention_policy('prediction_log', INTERVAL '90 days');`
   - `SELECT create_hypertable('system_events', 'time');`
   - `SELECT add_retention_policy('system_events', INTERVAL '90 days');`
   - Continuous aggregate `asset_daily_aggregates` (lihat SQL di SRS section 4)
   - Indexes: `idx_users_email`, `idx_users_role`, `idx_api_keys_user`, `idx_demo_pos_user`, `idx_demo_pos_symbol`
   - Default inserts for `system_config`: demo_mode_enabled='true', demo_initial_balance='10000', demo_max_leverage='10'

**Acceptance Criteria:**
- `alembic upgrade head` sukses terhadap TimescaleDB
- Semua 13 tabel terbuat
- Hypertables, retention policies, continuous aggregate, dan indexes terbuat
- Default `system_config` rows ada

---

## S1-T06: Celery Setup & Redis Connection

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/services/celery_app.py`
- `/home/ridwan/zf-core-v19/backend/app/services/tasks.py` (stubs)

**Dependencies:** S1-T03

**Deskripsi:**

### celery_app.py
- Buat Celery app: `celery_app = Celery("zfcore", broker=settings.REDIS_URL, backend=settings.REDIS_URL)`
- Set config: `task_serializer='json'`, `result_serializer='json'`, `accept_content=['json']`, `timezone='UTC'`
- Import `crontab` dari `celery.schedules`
- Set `beat_schedule` dengan 9 tasks:

```python
celery_app.conf.beat_schedule = {
    "calculate-deep-analysis": {
        "task": "app.services.tasks.calculate_deep_analysis",
        "schedule": 10.0,
    },
    "calculate-heartbeat": {
        "task": "app.services.tasks.calculate_heartbeat",
        "schedule": 60.0,
    },
    "save-mbs-snapshot": {
        "task": "app.services.tasks.save_mbs_snapshot",
        "schedule": 300.0,
    },
    "calculate-decay-prediction": {
        "task": "app.services.tasks.calculate_decay_prediction",
        "schedule": 3600.0,
    },
    "recalculate-clusters": {
        "task": "app.services.tasks.recalculate_clusters",
        "schedule": 21600.0,
    },
    "recalibrate-omega": {
        "task": "app.services.tasks.recalibrate_omega",
        "schedule": crontab(hour=0, minute=0),
    },
    "refresh-asset-registry": {
        "task": "app.services.tasks.refresh_asset_registry",
        "schedule": crontab(hour=0, minute=30),
    },
    "daily-db-backup": {
        "task": "app.services.tasks.backup_database",
        "schedule": crontab(hour=2, minute=0),
    },
    "check-demo-liquidations": {
        "task": "app.services.tasks.check_demo_liquidations",
        "schedule": 10.0,
    },
}
```

### tasks.py (stubs)
Buat 9 stub functions yang di-decorate `@celery_app.task`, masing-masing hanya `pass` atau log. Contoh:
```python
@celery_app.task
def calculate_deep_analysis():
    """Calculate ZF-Score & Ψ_total for Deep Analysis assets."""
    pass  # TODO: implement in S2-T03
```

**Acceptance Criteria:**
- `celery -A app.services.celery_app inspect ping` response OK (saat Redis tersedia)
- Semua 9 task terdaftar di Celery
- Beat schedule terkonfigurasi
