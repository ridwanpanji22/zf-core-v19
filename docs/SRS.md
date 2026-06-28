# SRS: ZF-Core V19.0 — Software Requirements Specification

**Versi Dokumen:** 1.0
**Tanggal:** 2026-06-28
**Referensi:** `docs/BUKU BESAR KRIPTO ZF ZEROTIME.txt`, `docs/PRD.md`

---

## 1. Pendahuluan

### 1.1 Tujuan Dokumen
Dokumen ini mendefinisikan spesifikasi kebutuhan perangkat lunak (SRS) untuk sistem ZF-Core V19.0 — Protokol Zerotime. Dokumen ini menjadi acuan teknis bagi pengembang dalam implementasi setiap modul, endpoint, struktur data, dan interaksi antar-komponen.

### 1.2 Ruang Lingkup Sistem
ZF-Core V19.0 adalah platform analisis pasar kripto derivatif yang:
- Memantau 200 aset kripto secara simultan via OKX Perpetual/Futures
- Menghitung metrik kuantitatif (ZF-Score, Ψ_total, Topological Drift)
- Menyajikan dashboard real-time dengan sinyal eksekusi deterministik
- Menyimpan data historis secara persisten (Memory Buffer Sesi)
- Memberikan alert otomatis via Telegram

### 1.3 Definisi & Akronim

| Istilah | Definisi |
|---|---|
| **Arsitek** | Pengguna utama sistem (trader profesional) |
| **ZF-Score** | Indeks kerapuhan aset (0-1) |
| **Ψ_total** | Ketegangan Struktural Terintegrasi |
| **D_res** | Topological Drift — deviasi harga dari resonansi murni |
| **MBS** | Memory Buffer Sesi — database persisten status 200 aset |
| **OI** | Open Interest — jumlah posisi derivatif terbuka |
| **FR** | Funding Rate — biaya periodik posisi perpetual |
| **OFI** | Order Flow Imbalance — ketimpangan arus pesanan |
| **α** | Shock Arbitrase — selisih harga antar bursa |
| **ω** | Bobot Adaptif — koefisien sensitivitas model |
| **χ** | Fungsi Cross-Over — prediktor inflection point |
| **σ** | Volatilitas pasar saat ini |
| **Decay_t** | Proyeksi peluruhan harga berdasarkan fungsi resonansi |
| **Code Red** | Status darurat: aset memenuhi semua kriteria disintegrasi 3 sesi berturut-turut |
| **Circuit Breaker** | Penghentian paksa seluruh eksekusi |
| **Heartbeat Mode** | Pemantauan ringan untuk aset stabil |
| **Deep Analysis** | Komputasi penuh untuk aset kritis |
| **Asset Swarm** | Koleksi 200 aset yang dipantau secara simultan |

### 1.4 Aktor Sistem

| Aktor | Deskripsi |
|---|---|
| **Super Admin** | Pengelola sistem, kelola user, konfigurasi global, akses penuh |
| **Arsitek** | User teregistrasi (login Google), akses dashboard penuh, input API key, terima alert |
| **Demo User** | User login yang menggunakan Mode Demo (paper trading), saldo virtual, akses dashboard penuh |
| **Zerotime Engine** | Subsistem backend yang menghitung metrik dan menjalankan logika otonom |
| **OKX API** | Sumber data eksternal (WebSocket + REST) |
| **Google OAuth** | Provider autentikasi eksternal |
| **Telegram Bot** | Kanal notifikasi outbound |
| **Celery Worker** | Proses background untuk scanning dan kalkulasi paralel |
| **Scheduler** | Cron/periodic task untuk re-kalibrasi ω (24 jam) dan cleanup data |

---

## 2. Kebutuhan Fungsional

### 2.1 Modul: Data Ingestion Engine

#### FR-ING-001: Koneksi WebSocket OKX
- **Deskripsi:** Sistem HARUS membuka dan memelihara koneksi WebSocket ke OKX API untuk menerima data real-time.
- **Channel yang di-subscribe:**

| Channel | Data | Interval |
|---|---|---|
| `books5` / `books` | Order Book depth (5/400 level) | Real-time |
| `trades` | Eksekusi perdagangan | Real-time |
| `funding-rate` | Funding Rate perpetual | Per update (8 jam) |
| `open-interest` | Open Interest | Per 3 menit |
| `liquidation-orders` | Order likuidasi | Real-time |
| `tickers` | Harga, volume 24h, bid/ask terbaik | Real-time |
| `mark-price` | Mark price (untuk kalkulasi VWAP) | Real-time |

- **Instrumen:** `instType=SWAP` (perpetual) untuk 200 aset teratas berdasarkan volume
- **Reconnect:** Auto-reconnect dengan exponential backoff (1s, 2s, 4s, 8s, max 60s)
- **Heartbeat:** Kirim ping setiap 25 detik; jika pong tidak diterima dalam 10 detik, reconnect

#### FR-ING-002: Normalisasi Data
- **Deskripsi:** Setiap data mentah dari OKX HARUS dinormalisasi ke format internal sebelum disimpan atau diproses.
- **Format internal:**
```json
{
  "symbol": "BTC-USDT-SWAP",
  "timestamp": 1719532800000,
  "type": "ticker|trade|book|funding|oi|liquidation",
  "data": { ... }
}
```
- **Timestamp:** Selalu UTC epoch milliseconds
- **Harga:** Desimal string, presisi sesuai aset (hindari floating point)

#### FR-ING-003: Rate Limiting
- **Deskripsi:** Sistem HARUS mematuhi rate limit OKX API.
- **WebSocket:** Max 240 request login per IP per jam; max 480 subscribe per koneksi
- **REST fallback:** Max 20 request/2 detik untuk endpoint publik
- **Implementasi:** Token bucket algorithm per endpoint

#### FR-ING-004: Data Buffer
- **Deskripsi:** Data real-time HARUS di-buffer di Redis sebelum diproses oleh Celery worker.
- **Struktur Redis:**

| Key Pattern | Tipe | TTL | Isi |
|---|---|---|---|
| `tick:{symbol}` | String (JSON) | 60s | Snapshot terakhir ticker |
| `book:{symbol}` | String (JSON) | 30s | Order book depth terakhir |
| `trades:{symbol}` | List | 300s | 100 trade terakhir |
| `oi:{symbol}` | String | 300s | Open Interest terakhir |
| `fr:{symbol}` | String | 28800s (8h) | Funding Rate terakhir |
| `liq:{symbol}` | List | 3600s | Liquidation orders 1 jam terakhir |

---

### 2.2 Modul: Zerotime Calculation Engine

#### FR-CALC-001: Topological Drift (D_res)
- **Deskripsi:** Sistem HARUS menghitung Topological Drift untuk setiap aset.
- **Rumus:** `D_res = |P_market - P_pure| / P_pure * 100`
- **P_pure:** VWAP 24 jam sebagai proxy harga resonansi murni (dihitung dari data trades)
- **Frekuensi perhitungan:** Setiap kali ticker update masuk (real-time)
- **Output:** Float, 2 desimal, satuan persen

#### FR-CALC-002: ZF-Score
- **Deskripsi:** Sistem HARUS menghitung ZF-Score (0-1) sebagai indeks kerapuhan aset.
- **Komponen input:**
  - Topological Drift (D_res) — bobot 30%
  - Rasio OI terhadap Volume 24h — bobot 25%
  - Divergensi Funding Rate (FR_curr / FR_avg_7d) — bobot 20%
  - Likuidasi density (jumlah liquidation / volume) — bobot 15%
  - Order Book imbalance (bid_vol / ask_vol) — bobot 10%
- **Normalisasi:** Min-max scaling ke rentang [0, 1]
- **Klasifikasi:**

| Range | Status | Aksi Sistem |
|---|---|---|
| 0.00 - 0.49 | Stabil | Heartbeat Mode |
| 0.50 - 0.59 | Normal | Heartbeat Mode |
| 0.60 - 0.79 | Perlu Perhatian | Deep Analysis Mode |
| 0.80 - 0.84 | Kritis | Deep Analysis + Alert Waspada |
| 0.85 - 0.98 | Disintegrasi | Kandidat prediksi + Alert Code Red (jika 3 sesi) |
| 0.99 - 1.00 | Force Exit | Circuit Breaker aktif |

- **Frekuensi:** Setiap 10 detik per aset (batch processing via Celery)

#### FR-CALC-003: Ketegangan Struktural (Ψ_total)
- **Deskripsi:** Sistem HARUS menghitung Ψ_total sebagai indeks kerentanan pasar.
- **Rumus:** `Ψ_total = |P_market - P_vwap| + ω1 * (ΔOI / Vol_24h) + ω2 * (FR_curr / FR_avg) + ω3 * α`
- **Komponen:**
  - `P_market`: Harga mark price terakhir
  - `P_vwap`: VWAP 24 jam
  - `ΔOI`: Perubahan Open Interest dalam 1 jam terakhir
  - `Vol_24h`: Volume perdagangan 24 jam
  - `FR_curr`: Funding Rate saat ini
  - `FR_avg`: Rata-rata Funding Rate 7 hari terakhir
  - `α`: Selisih harga OKX vs Binance (REST API fallback)
- **Bobot awal (ω):**
  - `ω1 = 0.35` (tekanan leverage)
  - `ω2 = 0.40` (divergensi sentimen)
  - `ω3 = 0.25` (shock arbitrase)
- **Ambang kritis:** Ψ_total > 3.0 dianggap over-extended
- **Frekuensi:** Setiap 10 detik per aset

#### FR-CALC-004: Decay Prediction (Decay_t)
- **Deskripsi:** Sistem HARUS memproyeksikan potensi perubahan harga 10 hari ke depan.
- **Metode:** Regresi linear dari time-series ZF-Score + Ψ_total 30 hari terakhir, diekstrapolasi
- **Output:** Persentase prediksi perubahan harga (`predicted_change_pct`)
- **Frekuensi:** Setiap 1 jam (Celery periodic task)

#### FR-CALC-005: Re-kalibrasi Bobot Adaptif (ω)
- **Deskripsi:** Sistem HARUS melakukan re-kalibrasi koefisien ω setiap 24 jam.
- **Metode:**
  1. Ambil prediksi vs aktual dari 24 jam terakhir
  2. Hitung error rate per komponen
  3. Adjust ω menggunakan gradient descent sederhana: `ω_new = ω_old - learning_rate * gradient`
  4. Constraint: `sum(ω) = 1.0`, setiap `ω >= 0.1`
- **Logging:** Simpan ω lama dan baru di tabel `calibration_log`
- **Trigger:** Celery beat schedule, 00:00 UTC

---

### 2.3 Modul: Asset Swarm Manager

#### FR-ASM-001: Inisialisasi Asset Swarm
- **Deskripsi:** Saat startup, sistem HARUS mengambil daftar 200 aset teratas dari OKX.
- **Kriteria seleksi:** 200 instrument `SWAP` (perpetual) dengan volume 24h tertinggi
- **Refresh daftar:** Setiap 24 jam (aset bisa masuk/keluar daftar)
- **Storage:** Tabel `asset_registry` di TimescaleDB

#### FR-ASM-002: Mode Pemantauan Adaptif
- **Deskripsi:** Sistem HARUS menjalankan dua mode pemantauan berdasarkan ZF-Score.

| Mode | Kondisi | Frekuensi Kalkulasi | Data yang Diproses |
|---|---|---|---|
| **Heartbeat** | ZF-Score < 0.6 | Setiap 60 detik | Ticker + OI saja |
| **Deep Analysis** | ZF-Score >= 0.6 ATAU ΔD_res > 20% dalam 5 menit | Setiap 10 detik | Semua channel |

- **Transisi mode:** Otomatis berdasarkan threshold; log setiap perubahan mode

#### FR-ASM-003: Klasterisasi Aset
- **Deskripsi:** Sistem HARUS mengelompokkan aset berdasarkan korelasi harga.
- **Metode:** Pearson correlation matrix dari return harga 7 hari
- **Threshold klaster:** Korelasi > 0.7 dianggap satu klaster
- **Refresh:** Setiap 6 jam
- **Kegunaan:** Deteksi efek domino (FR-DEF-003)

---

### 2.4 Modul: Dashboard Arsitek (Frontend)

#### FR-DASH-001: Tabel Utama Asset Swarm
- **Deskripsi:** Dashboard HARUS menampilkan tabel 200 aset dengan kolom berikut.
- **Kolom:**

| Kolom | Tipe | Deskripsi |
|---|---|---|
| # | Integer | Urutan berdasarkan ZF-Score descending |
| Aset | String | Simbol (e.g. BTC-USDT-SWAP) |
| Harga | Decimal | Mark price terakhir |
| Δ 24h | Percentage | Perubahan harga 24 jam |
| ZF-Score | Float (0-1) | Indeks kerapuhan, color-coded |
| Ψ_total | Float | Ketegangan struktural |
| D_res | Float (%) | Topological Drift |
| OI | Decimal | Open Interest (USD) |
| FR | Percentage | Funding Rate saat ini |
| Volume 24h | Decimal | Volume dalam USDT |
| Status | Enum | Normal / Waspada / Code Red |
| Mode | Enum | Heartbeat / Deep Analysis |

- **Update:** Real-time via WebSocket (push dari backend)
- **Sorting:** Default ZF-Score descending; kolom lain bisa di-sort
- **Filter:** Berdasarkan status, mode, klaster
- **Pagination:** Virtual scroll (render 50 baris visible, lazy load sisanya)

#### FR-DASH-002: Tabel Prediksi Top 20
- **Deskripsi:** Dashboard HARUS menampilkan tabel 20 aset prediksi berdasarkan dominasi pasar.
- **Logika judul dinamis:**
  - Jika > 60% aset dalam Asset Swarm memiliki Δ24h negatif:
    **"Pasar Dominan Turun — 20 Koin Prediksi Anjlok dalam 10 Hari"**
  - Jika > 60% aset memiliki Δ24h positif:
    **"Pasar Dominan Naik — 20 Koin Prediksi Naik dalam 10 Hari"**
  - Jika netral (40-60%):
    **"Pasar Netral — 20 Koin dengan Potensi Pergerakan Tertinggi dalam 10 Hari"**
- **Kolom:** #, Aset, Harga, ZF-Score, Ψ_total, D_res, Prediksi 10 Hari (%)
- **Urutan:** Berdasarkan potensi pergerakan tertinggi (absolute `predicted_change_pct` descending)
- **Kriteria masuk (mode turun):** ZF-Score > 0.85, Liquidity Void, d²P/dt² < 0
- **Kriteria masuk (mode naik):** ZF-Score < 0.3, volume surge, d²P/dt² > 0

#### FR-DASH-003: Visualisasi Order Book Depth
- **Deskripsi:** Dashboard HARUS menampilkan visualisasi depth chart per aset.
- **Tipe chart:** Area chart mirrored (Bid kiri, Ask kanan)
- **Data:** 20 level bid/ask dari Order Book
- **Highlight:** Liquidity clusters (volume > 3x rata-rata level)
- **Update:** Real-time

#### FR-DASH-004: Liquidation Heatmap
- **Deskripsi:** Dashboard HARUS menampilkan heatmap zona likuidasi.
- **Data:** Estimasi liquidation levels berdasarkan OI dan leverage distribution
- **Visualisasi:** Gradient color overlay pada price chart (merah = cluster padat)
- **Update:** Setiap 5 menit

#### FR-DASH-005: Funding Rate Chart
- **Deskripsi:** Dashboard HARUS menampilkan chart historis Funding Rate per aset.
- **Tipe:** Line chart
- **Rentang:** 7 hari terakhir
- **Marker:** Highlight saat FR > 2x FR_avg (extreme)

#### FR-DASH-006: Tabel Komparasi Sesi
- **Deskripsi:** Dashboard HARUS menampilkan perbandingan ZF-Score antara sesi sebelumnya dan sesi saat ini.
- **Kolom:** Aset, ZF-Score (sebelumnya), ZF-Score (sekarang), Δ ZF-Score, Status Transisi
- **Status Transisi:**
  - ↑ Memburuk (ZF-Score naik > 0.05)
  - ↓ Membaik (ZF-Score turun > 0.05)
  - → Stabil (perubahan < 0.05)
- **Tampilkan:** Hanya aset dengan perubahan signifikan (> 0.05), sorted by |Δ| descending

#### FR-DASH-007: Status Indikator Global
- **Deskripsi:** Dashboard HARUS menampilkan status keseluruhan pasar di header.
- **Indikator:**
  - Jumlah aset per status (Normal / Waspada / Code Red)
  - Dominasi pasar (% naik vs % turun)
  - Rata-rata ZF-Score seluruh Asset Swarm
  - Status Circuit Breaker (Aktif / Nonaktif)
  - Timestamp update terakhir
- **Visual:** Badge/pill dengan warna (hijau/kuning/merah)

#### FR-DASH-008: Autentikasi & Multi-User
- **Deskripsi:** Dashboard HARUS mendukung autentikasi multi-user via Google OAuth 2.0.
- **Metode:** Google Sign-In (OAuth 2.0 Authorization Code Flow)
- **Flow:**
  1. User klik "Login with Google" di halaman login
  2. Redirect ke Google consent screen
  3. Google callback dengan authorization code
  4. Backend tukar code → access token → ambil profil user (email, nama, avatar)
  5. Jika email belum terdaftar: auto-create user dengan role `architect`
  6. Generate JWT token (access + refresh)
- **Session:** JWT access token expire 1 jam, refresh token 7 hari
- **Roles:**

| Role | Kode | Deskripsi |
|---|---|---|
| Super Admin | `super_admin` | Akses penuh: kelola user, konfigurasi sistem, fitur toggle |
| Arsitek | `architect` | Dashboard, input API key, alert, prediksi, Mode Demo (paper trading) |

> **Catatan:** Mode Demo bukan role terpisah — ini fitur paper trading yang tersedia untuk semua user yang sudah login (lihat FR-DEMO-001).

- **Super Admin pertama:** Di-seed saat initial setup via env var `SUPER_ADMIN_EMAIL`
- **CORS:** Whitelist domain dashboard + Google OAuth redirect URI

---

### 2.5 Modul: Memory Buffer Sesi (MBS)

#### FR-MBS-001: Auto-Save Otonom
- **Deskripsi:** Sistem HARUS menyimpan snapshot status seluruh Asset Swarm secara berkala.
- **Data yang disimpan per aset:**
```json
{
  "symbol": "BTC-USDT-SWAP",
  "timestamp": "2026-06-28T12:00:00Z",
  "zf_score": 0.72,
  "psi_total": 2.15,
  "d_res": 3.45,
  "price": 67234.50,
  "oi": 1250000000,
  "funding_rate": 0.0008,
  "volume_24h": 5600000000,
  "mode": "deep_analysis",
  "status": "waspada",
  "cluster_id": 3,
  "omega_weights": {"w1": 0.35, "w2": 0.40, "w3": 0.25}
}
```
- **Frekuensi:** Setiap 5 menit (batch insert ke TimescaleDB hypertable)
- **Retensi snapshot:** 30 hari (auto-purge via TimescaleDB retention policy)

#### FR-MBS-002: Auto-Journaling
- **Deskripsi:** Saat proses shutdown (graceful), sistem HARUS membuat ringkasan sesi.
- **Isi journal:**
  - Timestamp mulai dan selesai sesi
  - Rata-rata ZF-Score per klaster
  - Daftar aset Code Red
  - Jumlah alert yang dikirim
  - Perubahan ω selama sesi
  - Error count
- **Storage:** Tabel `session_journals`

#### FR-MBS-003: Auto-Load & Merge
- **Deskripsi:** Saat startup, sistem HARUS memuat data sesi terakhir dan merge dengan data live.
- **Prosedur:**
  1. Load snapshot terakhir dari `asset_snapshots` (per aset, row terakhir)
  2. Bandingkan dengan data live dari OKX
  3. Jika |ZF-Score_snapshot - ZF-Score_live| > 0.2: flag "Resonance Mismatch"
  4. Populate dashboard dengan data merged
  5. Log merge result ke `session_journals`

---

### 2.6 Modul: Anomaly Detection & Cross-Validation

#### FR-ANOM-001: Divergensi Multi-Sumber
- **Deskripsi:** Sistem HARUS mendeteksi divergensi antara indikator.
- **Rules:**

| Kondisi | Status | Aksi |
|---|---|---|
| Harga ↑ + Volume ↓ + OI ↑ | Waspada | Naikkan sensitivitas D_res threshold |
| Harga ↓ + FR sangat positif + OI ↑ | Waspada | Alert: potensi long squeeze |
| Harga stabil + OI ↓↓ drastis | Waspada | Alert: posisi sedang di-unwind |
| ZF-Score > 0.85 + Liquidity Void + d²P/dt² < 0 | Code Red (jika 3 sesi) | Kandidat prediksi disintegrasi |

#### FR-ANOM-002: Validasi Drift
- **Deskripsi:** Sistem HARUS memvalidasi apakah Topological Drift yang terdeteksi signifikan.
- **Metode:** Z-score dari D_res terhadap distribusi D_res 30 hari
- **Threshold:** |Z| > 2.0 dianggap signifikan (bukan noise)

#### FR-ANOM-003: Filtering Engine (Top 20 Kandidat)
- **Deskripsi:** Sistem HARUS menyaring 20 aset kandidat disintegrasi/kenaikan.
- **Kriteria mode turun:**
  1. ZF-Score > 0.85
  2. Volume downtrend (volume hari ini < 70% volume rata-rata 7 hari)
  3. d²P/dt² < 0 (turunan kedua harga negatif — percepatan penurunan)
- **Kriteria mode naik:**
  1. ZF-Score < 0.3
  2. Volume surge (volume hari ini > 150% volume rata-rata 7 hari)
  3. d²P/dt² > 0 (percepatan kenaikan)
- **Ranking:** `|predicted_change_pct|` descending

#### FR-ANOM-004: Protokol Code Red
- **Deskripsi:** Sistem HARUS mengeluarkan status Code Red jika aset memenuhi semua kriteria disintegrasi selama 3 sesi berturut-turut.
- **Definisi sesi:** 1 sesi = 8 jam (selaras dengan siklus Funding Rate OKX)
- **Tracking:** Tabel `code_red_tracker` dengan counter per aset
- **Aksi:** Push alert Telegram + visual badge merah di dashboard

---

### 2.6a Modul: On-Chain Data Integration (Phase 2)

#### FR-ONCHAIN-001: Koneksi On-Chain Data Provider
- **Deskripsi:** Sistem HARUS menarik data on-chain dari provider eksternal.
- **Provider:** Glassnode / Santiment / API alternatif (configurable)
- **Data yang diambil:**

| Metrik | Deskripsi | Kegunaan |
|---|---|---|
| Exchange Inflow/Outflow | Volume aset masuk/keluar bursa | Indikasi akumulasi vs distribusi |
| Whale Transaction Count | Jumlah transaksi > $100K | Indikasi pergerakan pemain besar |
| Supply on Exchange | Persentase supply yang ada di bursa | Tekanan jual potensial |
| Active Addresses | Jumlah alamat aktif 24h | Proxy aktivitas jaringan |

- **Frekuensi polling:** Setiap 5-15 menit (on-chain data tidak real-time)
- **Caching:** Redis, TTL sesuai frekuensi polling per metrik
- **Fallback:** Jika provider tidak tersedia, metrik on-chain di-set `null` — sistem tetap berjalan tanpa input ini (graceful degradation)
- **Config:** `ONCHAIN_PROVIDER`, `ONCHAIN_API_KEY` via environment variable

#### FR-ONCHAIN-002: Divergensi On-Chain vs Harga
- **Deskripsi:** Sistem HARUS mendeteksi divergensi antara data on-chain dan pergerakan harga.
- **Rules:**

| Kondisi | Interpretasi | Aksi |
|---|---|---|
| Harga ↑ + Exchange Inflow ↑↑ | Distribusi terselubung (bandar jual) | Naikkan sensitivitas D_res |
| Harga ↓ + Exchange Outflow ↑↑ | Akumulasi (bandar beli) | Turunkan ZF-Score dampening |
| Harga stabil + Whale Tx ↑↑ | Persiapan pergerakan besar | Alert: "Whale Activity Detected" |

- **Output:** Flag `onchain_divergence: bool` + `onchain_signal: bullish|bearish|neutral` per aset
- **Integrasi:** Menjadi input tambahan FR-ANOM-001 (Divergensi Multi-Sumber)

---

### 2.6b Modul: Sentiment Feed Integration (Phase 2)

#### FR-SENT-001: Koneksi Sentiment Data Provider
- **Deskripsi:** Sistem HARUS menarik data sentimen dari social listener API.
- **Provider:** LunarCrush / Santiment Social / API alternatif (configurable)
- **Data yang diambil:**

| Metrik | Deskripsi | Kegunaan |
|---|---|---|
| Sentiment Score | Skor sentimen agregat (-1 to +1) | Mood pasar keseluruhan |
| Social Volume | Jumlah mention di social media | Hype/panic indicator |
| Social Dominance | % share mention vs total crypto mentions | Attention shift detection |

- **Frekuensi polling:** Setiap 15-30 menit
- **Caching:** Redis, TTL 900s (15 menit)
- **Fallback:** Jika provider tidak tersedia, metrik sentimen di-set `null` — graceful degradation
- **Config:** `SENTIMENT_PROVIDER`, `SENTIMENT_API_KEY` via environment variable

#### FR-SENT-002: Divergensi Sentimen vs Harga
- **Deskripsi:** Sistem HARUS mendeteksi divergensi antara sentimen sosial dan pergerakan harga.
- **Rules:**

| Kondisi | Interpretasi | Aksi |
|---|---|---|
| Harga ↑ + Sentiment sangat negatif | Rally tanpa dukungan publik — rapuh | Naikkan ZF-Score sensitivity |
| Harga ↓ + Sentiment sangat positif | Panic sell bertentangan dengan crowd — potensi rebound | Alert: "Sentiment Divergence" |
| Social Volume spike > 5x rata-rata | Hype/FUD ekstrem | Naikkan sensitivitas semua threshold |

- **Output:** Flag `sentiment_divergence: bool` + `sentiment_signal: bullish|bearish|neutral` per aset
- **Integrasi:** Menjadi input tambahan FR-ANOM-001 (Divergensi Multi-Sumber)

---

### 2.7 Modul: Order Book Analysis

#### FR-OB-001: Depth Mapping
- **Deskripsi:** Sistem HARUS menghitung rasio kekuatan Bid vs Ask.
- **Metrik:**
  - `bid_depth_ratio = sum(bid_volume[0:10]) / sum(ask_volume[0:10])` (10 level teratas)
  - `bid_depth_ratio < 0.5`: Indikasi pelemahan (bearish)
  - `bid_depth_ratio > 2.0`: Indikasi penguatan (bullish)
- **Frekuensi:** Real-time (setiap update order book)

#### FR-OB-002: Spoofing Detection
- **Deskripsi:** Sistem HARUS mendeteksi order spoofing.
- **Metode:**
  1. Track setiap order yang muncul di level harga ±0.5% dari mark price
  2. Jika order > 10x rata-rata volume di level tersebut DAN dibatalkan dalam < 3 detik: flag sebagai spoof
  3. Hitung `spoof_rate = spoof_count / total_orders` per 5 menit
  4. Jika `spoof_rate > 0.3`: alert spoofing terdeteksi
- **Output:** Boolean flag `is_spoofing_active` per aset

#### FR-OB-003: Liquidity Clustering
- **Deskripsi:** Sistem HARUS mengidentifikasi cluster likuiditas (magnetic points).
- **Metode:** Identifikasi level harga dengan volume > 3 standar deviasi di atas rata-rata
- **Output:** List of `{price_level, volume, type: "bid"|"ask", strength: float}`
- **Frekuensi:** Setiap 30 detik

#### FR-OB-004: Order Flow Imbalance (OFI)
- **Deskripsi:** Sistem HARUS menghitung OFI real-time.
- **Rumus:** `OFI = Σ(bid_volume_change) - Σ(ask_volume_change)` per interval 10 detik
- **Smoothing:** Exponential Moving Average 30 periode
- **Output:** Float, positif = buying pressure dominan, negatif = selling pressure dominan

#### FR-OB-005: Slippage Calculator
- **Deskripsi:** Sistem HARUS menghitung estimasi slippage untuk ukuran order tertentu.
- **Input:** `order_size_usd`, `side` (buy/sell), order book snapshot
- **Metode:** Walk the book — simulasi eksekusi order terhadap depth yang tersedia
- **Output:** `{estimated_avg_price, slippage_pct, levels_consumed}`

---

### 2.8 Modul: Protokol Pertahanan Sistemik

#### FR-DEF-001: Circuit Breaker
- **Deskripsi:** Sistem HARUS membekukan seluruh eksekusi saat kondisi kritis.
- **Trigger:**
  1. ZF-Score > 0.99 pada aset yang sedang memiliki posisi terbuka
  2. Flash crash: harga berubah > 10% dalam 1 menit
  3. Data feed loss: packet loss > 15% selama > 30 detik
  4. Spoofing global: > 50% aset dalam Asset Swarm memiliki `is_spoofing_active = true`
- **Aksi:**
  1. Set flag `circuit_breaker_active = true`
  2. Block semua eksekusi API (return 423 Locked)
  3. Kirim alert Telegram: "CIRCUIT BREAKER AKTIF"
  4. Log event ke `system_events`
- **Deaktivasi:** Manual oleh Arsitek via dashboard ATAU otomatis setelah 30 menit jika kondisi kembali normal

#### FR-DEF-002: Mode Dingin
- **Deskripsi:** Sistem HARUS mengunci trading interface jika over-trading terdeteksi.
- **Definisi over-trading:**
  - > 10 eksekusi dalam 1 jam
  - ATAU > 3 eksekusi yang menghasilkan loss berturut-turut
- **Aksi:** Lock trading selama 2 jam + alert Telegram
- **Override:** Arsitek bisa unlock manual dengan konfirmasi 2 kali

#### FR-DEF-003: Deteksi Efek Domino
- **Deskripsi:** Sistem HARUS mendeteksi potensi efek domino lintas aset.
- **Trigger:** > 50 aset dalam satu klaster mengalami Liquidity Void bersamaan
  (Liquidity Void = volume drop > 60% dalam 1 jam)
- **Aksi:** Aktifkan Protokol Pertahanan Sistemik — alert + rekomendasi de-leverage

---

### 2.9 Modul: Notifikasi & Alert System

#### FR-NOTIF-001: Telegram Bot Integration
- **Deskripsi:** Sistem HARUS mengirim notifikasi via Telegram Bot API.
- **Endpoint:** `https://api.telegram.org/bot{token}/sendMessage`
- **Config:** `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` via environment variable
- **Rate limit:** Max 30 pesan per detik (Telegram limit)

#### FR-NOTIF-002: Tipe Alert

| Prioritas | Tipe | Pesan |
|---|---|---|
| 🔴 CRITICAL | Circuit Breaker | "⚠️ CIRCUIT BREAKER AKTIF — {reason}" |
| 🔴 CRITICAL | Code Red | "🔴 CODE RED: {symbol} — ZF-Score {score} selama 3 sesi" |
| 🔴 CRITICAL | Black Swan | "🚨 BLACK SWAN DETECTED — Protokol Pertahanan Aktif" |
| 🟡 WARNING | Waspada | "⚠️ {symbol} memasuki fase kritis — ZF-Score {score}" |
| 🟡 WARNING | Spoofing | "⚠️ Spoofing terdeteksi pada {symbol}" |
| 🟡 WARNING | Resonance Mismatch | "⚠️ Data mismatch pada {symbol} — perlu perhatian" |
| 🟢 INFO | Prediksi Update | "📊 Update prediksi 10 hari: {count} aset berubah" |
| 🟢 INFO | Kalibrasi | "🔄 Re-kalibrasi ω selesai — ω1={w1}, ω2={w2}, ω3={w3}" |
| 🟢 INFO | Deploy | "✅ Deploy berhasil / ❌ Deploy gagal" |

#### FR-NOTIF-003: Anti-Spam
- **Deskripsi:** Sistem HARUS mencegah spam alert.
- **Rules:**
  - Alert identik (tipe + symbol sama) tidak dikirim ulang dalam 15 menit
  - Max 5 alert per menit
  - Akumulasi: jika > 10 aset Waspada bersamaan, kirim 1 ringkasan, bukan 10 pesan

---

### 2.10 Modul: Self-Learning & Feedback Loop

#### FR-LEARN-001: Error Logging
- **Deskripsi:** Sistem HARUS mencatat setiap prediksi vs aktual.
- **Data yang dicatat:**
```json
{
  "symbol": "BTC-USDT-SWAP",
  "predicted_at": "2026-06-28T00:00:00Z",
  "prediction_type": "decay_10d",
  "predicted_value": -12.5,
  "actual_value": -8.3,
  "error": 4.2,
  "omega_snapshot": {"w1": 0.35, "w2": 0.40, "w3": 0.25}
}
```
- **Storage:** Tabel `prediction_log` (TimescaleDB hypertable)

#### FR-LEARN-002: False Signal Dampening
- **Deskripsi:** Jika aset menghasilkan false signal > 3 kali dalam 7 hari, sistem HARUS menurunkan bobot resonansi aset tersebut.
- **Definisi false signal:** Prediksi anjlok (ZF-Score > 0.85) tetapi harga justru naik > 5%
- **Aksi:** Multiply ZF-Score aset tersebut dengan `dampening_factor = 0.8` selama 7 hari
- **Recovery:** Otomatis setelah 7 hari tanpa false signal

---

### 2.11 Modul: User Management & Super Admin

#### FR-USER-001: Google OAuth 2.0 Integration
- **Deskripsi:** Sistem HARUS mendukung login via Google OAuth 2.0.
- **Library:** `authlib` (Python) untuk backend OAuth flow
- **Google APIs:**
  - Authorization endpoint: `https://accounts.google.com/o/oauth2/v2/auth`
  - Token endpoint: `https://oauth2.googleapis.com/token`
  - Userinfo endpoint: `https://www.googleapis.com/oauth2/v3/userinfo`
- **Scopes:** `openid email profile`
- **Config:** `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` via environment variable
- **Redirect URI:** `https://{domain}/api/auth/google/callback`

#### FR-USER-002: Auto-Registration
- **Deskripsi:** User baru yang login via Google HARUS otomatis terdaftar.
- **Flow:**
  1. Cek apakah email sudah ada di tabel `users`
  2. Jika belum: create user baru dengan `role = 'architect'`, `status = 'active'`
  3. Jika sudah: update `last_login`, cek `status` (jika suspended/banned → tolak login)
  4. Generate JWT (access token 1 jam + refresh token 7 hari)
- **Data yang disimpan dari Google:** email, display_name, avatar_url, google_id

#### FR-USER-003: Role-Based Access Control (RBAC)
- **Deskripsi:** Sistem HARUS membatasi akses berdasarkan role user.
- **Permission Matrix:**

| Fitur | Arsitek (tanpa API key) | Arsitek (dengan API key) | Super Admin |
|---|---|---|---|
| Lihat dashboard (200 aset, real-time) | ✅ | ✅ | ✅ |
| Tabel Prediksi Top 20 | ✅ | ✅ | ✅ |
| Order Book Detail | ✅ | ✅ | ✅ |
| Liquidation Heatmap | ✅ | ✅ | ✅ |
| Komparasi Sesi | ✅ | ✅ | ✅ |
| Mode Demo (paper trading) | ✅ | ✅ | ✅ |
| Input API key OKX | ✅ | ✅ | ✅ |
| Terima alert Telegram | ✅ | ✅ | ✅ |
| Mode Live (eksekusi nyata, Phase 3) | ❌ | ✅ | ✅ |
| Kelola user (list, suspend, ban, promote) | ❌ | ❌ | ✅ |
| Konfigurasi sistem (toggle fitur, parameter) | ❌ | ❌ | ✅ |
| Reset Circuit Breaker | ❌ | ❌ | ✅ |
| Trigger re-kalibrasi manual | ❌ | ❌ | ✅ |
| Lihat semua API key user (masked) | ❌ | ❌ | ✅ |

- **Implementasi:** Middleware decorator `@require_role("super_admin")` pada endpoint yang dibatasi

#### FR-USER-004: Super Admin Management
- **Deskripsi:** Super Admin HARUS bisa mengelola user.
- **Aksi yang tersedia:**

| Aksi | Endpoint | Deskripsi |
|---|---|---|
| List users | GET `/api/admin/users` | Daftar semua user + status + role |
| Get user detail | GET `/api/admin/users/{id}` | Detail user termasuk API key (masked) |
| Update status | PATCH `/api/admin/users/{id}/status` | Set active / suspended / banned |
| Update role | PATCH `/api/admin/users/{id}/role` | Promote/demote (architect ↔ super_admin) |
| Delete user | DELETE `/api/admin/users/{id}` | Hard delete user + API key |
| System config | GET/PUT `/api/admin/config` | Toggle fitur (demo mode, dll) |

- **Constraint:** Minimal 1 Super Admin harus selalu ada (tidak bisa demote diri sendiri jika satu-satunya)
- **Audit:** Semua aksi admin dicatat di `system_events` dengan `event_type = 'admin_action'`

#### FR-USER-005: Super Admin Seeding
- **Deskripsi:** Super Admin pertama HARUS dibuat saat initial setup.
- **Metode:** Environment variable `SUPER_ADMIN_EMAIL=admin@example.com`
- **Flow startup:**
  1. Cek apakah ada user dengan `role = 'super_admin'`
  2. Jika tidak ada: create placeholder user dengan email dari env var, `role = 'super_admin'`
  3. Saat user tersebut login via Google untuk pertama kali, data Google (nama, avatar) akan di-merge
- **Fallback:** Jika env var tidak di-set, user pertama yang login otomatis menjadi Super Admin

---

### 2.12 Modul: API Key Management

#### FR-APIKEY-001: Input API Key OKX
- **Deskripsi:** Arsitek HARUS bisa menginput API key OKX pribadi.
- **Data yang disimpan:**
  - `api_key`: API Key
  - `secret_key`: Secret Key
  - `passphrase`: Passphrase
  - `label`: Label deskriptif (opsional)
- **Endpoint:** POST `/api/user/api-keys`
- **Validasi saat simpan:**
  1. Test call ke OKX REST API: `GET /api/v5/account/balance` dengan credential yang diberikan
  2. Jika berhasil: simpan + catat permission level (read-only / trade / withdraw)
  3. Jika gagal: return error dengan pesan dari OKX
- **Rekomendasi:** Sistem HARUS memperingatkan user jika API key memiliki withdraw permission

#### FR-APIKEY-002: Enkripsi API Key
- **Deskripsi:** API key HARUS disimpan terenkripsi.
- **Algoritma:** AES-256-GCM (symmetric encryption)
- **Key management:**
  - Encryption key dari environment variable `API_KEY_ENCRYPTION_SECRET`
  - Setiap API key di-encrypt dengan unique nonce (IV)
- **Display:** API key hanya ditampilkan masked: `sk-****...7f3a` (4 karakter terakhir)
- **Decrypt:** Hanya saat digunakan untuk API call ke OKX (in-memory, tidak pernah di-log)

#### FR-APIKEY-003: CRUD API Key
- **Deskripsi:** User HARUS bisa mengelola API key miliknya.
- **Endpoints:**

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| POST | `/api/user/api-keys` | Tambah API key baru (max 3 per user) | Arsitek+ |
| GET | `/api/user/api-keys` | List API key milik sendiri (masked) | Arsitek+ |
| DELETE | `/api/user/api-keys/{id}` | Hapus API key | Arsitek+ |
| POST | `/api/user/api-keys/{id}/test` | Test koneksi API key | Arsitek+ |

- **Limit:** Maksimal 3 API key per user (misalnya: 1 read-only, 1 trade, 1 backup)
- **Ownership:** User hanya bisa melihat/hapus API key miliknya sendiri (kecuali Super Admin)

---

### 2.13 Modul: Mode Demo (Paper Trading)

#### FR-DEMO-001: Saldo Virtual
- **Deskripsi:** Setiap user yang login HARUS memiliki akun demo dengan saldo virtual.
- **Saldo default:** 10.000 USDT (configurable oleh Super Admin via `system_config`)
- **Reset:** User bisa reset saldo virtual ke default kapan saja
- **Isolasi:** Saldo dan posisi demo **terpisah sepenuhnya** dari mode live
- **Tidak perlu API key OKX** — mode demo menggunakan data harga real-time dari ingestion engine yang sudah berjalan

#### FR-DEMO-002: Open/Close Posisi Virtual
- **Deskripsi:** User HARUS bisa membuka dan menutup posisi virtual menggunakan harga pasar real-time.
- **Tipe order:**
  - Market order (eksekusi instan di mark price saat itu)
  - Limit order (eksekusi saat harga mencapai target) — opsional, Phase 2
- **Parameter posisi:**
  - Symbol (dari 200 aset Asset Swarm)
  - Side: Long / Short
  - Size (dalam USDT)
  - Leverage: 1x - 10x (maksimal, dibatasi untuk edukasi risiko)
- **Eksekusi:** Tidak ada order nyata ke OKX; posisi dicatat di tabel `demo_positions`
- **Harga eksekusi:** Mark price saat order diterima (tanpa simulasi slippage)

#### FR-DEMO-003: Kalkulasi PnL Virtual Real-Time
- **Deskripsi:** Sistem HARUS menghitung PnL posisi demo secara real-time.
- **Rumus:**
  - Long: `PnL = (mark_price_now - entry_price) * size * leverage`
  - Short: `PnL = (entry_price - mark_price_now) * size * leverage`
- **Liquidation virtual:** Jika unrealized loss >= margin yang dialokasikan, posisi otomatis di-close (liquidation virtual)
- **Update:** PnL di-push via WebSocket ke dashboard, sama seperti data aset lainnya
- **Fee simulasi:** Trading fee 0.05% per open/close (sesuai OKX taker fee tier 1)

#### FR-DEMO-004: Histori Transaksi Demo
- **Deskripsi:** Seluruh transaksi demo HARUS tersimpan untuk review.
- **Data yang dicatat per transaksi:**
```json
{
  "id": 1,
  "user_id": 5,
  "symbol": "BTC-USDT-SWAP",
  "side": "long",
  "size_usdt": 1000.00,
  "leverage": 5,
  "entry_price": 67234.50,
  "exit_price": 68100.00,
  "pnl": 64.32,
  "fee": 1.00,
  "status": "closed",
  "opened_at": "2026-06-28T10:00:00Z",
  "closed_at": "2026-06-28T14:30:00Z",
  "close_reason": "manual"
}
```
- **Close reason:** `manual` | `take_profit` | `stop_loss` | `liquidation`
- **Retensi:** 90 hari

#### FR-DEMO-005: Dashboard Demo
- **Deskripsi:** Dashboard HARUS menyediakan panel mode demo yang terintegrasi.
- **UI Elements:**
  - Toggle switch "Demo / Live" di header (Live hanya aktif jika user punya API key)
  - Saldo virtual + unrealized PnL ditampilkan di panel atas
  - Badge "MODE DEMO" warna kuning di header saat aktif
  - Daftar posisi terbuka (demo) dengan PnL real-time
  - Histori transaksi demo (tabel, sortable, filterable)
  - Tombol "Open Position" — form: symbol, side, size, leverage
  - Tombol "Reset Saldo" dengan konfirmasi
- **Akses penuh:** User demo tetap melihat **seluruh 200 aset real-time**, semua chart, semua prediksi — hanya eksekusi yang virtual
- **Statistik demo:** Win rate, total PnL, rata-rata holding time, best/worst trade

#### FR-DEMO-006: Transisi Demo ↔ Live
- **Deskripsi:** User HARUS bisa beralih antara mode Demo dan Live.
- **Kondisi Live aktif:** User memiliki minimal 1 API key OKX yang valid
- **Kondisi Demo aktif:** Selalu tersedia untuk semua user yang login
- **Switching:** Tidak mempengaruhi posisi yang sudah terbuka di mode lain (posisi demo tetap ada saat switch ke live, dan sebaliknya)
- **Visual:** Indikator mode yang jelas (warna background berbeda: kuning demo, hijau live)

---

## 3. Kebutuhan Non-Fungsional

### NFR-001: Performa

| Metrik | Target | Metode Pengukuran |
|---|---|---|
| Latency ingestion → dashboard | < 500ms (P95) | Timestamp diff: data masuk vs WebSocket push |
| Kalkulasi ZF-Score per aset | < 100ms | Profiling Celery task |
| Dashboard initial load | < 3 detik | Lighthouse / browser timing |
| API response time (REST) | < 200ms (P95) | FastAPI middleware timing |
| WebSocket message throughput | > 1000 msg/detik | Load test |

### NFR-002: Ketersediaan
- **Target:** 99.5% uptime (max downtime ~3.6 jam/bulan)
- **Strategi:** Docker restart policy `unless-stopped`, health check endpoint
- **Monitoring:** `/api/health` endpoint, UptimeRobot external check

### NFR-003: Skalabilitas
- **Horizontal:** Tidak diperlukan di MVP (single VPS)
- **Vertikal:** Sistem HARUS berfungsi dalam constraint 4 core / ~10GB RAM (shared VPS)
- **Degradation:** Jika RAM > 80%, otomatis switch semua aset ke Heartbeat Mode

### NFR-004: Keamanan
- **Transport:** SSL/TLS via Cloudflare (end-to-end encryption)
- **Authentication:** JWT untuk dashboard, API key untuk programmatic access
- **Secrets management:** Environment variable via `.env` file (Docker Compose)
- **OKX API key:** Read-only permission (jangan beri trade permission di MVP)
- **CORS:** Whitelist domain dashboard saja
- **Input validation:** Semua API endpoint HARUS validate input (Pydantic models)

### NFR-005: Data Integrity
- **Database:** TimescaleDB dengan WAL (Write-Ahead Log) aktif
- **Backup:** Daily pg_dump ke local storage (Celery periodic task)
- **Retensi:** Tick data 30 hari, agregat unlimited, logs 90 hari

### NFR-006: Observabilitas
- **Logging:** Structured JSON logging (Python `structlog`)
- **Log levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log rotation:** Max 100MB per file, 5 file retained
- **Health endpoint:** `GET /api/health` return:
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

---

## 4. Desain Database

### 4.1 Tabel Utama

#### `asset_registry`
```sql
CREATE TABLE asset_registry (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,        -- e.g. BTC-USDT-SWAP
    base_currency VARCHAR(20) NOT NULL,        -- e.g. BTC
    inst_type VARCHAR(10) DEFAULT 'SWAP',
    is_active BOOLEAN DEFAULT true,
    cluster_id INTEGER,
    dampening_factor FLOAT DEFAULT 1.0,
    dampening_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `asset_snapshots` (TimescaleDB Hypertable)
```sql
CREATE TABLE asset_snapshots (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    zf_score FLOAT NOT NULL,
    psi_total FLOAT NOT NULL,
    d_res FLOAT NOT NULL,
    oi DECIMAL(20, 2),
    funding_rate FLOAT,
    volume_24h DECIMAL(20, 2),
    bid_depth_ratio FLOAT,
    ofi FLOAT,
    mode VARCHAR(20),                          -- heartbeat | deep_analysis
    status VARCHAR(20),                        -- normal | waspada | code_red
    predicted_change_pct FLOAT
);
SELECT create_hypertable('asset_snapshots', 'time');
-- Retensi: 30 hari
SELECT add_retention_policy('asset_snapshots', INTERVAL '30 days');
-- Agregat: continuous aggregate untuk data harian
```

#### `asset_daily_aggregates` (Continuous Aggregate)
```sql
CREATE MATERIALIZED VIEW asset_daily_aggregates
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    symbol,
    AVG(zf_score) AS avg_zf_score,
    MAX(zf_score) AS max_zf_score,
    AVG(psi_total) AS avg_psi_total,
    FIRST(price, time) AS open_price,
    LAST(price, time) AS close_price,
    MAX(price) AS high_price,
    MIN(price) AS low_price,
    AVG(volume_24h) AS avg_volume
FROM asset_snapshots
GROUP BY day, symbol;
-- Retensi: unlimited
```

#### `prediction_log`
```sql
CREATE TABLE prediction_log (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(30) NOT NULL,      -- decay_10d | zf_score_change
    predicted_value FLOAT NOT NULL,
    actual_value FLOAT,                        -- NULL sampai diverifikasi
    error FLOAT,
    omega_w1 FLOAT,
    omega_w2 FLOAT,
    omega_w3 FLOAT
);
SELECT create_hypertable('prediction_log', 'time');
SELECT add_retention_policy('prediction_log', INTERVAL '90 days');
```

#### `calibration_log`
```sql
CREATE TABLE calibration_log (
    id SERIAL PRIMARY KEY,
    calibrated_at TIMESTAMPTZ DEFAULT NOW(),
    omega_w1_old FLOAT NOT NULL,
    omega_w2_old FLOAT NOT NULL,
    omega_w3_old FLOAT NOT NULL,
    omega_w1_new FLOAT NOT NULL,
    omega_w2_new FLOAT NOT NULL,
    omega_w3_new FLOAT NOT NULL,
    avg_error_before FLOAT,
    avg_error_after FLOAT,
    samples_used INTEGER
);
```

#### `code_red_tracker`
```sql
CREATE TABLE code_red_tracker (
    symbol VARCHAR(50) PRIMARY KEY,
    consecutive_sessions INTEGER DEFAULT 0,
    first_triggered_at TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT false
);
```

#### `session_journals`
```sql
CREATE TABLE session_journals (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,
    avg_zf_score FLOAT,
    code_red_count INTEGER,
    alerts_sent INTEGER,
    errors_count INTEGER,
    omega_changes JSONB,
    summary TEXT
);
```

#### `system_events`
```sql
CREATE TABLE system_events (
    time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,           -- circuit_breaker | mode_dingin | black_swan | deploy
    severity VARCHAR(20) NOT NULL,             -- critical | warning | info
    symbol VARCHAR(50),                        -- NULL untuk event global
    details JSONB,
    resolved_at TIMESTAMPTZ
);
SELECT create_hypertable('system_events', 'time');
SELECT add_retention_policy('system_events', INTERVAL '90 days');
```

#### `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(20) NOT NULL DEFAULT 'architect',  -- super_admin | architect
    status VARCHAR(20) NOT NULL DEFAULT 'active',   -- active | suspended | banned
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

#### `user_api_keys`
```sql
CREATE TABLE user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR(100),
    api_key_encrypted BYTEA NOT NULL,            -- AES-256-GCM encrypted
    secret_key_encrypted BYTEA NOT NULL,
    passphrase_encrypted BYTEA NOT NULL,
    nonce BYTEA NOT NULL,                        -- unique IV per row
    api_key_last4 VARCHAR(4) NOT NULL,           -- last 4 chars for display
    permission_level VARCHAR(20),                -- read_only | trade | withdraw
    is_valid BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_tested_at TIMESTAMPTZ,
    CONSTRAINT max_3_keys_per_user CHECK (true)  -- enforced in app layer
);
CREATE INDEX idx_api_keys_user ON user_api_keys(user_id);
```

#### `demo_wallets`
```sql
CREATE TABLE demo_wallets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance DECIMAL(20, 2) NOT NULL DEFAULT 10000.00,  -- saldo virtual USDT
    initial_balance DECIMAL(20, 2) NOT NULL DEFAULT 10000.00,
    total_pnl DECIMAL(20, 2) DEFAULT 0.00,
    total_trades INTEGER DEFAULT 0,
    win_trades INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_reset_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `demo_positions`
```sql
CREATE TABLE demo_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,                 -- long | short
    size_usdt DECIMAL(20, 2) NOT NULL,
    leverage INTEGER NOT NULL DEFAULT 1,
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    margin DECIMAL(20, 2) NOT NULL,            -- size_usdt / leverage
    pnl DECIMAL(20, 2),
    fee DECIMAL(20, 4),
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- open | closed
    close_reason VARCHAR(20),                  -- manual | take_profit | stop_loss | liquidation
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);
CREATE INDEX idx_demo_pos_user ON demo_positions(user_id, status);
CREATE INDEX idx_demo_pos_symbol ON demo_positions(symbol, status);
-- Retensi: 90 hari untuk posisi closed
```

#### `system_config`
```sql
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);
-- Default configs:
-- INSERT INTO system_config VALUES ('demo_mode_enabled', 'true');
-- INSERT INTO system_config VALUES ('demo_initial_balance', '10000');
-- INSERT INTO system_config VALUES ('demo_max_leverage', '10');
```

---

## 5. Desain API

### 5.1 REST Endpoints

#### Autentikasi (Google OAuth)

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/auth/google` | Redirect ke Google consent screen | No |
| GET | `/api/auth/google/callback` | Google OAuth callback, return JWT | No |
| POST | `/api/auth/refresh` | Refresh JWT token | Yes (refresh token) |
| GET | `/api/auth/me` | Profil user saat ini | Yes |
| POST | `/api/auth/logout` | Invalidate refresh token | Yes |

#### User API Key Management

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| POST | `/api/user/api-keys` | Tambah API key OKX (max 3) | Arsitek+ |
| GET | `/api/user/api-keys` | List API key milik sendiri (masked) | Arsitek+ |
| DELETE | `/api/user/api-keys/{id}` | Hapus API key | Arsitek+ |
| POST | `/api/user/api-keys/{id}/test` | Test koneksi API key ke OKX | Arsitek+ |

#### Super Admin

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/admin/users` | List semua user + status + role | Super Admin |
| GET | `/api/admin/users/{id}` | Detail user (termasuk API key masked) | Super Admin |
| PATCH | `/api/admin/users/{id}/status` | Set active/suspended/banned | Super Admin |
| PATCH | `/api/admin/users/{id}/role` | Promote/demote role | Super Admin |
| DELETE | `/api/admin/users/{id}` | Hard delete user + data | Super Admin |
| GET | `/api/admin/config` | Get system config | Super Admin |
| PUT | `/api/admin/config` | Update system config (toggle demo, dll) | Super Admin |
| GET | `/api/admin/stats` | Statistik: jumlah user, aktif, API key count | Super Admin |

#### Demo (Paper Trading)

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/demo/wallet` | Get saldo virtual + statistik trading demo | Yes |
| POST | `/api/demo/wallet/reset` | Reset saldo virtual ke default (10.000 USDT) | Yes |
| GET | `/api/demo/positions` | List posisi demo terbuka (open) | Yes |
| POST | `/api/demo/positions` | Open posisi demo baru (long/short) | Yes |
| POST | `/api/demo/positions/{id}/close` | Close posisi demo secara manual | Yes |
| GET | `/api/demo/history` | Histori posisi demo yang sudah closed | Yes |

#### Asset Swarm

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/assets` | List 200 aset dengan metrik terkini | Yes |
| GET | `/api/assets/{symbol}` | Detail satu aset | Yes |
| GET | `/api/assets/{symbol}/history` | Historis snapshot (query: from, to, interval) | Yes |
| GET | `/api/assets/{symbol}/orderbook` | Order Book depth + analisis | Yes |
| GET | `/api/assets/{symbol}/liquidation-map` | Heatmap data likuidasi | Yes |

#### Prediksi & Analisis

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/predictions/top20` | Top 20 prediksi (auto-detect mode naik/turun) | Yes |
| GET | `/api/predictions/{symbol}` | Prediksi detail per aset | Yes |
| GET | `/api/analysis/correlation-matrix` | Matriks korelasi antar klaster | Yes |
| GET | `/api/analysis/market-dominance` | Statistik dominasi pasar (% naik/turun/netral) | Yes |

#### Sesi & Sistem

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/health` | Health check | No |
| GET | `/api/sessions` | Daftar session journals | Yes |
| GET | `/api/sessions/{id}` | Detail journal sesi | Yes |
| GET | `/api/system/status` | Status Circuit Breaker, Mode Dingin, alert stats | Yes |
| POST | `/api/system/circuit-breaker/reset` | Reset Circuit Breaker manual | Yes |
| POST | `/api/system/cold-mode/unlock` | Unlock Mode Dingin manual | Yes |

#### Kalibrasi

| Method | Path | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/calibration/current` | Bobot ω saat ini | Yes |
| GET | `/api/calibration/history` | Riwayat re-kalibrasi | Yes |
| POST | `/api/calibration/trigger` | Trigger re-kalibrasi manual | Yes |

### 5.2 WebSocket Endpoints

#### `ws://host/ws/dashboard`
- **Auth:** JWT token via query param `?token=xxx`
- **Server → Client messages:**
```json
{"type": "asset_update", "data": {"symbol": "BTC-USDT-SWAP", "price": 67234.5, "zf_score": 0.72, ...}}
{"type": "alert", "data": {"priority": "critical", "type": "code_red", "symbol": "XYZ-USDT-SWAP", ...}}
{"type": "prediction_update", "data": {"title": "Pasar Dominan Turun...", "assets": [...]}}
{"type": "system_status", "data": {"circuit_breaker": false, "cold_mode": false, ...}}
{"type": "session_comparison", "data": {"changes": [...]}}
```
- **Client → Server messages:**
```json
{"type": "subscribe", "symbols": ["BTC-USDT-SWAP"]}
{"type": "unsubscribe", "symbols": ["BTC-USDT-SWAP"]}
```

### 5.3 Response Format Standard
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-06-28T12:00:00Z"
}
```
Error response:
```json
{
  "success": false,
  "data": null,
  "error": {"code": "CIRCUIT_BREAKER_ACTIVE", "message": "Trading is currently frozen"},
  "timestamp": "2026-06-28T12:00:00Z"
}
```

---

## 6. Desain Infrastruktur

### 6.1 Docker Compose Services

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]  # Internal only, proxied via OpenLiteSpeed
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
    ports: ["3000:3000"]  # Internal only
    env_file: .env
    restart: unless-stopped

  db:
    image: timescale/timescaledb:latest-pg16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: zfcore
      POSTGRES_USER: zfcore
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]  # Bind to 127.0.0.1 only
    restart: unless-stopped
    shm_size: '256mb'

  redis:
    image: redis:7-alpine
    volumes: ["redisdata:/data"]
    ports: ["6379:6379"]  # Bind to 127.0.0.1 only
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

volumes:
  pgdata:
  redisdata:
```

### 6.2 Environment Variables (.env.example)

```env
# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=zfcore
DB_USER=zfcore
DB_PASSWORD=changeme

# Redis
REDIS_URL=redis://redis:6379/0

# OKX API (system-level, read-only — untuk data ingestion global)
OKX_API_KEY=
OKX_SECRET_KEY=
OKX_PASSPHRASE=

# Google OAuth 2.0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://zf.yourdomain.com/api/auth/google/callback

# Super Admin (email Google pertama yang jadi super admin)
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

### 6.3 OpenLiteSpeed Proxy Config (CyberPanel)
- **Domain:** Subdomain khusus (e.g. `zf.yourdomain.com`)
- **Proxy rules:**
  - `/api/*` → `http://127.0.0.1:8000`
  - `/ws/*` → `ws://127.0.0.1:8000` (WebSocket proxy)
  - `/*` → `http://127.0.0.1:3000` (Next.js frontend)
- **SSL:** Handled by Cloudflare (Full mode), OpenLiteSpeed hanya HTTP internal
- **WebSocket:** Enable WebSocket proxy di OpenLiteSpeed vhost config

---

## 7. Celery Task Schedule

```python
CELERY_BEAT_SCHEDULE = {
    # Hitung ZF-Score & Ψ_total untuk aset Deep Analysis
    "calculate-deep-analysis": {
        "task": "app.services.tasks.calculate_deep_analysis",
        "schedule": 10.0,  # setiap 10 detik
    },
    # Hitung ZF-Score untuk aset Heartbeat
    "calculate-heartbeat": {
        "task": "app.services.tasks.calculate_heartbeat",
        "schedule": 60.0,  # setiap 60 detik
    },
    # Snapshot MBS
    "save-mbs-snapshot": {
        "task": "app.services.tasks.save_mbs_snapshot",
        "schedule": 300.0,  # setiap 5 menit
    },
    # Prediksi Decay 10 hari
    "calculate-decay-prediction": {
        "task": "app.services.tasks.calculate_decay_prediction",
        "schedule": 3600.0,  # setiap 1 jam
    },
    # Klasterisasi aset
    "recalculate-clusters": {
        "task": "app.services.tasks.recalculate_clusters",
        "schedule": 21600.0,  # setiap 6 jam
    },
    # Re-kalibrasi ω
    "recalibrate-omega": {
        "task": "app.services.tasks.recalibrate_omega",
        "schedule": crontab(hour=0, minute=0),  # 00:00 UTC
    },
    # Refresh daftar aset
    "refresh-asset-registry": {
        "task": "app.services.tasks.refresh_asset_registry",
        "schedule": crontab(hour=0, minute=30),  # 00:30 UTC
    },
    # Database backup
    "daily-db-backup": {
        "task": "app.services.tasks.backup_database",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC
    },
    # Cek likuidasi posisi demo (virtual)
    "check-demo-liquidations": {
        "task": "app.services.tasks.check_demo_liquidations",
        "schedule": 10.0,  # setiap 10 detik
    },
}
```

---

## 8. Traceability Matrix

| Requirement | Bab Buku Besar | PRD Feature | API/Module |
|---|---|---|---|
| FR-ING-001..004 | Bab II, VI | F1 | `ingestion/` |
| FR-CALC-001 | Bab I | F2 | `core/drift.py` |
| FR-CALC-002 | Bab I | F2 | `core/zf_score.py` |
| FR-CALC-003 | Bab III | F2 | `core/psi_total.py` |
| FR-CALC-004 | Bab VII | F2 | `core/decay.py` |
| FR-CALC-005 | Bab III | F11 | `core/calibration.py` |
| FR-ASM-001..003 | Bab VI, VIII | F3 | `core/asset_swarm.py` |
| FR-DASH-001..008 | Bab VII, VIII | F4 | `frontend/` |
| FR-MBS-001..003 | Bab VIII | F5 | `services/mbs.py` |
| FR-ANOM-001..004 | Bab VII | F6 | `analysis/anomaly.py` |
| FR-ONCHAIN-001..002 | Bab VI | F16 | `ingestion/onchain.py` |
| FR-SENT-001..002 | Bab VI | F17 | `ingestion/sentiment.py` |
| FR-OB-001..005 | Bab IV | F7 | `analysis/orderbook.py` |
| FR-DEF-001..003 | Bab III, IX | F8 | `core/defense.py` |
| FR-NOTIF-001..003 | Bab IX | F10 | `services/telegram.py` |
| FR-LEARN-001..002 | Bab III, VI | F11 | `services/feedback.py` |
| FR-USER-001..005 | — | F13 | `api/auth.py`, `api/admin.py` |
| FR-APIKEY-001..003 | — | F14 | `api/api_keys.py`, `services/crypto.py` |
| FR-DEMO-001..004 | — | F15 | `api/demo.py`, `services/demo.py` |

---

## 9. Acceptance Criteria (Phase 1 MVP)

| # | Kriteria | Metode Verifikasi |
|---|---|---|
| AC-01 | WebSocket ke OKX terhubung dan menerima data 200 aset | Log koneksi + data count |
| AC-02 | ZF-Score terhitung untuk seluruh 200 aset | Query `asset_snapshots` count |
| AC-03 | Dashboard menampilkan tabel 200 aset real-time | Manual test browser |
| AC-04 | Tabel prediksi Top 20 muncul dengan judul dinamis | Screenshot test |
| AC-05 | MBS auto-save setiap 5 menit | Query `asset_snapshots` interval |
| AC-06 | Session journal tersimpan saat shutdown | Restart test + query `session_journals` |
| AC-07 | Data sesi sebelumnya ter-load saat startup | Restart test + merge log |
| AC-08 | Alert Telegram terkirim saat ZF-Score > 0.8 | Trigger test + check Telegram |
| AC-09 | Login via Google OAuth berhasil, JWT diterima | Login flow test |
| AC-10 | Health endpoint return OK | `curl /api/health` |
| AC-11 | Latency data → dashboard < 500ms P95 | Timing measurement |
| AC-12 | Sistem berjalan stabil dalam RAM < 10GB | `docker stats` monitoring 24 jam |
| AC-13 | User baru auto-register sebagai Arsitek saat login Google | Login user baru + cek DB |
| AC-14 | Super Admin bisa list, suspend, promote user | Manual test admin panel |
| AC-15 | API key OKX tersimpan terenkripsi, ditampilkan masked | Insert + query + cek DB |
| AC-16 | Mode Demo: user bisa open/close posisi virtual dengan saldo 10.000 USDT | Buka posisi demo + cek PnL real-time |
| AC-17 | RBAC: Arsitek tidak bisa akses endpoint admin | 403 test |
| AC-18 | Demo user bisa akses seluruh dashboard (200 aset, real-time) sama seperti mode live | Bandingkan tampilan demo vs live |
