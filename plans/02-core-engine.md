# Stream 2: Backend Core Engine

> Depends on: Stream 1 selesai (S1-T01 sampai S1-T06)

---

## S2-T01: Data Ingestion — OKX WebSocket Client

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/ingestion/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/ingestion/okx_ws.py`
- `/home/ridwan/zf-core-v19/backend/app/ingestion/normalizer.py`

**Dependencies:** S1-T03, S1-T06

**Deskripsi:**

### okx_ws.py — `OKXWebSocketClient` class
- Library: `ccxt.pro` (async WebSocket built-in)
- Init: exchange = `ccxt.pro.okx({...})` dengan credential dari settings
- Method `start(symbols: list[str])`:
  - Subscribe ke channels per symbol: `books5`, `trades`, `tickers`, `mark-price`
  - Untuk funding-rate dan open-interest, gunakan REST polling (OKX WS channel terbatas)
  - Loop: `while True: await exchange.watch_order_book(symbol)` dll
  - Setiap data masuk → normalize via `normalizer.py` → simpan ke Redis
- Auto-reconnect: ccxt.pro sudah handle, tambahkan try/except dengan exponential backoff (1s, 2s, 4s, 8s, max 60s)
- Heartbeat: ccxt.pro handle internal. Log jika reconnect terjadi.
- Method `stop()`: close exchange connection gracefully

### normalizer.py — `normalize(channel, raw_data) -> dict`
Format output standar:
```python
{
    "symbol": "BTC-USDT-SWAP",
    "timestamp": 1719532800000,  # UTC epoch ms
    "type": "ticker",  # ticker|trade|book|funding|oi|liquidation
    "data": { ... }
}
```
- Harga: simpan sebagai string (hindari floating point errors)
- Timestamp: selalu UTC epoch milliseconds

### Redis buffer
Gunakan `redis.asyncio` client. Simpan data sesuai pattern:

| Key | Type | TTL | Content |
|-----|------|-----|---------|
| `tick:{symbol}` | String JSON | 60s | Snapshot terakhir ticker |
| `book:{symbol}` | String JSON | 30s | Order book depth terakhir |
| `trades:{symbol}` | List | 300s | 100 trade terakhir (LPUSH + LTRIM) |
| `oi:{symbol}` | String | 300s | Open Interest terakhir |
| `fr:{symbol}` | String | 28800s | Funding Rate terakhir |

**Acceptance Criteria:**
- `OKXWebSocketClient` bisa connect ke OKX testnet/mainnet
- Data ter-normalize dan tersimpan di Redis
- Redis key pattern sesuai spec
- Reconnect otomatis saat koneksi putus

---

## S2-T02: Calculation Engine — Core Formulas

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/core/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/core/drift.py`
- `/home/ridwan/zf-core-v19/backend/app/core/zf_score.py`
- `/home/ridwan/zf-core-v19/backend/app/core/psi_total.py`
- `/home/ridwan/zf-core-v19/backend/app/core/decay.py`
- `/home/ridwan/zf-core-v19/backend/app/core/calibration.py`

**Dependencies:** S1-T03

**Deskripsi:**

### drift.py — `calculate_drift(p_market: float, p_pure: float) -> float`
```
D_res = |P_market - P_pure| / P_pure * 100
```
- P_pure = VWAP 24 jam (dihitung dari trade data)
- Output: float, 2 desimal, satuan persen
- Helper: `calculate_vwap(trades: list[dict]) -> float` — sum(price*volume) / sum(volume)

### zf_score.py — `calculate_zf_score(d_res, oi_ratio, fr_divergence, liq_density, book_imbalance) -> float`
Komponen dan bobot:
- Topological Drift (D_res): 30%
- Rasio OI/Volume 24h: 25%
- FR_curr / FR_avg_7d: 20%
- Liquidation count / volume: 15%
- bid_vol / ask_vol: 10%

Normalisasi: min-max scaling ke [0, 1].
Setiap komponen dinormalisasi independen terhadap historis 30 hari (perlu fungsi helper `min_max_scale(value, min_val, max_val) -> float`).

Klasifikasi output:

| Range | Status | Mode |
|-------|--------|------|
| 0.00-0.59 | normal | heartbeat |
| 0.60-0.79 | perlu_perhatian | deep_analysis |
| 0.80-0.84 | kritis | deep_analysis |
| 0.85-0.98 | disintegrasi | deep_analysis |
| 0.99-1.00 | force_exit | deep_analysis |

Return: `ZFScoreResult(score=float, status=str, mode=str)` (dataclass/namedtuple)

### psi_total.py — `calculate_psi_total(p_market, p_vwap, delta_oi, vol_24h, fr_curr, fr_avg, alpha, omega) -> float`
```
Ψ_total = |P_market - P_vwap| + ω1*(ΔOI/Vol_24h) + ω2*(FR_curr/FR_avg) + ω3*(α)
```
- omega: dict `{"w1": 0.35, "w2": 0.40, "w3": 0.25}` (default values)
- alpha (α): selisih harga OKX vs Binance (float, bisa 0 jika data tidak tersedia)
- Ambang kritis: Ψ_total > 3.0 = over-extended
- Return: float

### decay.py — `predict_decay(zf_scores_30d: list[float], psi_totals_30d: list[float]) -> float`
- Metode: linear regression dari time-series ZF-Score + Ψ_total 30 hari, extrapolasi 10 hari
- Library: `numpy.polyfit` atau `scipy.stats.linregress`
- Output: `predicted_change_pct` (float, bisa negatif = prediksi turun, positif = prediksi naik)

### calibration.py — `recalibrate_omega(predictions: list, actuals: list, current_omega: dict) -> dict`
- Ambil prediksi vs aktual 24 jam terakhir
- Hitung gradient error per komponen
- `ω_new = ω_old - learning_rate * gradient` (learning_rate = 0.01)
- Constraint: `sum(ω) = 1.0`, setiap `ω >= 0.1`
- Jika constraint dilanggar, re-normalize
- Return: `{"w1": float, "w2": float, "w3": float}`

**Acceptance Criteria:**
- Setiap fungsi bisa dipanggil dengan input test dan return hasil yang masuk akal
- `calculate_drift(67500, 67000)` → ~0.75 (percent)
- `calculate_zf_score(...)` → float antara 0-1
- `calculate_psi_total(...)` → float positif
- `predict_decay(...)` → float (persen)
- `recalibrate_omega(...)` → dict dengan sum=1.0, setiap ω≥0.1

---

## S2-T03: Asset Swarm Manager

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/core/asset_swarm.py`

**Dependencies:** S2-T01, S2-T02, S1-T04

**Deskripsi:**

### Class `AssetSwarmManager`

#### `async refresh_registry(exchange) -> list[str]`
- Panggil OKX REST: ambil 200 SWAP instruments dengan volume 24h tertinggi
- Upsert ke tabel `asset_registry` (insert new, deactivate yang keluar daftar)
- Return list of symbols

#### `async get_mode(symbol: str, zf_score: float, d_res_change_5m: float) -> str`
- Jika ZF-Score < 0.6 AND ΔD_res ≤ 20%: return `"heartbeat"`
- Else: return `"deep_analysis"`
- Log setiap perubahan mode

#### `async classify_assets(db_session) -> dict`
- Query semua aset aktif
- Return `{"heartbeat": [symbols], "deep_analysis": [symbols]}`

#### `async recalculate_clusters(db_session)`
- Ambil return harga 7 hari dari `asset_snapshots`
- Hitung Pearson correlation matrix (numpy)
- Threshold: korelasi > 0.7 = satu klaster
- Update `cluster_id` di `asset_registry`

**Acceptance Criteria:**
- `refresh_registry()` return list 200 symbols
- Mode switching berdasarkan ZF-Score threshold benar
- Klasterisasi menghasilkan grouping yang valid

---

## S2-T04: Memory Buffer Sesi (MBS)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/mbs.py`

**Dependencies:** S1-T04, S2-T02

**Deskripsi:**

### `async save_snapshot(db_session, assets_data: list[dict])`
- Batch insert ke `asset_snapshots` (TimescaleDB hypertable)
- Data per aset: symbol, price, zf_score, psi_total, d_res, oi, funding_rate, volume_24h, bid_depth_ratio, ofi, mode, status, predicted_change_pct
- Dipanggil tiap 5 menit oleh Celery task `save_mbs_snapshot`

### `async create_journal(db_session, started_at, ended_at)`
- Hitung: avg ZF-Score, count Code Red, total alerts, error count
- Ambil omega changes dari `calibration_log`
- Insert ke `session_journals`
- Dipanggil saat graceful shutdown (lifespan on_shutdown di main.py)

### `async load_and_merge(db_session) -> list[dict]`
- Load snapshot terakhir per aset (latest row per symbol dari `asset_snapshots`)
- Bandingkan dengan data live dari Redis
- Jika |ZF-Score_snapshot - ZF-Score_live| > 0.2: flag "Resonance Mismatch" → log warning
- Return merged data list
- Dipanggil saat startup (lifespan on_startup di main.py)

**Acceptance Criteria:**
- Snapshot tersimpan di DB setiap 5 menit
- Journal terbuat saat shutdown
- Merge saat startup mendeteksi mismatch dengan benar

---

## S2-T05: Implement Celery Tasks (Core)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/tasks.py` (replace stubs dari S1-T06)

**Dependencies:** S2-T01, S2-T02, S2-T03, S2-T04

**Deskripsi:**
Implementasi 6 dari 9 Celery tasks (3 sisanya di Stream 3):

### `calculate_deep_analysis()` (tiap 10 detik)
1. Ambil list aset deep_analysis dari Redis cache atau DB
2. Untuk setiap aset: baca data dari Redis → hitung D_res, ZF-Score, Ψ_total
3. Simpan hasil ke Redis key `metrics:{symbol}` (untuk WebSocket push)
4. Update mode jika threshold berubah

### `calculate_heartbeat()` (tiap 60 detik)
1. Ambil list aset heartbeat
2. Hitung hanya ZF-Score (simplified — hanya ticker + OI)
3. Jika ZF-Score naik > 0.6: switch ke deep_analysis mode

### `save_mbs_snapshot()` (tiap 5 menit)
1. Panggil `mbs.save_snapshot()` dengan data terkini dari Redis

### `calculate_decay_prediction()` (tiap 1 jam)
1. Per aset: ambil ZF-Score + Ψ_total 30 hari dari `asset_snapshots`
2. Panggil `decay.predict_decay()`
3. Simpan hasil ke `prediction_log`

### `recalculate_clusters()` (tiap 6 jam)
1. Panggil `asset_swarm.recalculate_clusters()`

### `recalibrate_omega()` (daily 00:00 UTC)
1. Ambil prediksi vs aktual 24 jam dari `prediction_log`
2. Panggil `calibration.recalibrate_omega()`
3. Simpan log ke `calibration_log`
4. Broadcast new omega via Redis pub/sub

**Acceptance Criteria:**
- Semua 6 tasks berjalan tanpa error saat dipanggil manual
- Data tersimpan di tabel yang benar
- Logging structured (structlog)

---

## S2-T06: WebSocket Dashboard Handler (Backend)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/websocket.py`

**Dependencies:** S2-T05, S1-T03

**Deskripsi:**

### WebSocket endpoint: `ws://host/ws/dashboard?token={jwt}`

1. On connect: validate JWT token dari query param. Reject jika invalid.
2. Gunakan Redis pub/sub: subscribe ke channel `dashboard:updates`
3. Celery tasks (S2-T05) publish update ke channel ini setelah kalkulasi
4. Server → Client message types:
```json
{"type": "asset_update", "data": {"symbol": "...", "price": ..., "zf_score": ..., ...}}
{"type": "alert", "data": {"priority": "critical", "type": "code_red", "symbol": "...", ...}}
{"type": "prediction_update", "data": {"title": "Pasar Dominan Turun...", "assets": [...]}}
{"type": "system_status", "data": {"circuit_breaker": false, "cold_mode": false, ...}}
{"type": "session_comparison", "data": {"changes": [...]}}
```
5. Client → Server: `{"type": "subscribe", "symbols": [...]}` dan `{"type": "unsubscribe", "symbols": [...]}`
6. Handle disconnect gracefully

**Acceptance Criteria:**
- WebSocket connect dengan valid JWT → sukses
- WebSocket connect tanpa/invalid JWT → rejected
- Update dari Redis pub/sub ter-forward ke client
- Subscribe/unsubscribe per symbol berfungsi

---

## S2-T07: Asset & Prediction REST Endpoints

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/assets.py`
- `/home/ridwan/zf-core-v19/backend/app/api/predictions.py`
- `/home/ridwan/zf-core-v19/backend/app/api/system.py`
- `/home/ridwan/zf-core-v19/backend/app/api/calibration.py`

**Dependencies:** S2-T05, S1-T04

**Deskripsi:**

### assets.py
- `GET /api/assets` → List 200 aset dengan metrik terkini (dari Redis cache, fallback DB)
- `GET /api/assets/{symbol}` → Detail satu aset
- `GET /api/assets/{symbol}/history?from=&to=&interval=` → Historical snapshots
- `GET /api/assets/{symbol}/orderbook` → Order book depth + bid_depth_ratio
- `GET /api/assets/{symbol}/liquidation-map` → Estimasi liquidation zones

### predictions.py
- `GET /api/predictions/top20` → Top 20 prediksi. Logic judul dinamis:
  - Jika >60% aset Δ24h negatif: "Pasar Dominan Turun — 20 Koin Prediksi Anjlok dalam 10 Hari"
  - Jika >60% positif: "Pasar Dominan Naik — 20 Koin Prediksi Naik dalam 10 Hari"
  - Else: "Pasar Netral — 20 Koin dengan Potensi Pergerakan Tertinggi dalam 10 Hari"
  - Urut: |predicted_change_pct| descending
- `GET /api/predictions/{symbol}` → Prediksi detail per aset
- `GET /api/analysis/correlation-matrix` → Matriks korelasi klaster
- `GET /api/analysis/market-dominance` → % naik/turun/netral

### system.py
- `GET /api/health` → (sudah ada di main.py, pindahkan ke sini atau biarkan)
- `GET /api/sessions` → List session journals
- `GET /api/sessions/{id}` → Detail journal
- `GET /api/system/status` → Circuit Breaker status, Cold Mode, alert stats
- `POST /api/system/circuit-breaker/reset` → Reset CB (Super Admin only)
- `POST /api/system/cold-mode/unlock` → Unlock (Super Admin only)

### calibration.py
- `GET /api/calibration/current` → Bobot ω saat ini
- `GET /api/calibration/history` → Riwayat re-kalibrasi
- `POST /api/calibration/trigger` → Manual trigger (Super Admin only)

Response format standar:
```json
{"success": true, "data": {...}, "error": null, "timestamp": "2026-06-28T12:00:00Z"}
```

Semua endpoint require auth (JWT) kecuali `/api/health`.

**Acceptance Criteria:**
- Semua endpoint return response format standar
- Auth middleware enforce JWT
- Pagination berfungsi pada list endpoints
- Error handling return proper error codes
