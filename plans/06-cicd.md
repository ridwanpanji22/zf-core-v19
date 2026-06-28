# Stream 6: CI/CD & DevOps

> Depends on: Stream 1 selesai
> Bisa dijalankan PARALEL dengan Stream 2, 3, dan 4

---

## S6-T01: GitHub Actions CI/CD Pipeline

**Files:**
- `/home/ridwan/zf-core-v19/.github/workflows/ci-cd.yml`

**Dependencies:** S1-T02

**Deskripsi:**

Buat GitHub Actions workflow yang terpicu saat:
- Push ke branch `main` (production deploy)
- Push ke branch `develop` (staging deploy)
- PR ke branch `main` atau `develop` (run tests & lint only)

### Pipeline Stages:

#### 1. Lint & Code Quality
- Job `lint` (runner: ubuntu-latest)
- Python: `ruff` atau `flake8` untuk linting kode backend.
- Next.js: `npm run lint` untuk frontend.

#### 2. Run Tests
- Job `test` (depends on lint)
- Backend: Run pytest (`pytest backend/tests/`)
- Frontend: Run jest/vitest (`npm --prefix frontend test`)

#### 3. Build & Push Docker (Only on push main/develop)
- Job `build` (depends on test)
- Login ke GitHub Container Registry (GHCR) atau Docker Hub.
- Build & push docker images:
  - `zf-backend:latest`
  - `zf-frontend:latest`

#### 4. SSH Deploy (Only on push main/develop)
- Job `deploy` (depends on build)
- Gunakan `appleboy/ssh-action` untuk ssh ke VPS.
- Perintah deploy di VPS:
  ```bash
  cd /home/ridwan/zf-core-v19
  git pull origin main # atau develop
  docker compose pull
  docker compose up -d --remove-orphans
  ```
- Kirim status deploy (sukses/gagal) ke Telegram Bot API (S6-T03).

**Acceptance Criteria:**
- Commit workflow file valid (`git diff` clean).
- CI pipeline terpicu otomatis saat ada push/PR.
- Step deploy berjalan jika target branch match.

---

## S6-T02: Health Check & Graceful Degradation

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/system.py` (edit)
- `/home/ridwan/zf-core-v19/backend/app/main.py` (edit)

**Dependencies:** S1-T03, S1-T04

**Deskripsi:**

### Endpoint `GET /api/health`
Kembalikan format JSON:
```json
{
  "status": "healthy",
  "version": "19.0.1",
  "uptime_seconds": 86400,
  "websocket_connected": true,
  "assets_monitored": 200,
  "assets_deep_analysis": 45,
  "circuit_breaker": false,
  "redis_connected": true,
  "db_connected": true,
  "last_data_received": "2026-06-28T12:00:00Z"
}
```
- DB Health: panggil query `SELECT 1` via `AsyncSession` untuk cek koneksi.
- Redis Health: panggil `PING` command di Redis client.
- Jika DB atau Redis putus, return `status: "unhealthy"` (HTTP status 503).

### Graceful Degradation (RAM Management)
- Buat logic middleware / background checker di Celery task `calculate_heartbeat`.
- Jika sisa memory VPS < 15% (baca `/proc/meminfo` atau gunakan library `psutil`):
  - Kirim critical alert "VPS memory warning, switching to Heartbeat Mode".
  - Otomatis switch **seluruh 200 aset** ke "Heartbeat Mode" (hentikan komputasi Deep Analysis untuk menghemat RAM).
  - Simpan event ke `system_events`.

**Acceptance Criteria:**
- Health endpoint mengembalikan status "unhealthy" 503 jika DB atau Redis mati.
- Data health status akurat dengan metrik system yang aktif.
- Memory protection system mendeteksi low memory dan men-downgrade mode kalkulasi dengan benar.

---

## S6-T03: Telegram Bot Integration (Alert System)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/telegram.py`

**Dependencies:** S1-T03, S1-T04

**Deskripsi:**

### Class `TelegramAlertSystem`
- Kirim pesan outbound ke Telegram menggunakan `httpx.AsyncClient` (non-blocking).
- Token bot dan target chat ID dibaca dari `settings.TELEGRAM_BOT_TOKEN` dan `settings.TELEGRAM_CHAT_ID`.
- Format templates pesan sesuai priority (CRITICAL/WARNING/INFO). Gunakan markdown format.
  - Critical: Emoji 🔴 / 🚨, tebal, warning teks.
  - Warning: Emoji 🟡 / ⚠️.
  - Info: Emoji 🟢 / ✅.
- **Anti-Spam Filter (In-Memory / Redis):**
  - Gunakan Redis key `alert_sent:{type}:{symbol}` dengan TTL 900 detik (15 menit).
  - Jika key sudah ada, jangan kirim pesan duplikat.
  - Limit: Simpan counter alert per menit di Redis. Jika counter > 5, tahan pengiriman dan gabungkan pesan.
  - Akumulasi: Jika > 10 aset memicu status Waspada bersamaan, kirim 1 ringkasan pesan komparatif, bukan 10 pesan individual.

**Acceptance Criteria:**
- Berhasil mengirim pesan Telegram melalui unit test.
- Filter spam menolak pengiriman alert identik dalam waktu kurang dari 15 menit.
- Grouping alert bekerja saat banyak aset waspada bersamaan.
