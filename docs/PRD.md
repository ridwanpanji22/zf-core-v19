# PRD: ZF-Core V19.0 — Protokol Zerotime Trading Platform

## 1. Ringkasan Produk

**Nama:** ZF-Core V19.0 (Protokol Zerotime)
**Tipe:** Platform analisis & eksekusi trading kripto derivatif berbasis AI
**Target Pengguna:** Arsitek (trader profesional) yang membutuhkan analisis pasar derivatif real-time dengan pendekatan kuantitatif
**Bursa Utama:** OKX (Perpetual/Futures)

ZF-Core V19.0 adalah sistem orkestrasi data multi-dimensi yang memantau 200 aset kripto secara simultan, menghitung ketegangan struktural pasar, dan memberikan sinyal eksekusi deterministik berdasarkan mekanika resonansi — bukan spekulasi arah harga.

---

## 2. Masalah yang Diselesaikan

1. **Informasi Asimetris:** Trader ritel tidak bisa melihat liquidation cluster, order flow imbalance, dan niat algoritma bandar.
2. **Overload Data:** Memantau 200 aset secara manual mustahil tanpa otomasi.
3. **Emosi Trading:** Keputusan emosional menghasilkan kerugian; dibutuhkan sistem deterministik.
4. **Kehilangan Konteks:** Data sesi sebelumnya hilang; dibutuhkan Memory Buffer Sesi (MBS) persisten.

---

## 3. Fitur Utama (Prioritas)

### 3.1 Phase 1 — Fondasi (MVP)

#### F1: Data Ingestion Engine
- Koneksi WebSocket ke OKX API (Perpetual/Futures)
- Data: Order Book (depth), Trades, Funding Rate, Open Interest, Liquidation
- Normalisasi dan buffering data real-time
- Heartbeat monitoring per koneksi

#### F2: Zerotime Calculation Engine
- **Topological Drift (D_res):** `|P_market - P_pure| / P_pure * 100`
- **ZF-Score (0-1):** Indeks stabilitas/kerapuhan aset
- **Psi Total (Ψ_total):** `|P_market - P_vwap| + ω1(ΔOI/Vol_24h) + ω2(FR_curr/FR_avg) + ω3(α)`
- **Decay Prediction (Decay_t):** Proyeksi peluruhan harga 10 hari
- Bobot adaptif (ω) yang menyesuaikan volatilitas real-time

#### F3: Asset Swarm Manager (200 Aset)
- Scanning loop berdasarkan profil volatilitas
- **Heartbeat Mode:** Pemantauan ringan untuk aset stabil (ZF-Score < 0.6)
- **Deep Analysis Mode:** Komputasi penuh untuk aset kritis (ZF-Score > 0.6)
- Klasterisasi aset berdasarkan korelasi dan sektor

#### F4: Dashboard Arsitek
- Tabel utama: 200 aset dengan kolom ZF-Score, Drift, Ψ_total, Harga, Trend
- **Tabel Prediksi:** Top 20 aset prediksi naik/anjlok 10 hari (dinamis berdasarkan dominasi pasar)
- Status indikator: Normal / Waspada / Code Red
- Visualisasi: Order Book Depth, Liquidation Heatmap, Funding Rate Chart
- Real-time update via WebSocket

#### F5: Memory Buffer Sesi (MBS) Otonom
- Auto-save status 200 aset secara real-time ke database
- Auto-journaling saat sesi ditutup
- Auto-load + merge data historis saat sesi baru dimulai
- Tabel komparasi ZF-Score: sesi sebelumnya vs saat ini

#### F13: Multi-User & Autentikasi
- **Login via Google OAuth 2.0** (Google Sign-In) — tidak ada registrasi manual
- **Role-based access:**
  - **Super Admin:** Akses penuh — kelola user, konfigurasi sistem, lihat semua data, aktifkan/nonaktifkan fitur, kelola API key global
  - **Arsitek (User):** Akses dashboard, input API key OKX pribadi, terima alert, lihat prediksi
- Super Admin dibuat saat setup awal (seeding), bisa menunjuk user lain sebagai Super Admin
- Super Admin bisa mengatur status user: aktif / suspended / banned
- Setiap user baru yang login via Google otomatis mendapat role Arsitek

#### F14: Input API Key per User
- Setiap Arsitek bisa menginput **API key OKX pribadi** melalui halaman Settings
- API key disimpan terenkripsi (AES-256) di database — tidak pernah ditampilkan kembali secara utuh (masked)
- Validasi API key: sistem melakukan test call ke OKX saat disimpan
- API key bersifat opsional di MVP — jika tidak diinput, user hanya bisa melihat data (read-only dashboard)
- Di Phase 3 (Execution Engine), API key digunakan untuk eksekusi trade atas nama user masing-masing

#### F15: Mode Demo (Paper Trading)
- Mode Demo adalah **simulasi trading** dengan saldo virtual untuk user yang belum memiliki saldo di OKX atau ingin berlatih tanpa risiko
- **Fitur Mode Demo:**
  - Setiap user mendapat **saldo virtual** (default: 10.000 USDT) yang bisa di-reset
  - Akses **penuh ke seluruh dashboard** (200 aset, real-time, semua visualisasi) — sama seperti user biasa
  - Bisa melakukan **open/close posisi virtual** menggunakan harga pasar real-time dari OKX
  - Sistem menghitung **PnL virtual** secara real-time berdasarkan pergerakan harga aktual
  - Histori transaksi demo tersimpan terpisah dari transaksi live
  - Tidak memerlukan API key OKX (tidak ada koneksi ke akun exchange)
- **Batasan Mode Demo:**
  - Tidak ada eksekusi order nyata ke OKX
  - Tidak ada slippage simulation (eksekusi di harga mark price saat itu)
  - Leverage maksimal 10x (di live bisa lebih tinggi)
- **Tujuan:** Latihan trading tanpa risiko, validasi strategi, dan onboarding user baru sebelum menggunakan dana real
- **Transisi:** User bisa beralih antara Mode Demo dan Mode Live kapan saja (jika sudah punya API key)
- Mode Demo tersedia untuk semua user yang sudah login (tidak perlu API key)

### 3.2 Phase 2 — Inteligensi

#### F6: Anomaly Detection & Cross-Validation
- Divergensi multi-sumber: harga vs volume vs on-chain vs sentimen
- Audit silang (Cross-Checking): validasi Drift, audit likuiditas
- Filtering Engine: saring 20 aset kandidat disintegrasi (ZF-Score > 0.85)
- Peringatan "Code Red" otomatis (3 sesi berturut-turut memenuhi kriteria)

#### F16: On-Chain Data Integration
- Koneksi ke provider on-chain data (Glassnode / Santiment / API alternatif)
- Data: whale wallet movement, supply distribution, exchange inflow/outflow
- Digunakan sebagai input divergensi multi-sumber (F6) — jika harga naik tapi on-chain menunjukkan distribusi besar, naikkan sensitivitas Drift
- Frekuensi: polling setiap 5-15 menit (on-chain data tidak real-time)

#### F17: Sentiment Feed Integration
- Koneksi ke social listener API (LunarCrush / Santiment Social / API alternatif)
- Data: sentiment score, social volume, social dominance per aset
- Digunakan sebagai input anomaly detection (F6) — divergensi antara sentimen dan harga = sinyal waspada
- Frekuensi: polling setiap 15-30 menit

#### F7: Order Book Analysis
- Depth Mapping: rasio Bid/Ask per level harga
- Spoofing Detection: filter Order Cancellation Rate
- Liquidity Clustering: identifikasi magnetic points
- Dynamic Order Flow Imbalance (OFI)
- Slippage Calculator

#### F8: Protokol Pertahanan Sistemik
- De-leveraging otomatis saat liquidation cluster mendekat
- Circuit Breaker: freeze eksekusi saat spoofing terdeteksi global
- Cross-Asset Correlation: deteksi efek domino (50+ aset liquidity void)

### 3.3 Phase 3 — Eksekusi & Proteksi

#### F9: Execution Engine (Archi-Trade)
- Resonance Re-entry: titik masuk deterministik
- Entry Tolerance: `E = Entry Range ± (k * σ)` (k = 0.618)
- Dynamic Stop-Loss: keluar jika deviasi > 3-sigma dari model resonansi
- Alokasi modal berbasis ZF-Score
- Protokol Exit bertahap (panen energi resonansi)

#### F10: Notifikasi & Alert System
- Telegram Bot: sinyal Code Red, Black Swan, Circuit Breaker
- Peringatan dini: aset memenuhi kriteria disintegrasi
- Notifikasi status: Waspada / Pertahanan Sistemik / Eksekusi Short

#### F11: Self-Learning & Feedback Loop
- Error Log per transaksi
- Re-kalibrasi koefisien ω setiap 24 jam
- Re-training model jika false signal konsisten
- Penurunan bobot resonansi aset yang sering memberi sinyal palsu

### 3.4 Phase 4 — Mitigasi & Lanjutan

#### F12: Protokol Mitigasi Anomali
- Force Exit otomatis jika ZF-Score > 0.99 atau flash crash
- Cross-Exchange Hedging: pindah eksposur ke bursa lain saat liquidity void
- Mode Dingin: kunci trading interface saat over-trading terdeteksi
- Resonance Mismatch: isolasi aset, stop eksekusi, re-training dari nol
- Protokol Eskalasi Black Swan: leverage 1x, alihkan ke stablecoin

---

## 4. Arsitektur Teknis

### 4.1 Tech Stack

| Layer | Teknologi | Alasan |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Ekosistem kripto terbaik (ccxt, numpy, scipy) |
| **Frontend** | Next.js 15 (React) | Dashboard real-time, SSR, WebSocket client |
| **Database** | TimescaleDB (PostgreSQL ext) | Time-series native, SQL biasa, hemat RAM |
| **Cache/Queue** | Redis | MBS, pub/sub WebSocket, Celery task queue |
| **Task Worker** | Celery | Scanning loop 200 aset paralel, re-training 24h |
| **Exchange** | ccxt / ccxt.pro | Unified API OKX (REST + WebSocket) |
| **ML** | scikit-learn, numpy, scipy | Model parametrik, anomaly detection |
| **Containerization** | Docker + Docker Compose | Isolasi, reproducibility |
| **Reverse Proxy** | OpenLiteSpeed (CyberPanel) | Sudah terinstall, shared dengan app lain |
| **SSL** | Cloudflare | Sudah digunakan user |
| **CI/CD** | GitHub Actions | Build, test, deploy otomatis via SSH |
| **Notifikasi** | Telegram Bot API | Alert real-time ke Arsitek |

### 4.2 Diagram Arsitektur

```
Internet
    │
    ▼
Cloudflare (SSL/CDN)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ VPS (4C/16GB/100GB) — CyberPanel + OpenLiteSpeed    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ Docker Compose Stack: zf-core-v19           │    │
│  │                                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │    │
│  │  │ Next.js  │  │ FastAPI  │  │  Celery   │  │    │
│  │  │ :3000    │◄─┤ :8000    │◄─┤  Workers  │  │    │
│  │  │Dashboard │  │ REST+WS  │  │ (scanning │  │    │
│  │  └──────────┘  └────┬─────┘  │  200 aset)│  │    │
│  │                     │        └─────┬─────┘  │    │
│  │              ┌──────┴──────┐ ┌─────┴─────┐  │    │
│  │              │TimescaleDB  │ │   Redis    │  │    │
│  │              │(PostgreSQL) │ │Cache+Queue │  │    │
│  │              │ :5432       │ │ :6379      │  │    │
│  │              └─────────────┘ └───────────┘  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ Aplikasi lain (future projects)             │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         │                          │
    OKX WebSocket              Telegram Bot
    (Live Feed)                (Alerts)
```

### 4.3 Estimasi Resource

| Komponen | RAM | Catatan |
|---|---|---|
| TimescaleDB | ~2-3 GB | Shared dengan app lain jika perlu |
| Redis | ~512 MB | |
| FastAPI + Celery | ~4-6 GB | 200 aset concurrent |
| Next.js (prod) | ~256 MB | |
| Docker overhead | ~512 MB | |
| **Cadangan untuk app lain** | **~4-6 GB** | VPS shared |
| **Total** | **~16 GB** | Fit tapi ketat |

> **Catatan:** Jika VPS shared menjadi bottleneck, prioritaskan: kurangi jumlah aset heartbeat, atau upgrade RAM.

---

## 5. Data Flow

```
OKX WebSocket API
    │
    ▼
[Data Ingestion Engine] ──► Redis (buffer real-time)
    │                            │
    ▼                            ▼
[Celery Workers]           [FastAPI WebSocket]
    │                            │
    ├─ Hitung ZF-Score           ├─ Push ke Dashboard
    ├─ Hitung Ψ_total           └─ Push Alert
    ├─ Hitung D_res
    ├─ Anomaly Detection
    │
    ▼
TimescaleDB
    │
    ├─ MBS (Memory Buffer Sesi)
    ├─ ZF-Score historis
    ├─ Error Log
    └─ Prediksi Decay_t
```

---

## 6. Non-Functional Requirements

| Aspek | Target |
|---|---|
| **Latency** | < 500ms dari data masuk sampai dashboard update |
| **Uptime** | 99.5% (downtime max ~3.6 jam/bulan) |
| **Data Retention** | Tick data: 30 hari. Aggregat: unlimited |
| **Concurrent Assets** | 200 aset real-time |
| **Security** | SSL via Cloudflare, API key auth, env-based secrets |
| **Backup** | Daily DB backup ke object storage |

---

## 7. Deployment & CI/CD

### Git Strategy
- **Branch:** `main` (production), `develop` (staging), `feature/*`
- **Versioning:** Semantic Versioning (`v19.x.x`)
- **Tagging:** Setiap release di-tag

### CI/CD Pipeline (GitHub Actions)
```
Push/PR → Lint → Test → Build Docker → SSH Deploy → Health Check
```

### Deployment Flow
```
Developer push → GitHub Actions →
  1. Run tests (pytest + jest)
  2. Build Docker images
  3. SSH ke VPS
  4. docker compose pull && docker compose up -d
  5. Health check: curl /api/health
  6. Notif Telegram: deploy sukses/gagal
```

---

## 8. Milestones

| Phase | Scope | Estimasi |
|---|---|---|
| **Phase 1** | Data Ingestion + Calculation Engine + Dashboard MVP + MBS + Multi-User (Google OAuth) + API Key Management + Mode Demo (Paper Trading) + Super Admin | 6-8 minggu |
| **Phase 2** | Anomaly Detection + On-Chain Data + Sentiment Feed + Order Book Analysis + Pertahanan | 4-6 minggu |
| **Phase 3** | Execution Engine + Alert System + Self-Learning | 3-4 minggu |
| **Phase 4** | Mitigasi Anomali + Polish + Monitoring | 2-3 minggu |

---

## 9. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| OKX API rate limit | Implementasi rate limiter + backoff exponensial |
| VPS RAM tidak cukup (shared) | Heartbeat mode untuk aset stabil, monitor resource |
| Data loss saat deploy | Rolling deploy, DB backup sebelum deploy |
| Flash crash / Black Swan | Circuit Breaker + Force Exit otomatis |
| Model prediksi meleset | Feedback loop + re-kalibrasi ω setiap 24 jam |

---

## 10. Output Utama Dashboard

### Jika Pasar Dominan Turun:
**"Pasar Dominan Turun — 20 Koin Prediksi Anjlok dalam 10 Hari"**

| # | Aset | Harga | ZF-Score | Ψ_total | Drift | Prediksi 10H |
|---|---|---|---|---|---|---|

### Jika Pasar Dominan Naik:
**"Pasar Dominan Naik — 20 Koin Prediksi Naik dalam 10 Hari"**

| # | Aset | Harga | ZF-Score | Ψ_total | Drift | Prediksi 10H |
|---|---|---|---|---|---|---|

Diurutkan berdasarkan potensi tertinggi.
