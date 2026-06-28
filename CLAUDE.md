# ZF-Core V19.0 — Protokol Zerotime

## Deskripsi Project
Platform analisis & eksekusi trading kripto derivatif berbasis AI. Memantau 200 aset kripto secara simultan, menghitung ketegangan struktural pasar (Ψ_total, ZF-Score, Topological Drift), dan memberikan sinyal eksekusi deterministik.

**Bursa utama:** OKX (Perpetual/Futures)
**Dokumen lengkap:** `docs/BUKU BESAR KRIPTO ZF ZEROTIME.txt`
**PRD:** `docs/PRD.md`
**SRS:** `docs/SRS.md`

## Tech Stack
- **Backend:** Python 3.12 + FastAPI
- **Frontend:** Next.js 15 (React)
- **Database:** TimescaleDB (PostgreSQL extension)
- **Cache/Queue:** Redis
- **Task Worker:** Celery
- **Exchange API:** ccxt / ccxt.pro (OKX WebSocket + REST)
- **ML:** scikit-learn, numpy, scipy
- **Container:** Docker + Docker Compose
- **CI/CD:** GitHub Actions → SSH deploy
- **Notifikasi:** Telegram Bot API

## Infrastruktur
- **VPS:** 4 core, 16GB RAM, 100GB storage
- **Panel:** CyberPanel + OpenLiteSpeed (reverse proxy)
- **SSL:** Cloudflare (bukan Let's Encrypt)
- **VPS shared:** Digunakan untuk project lain juga — jaga resource usage
- **Versioning:** Semantic Versioning (v19.x.x)
- **Git branching:** main (prod), develop (staging), feature/*

## Struktur Project (Target)
```
zf-core-v19/
├── CLAUDE.md              # File ini
├── docker-compose.yml
├── .github/workflows/     # CI/CD
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          # Zerotime engine (ZF-Score, Ψ_total, Drift)
│   │   ├── ingestion/     # OKX WebSocket data ingestion
│   │   ├── analysis/      # Anomaly detection, cross-validation
│   │   ├── execution/     # Archi-Trade engine
│   │   ├── models/        # DB models (SQLAlchemy)
│   │   ├── api/           # REST + WebSocket endpoints
│   │   │   ├── auth.py    # Google OAuth + JWT
│   │   │   ├── admin.py   # Super Admin endpoints
│   │   │   ├── api_keys.py # User API Key CRUD
│   │   │   ├── demo.py    # Mode Demo endpoints
│   │   │   └── ...
│   │   └── services/      # Celery tasks, Telegram bot, crypto (encryption)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
├── frontend/              # Next.js dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/    # Login page
│   │   │   ├── (demo)/    # Demo dashboard
│   │   │   ├── (dashboard)/ # Full dashboard (protected)
│   │   │   └── admin/     # Admin panel (super admin only)
│   │   ├── components/
│   │   └── lib/
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── BUKU BESAR KRIPTO ZF ZEROTIME.txt
│   ├── PRD.md
│   └── SRS.md
└── .env.example
```

## Rumus Inti (Jangan Diubah Tanpa Konfirmasi)

### ZF-Score (0-1)
Indeks kerapuhan aset. < 0.5 stabil, > 0.8 kritis, > 0.85 kandidat disintegrasi, > 0.99 force exit.

### Topological Drift
```
D_res = |P_market - P_pure| / P_pure * 100
```

### Ketegangan Struktural (Ψ_total)
```
Ψ_total = |P_market - P_vwap| + ω1(ΔOI/Vol_24h) + ω2(FR_curr/FR_avg) + ω3(α)
```
- ω = bobot adaptif, re-kalibrasi tiap 24 jam
- α = shock arbitrase (selisih harga antar bursa)

### Entry Tolerance
```
E = Entry Range ± (k * σ)
```
- k = 0.618 (Fibonacci)
- σ = volatilitas saat ini

### Stop-Loss
Keluar jika deviasi > 3-sigma dari model resonansi.

## Konvensi & Aturan

### Bahasa
- Komunikasi dengan user: **Bahasa Indonesia**
- Kode & komentar: **Bahasa Inggris**
- Nama variabel rumus: sesuai dokumen asli (Ψ_total, D_res, ZF-Score, dll)

### Kode
- Python: PEP 8, type hints, async/await untuk I/O
- TypeScript: strict mode
- Semua endpoint wajib punya error handling
- Input validation di trust boundary (API endpoint)
- Secrets via environment variable, JANGAN hardcode

### Data
- Tick data: retensi 30 hari
- Agregat (ZF-Score, Ψ_total harian): retensi unlimited
- Timezone: UTC untuk semua timestamp

### Deployment
- Docker Compose untuk orchestration
- Reverse proxy: OpenLiteSpeed (CyberPanel) — jangan install Nginx/Traefik
- SSL terminate di Cloudflare, bukan di server
- Port binding: internal only (tidak expose ke public langsung)

## Phase Implementasi
1. **Phase 1 (MVP):** Data Ingestion + Calculation Engine + Dashboard + MBS + Multi-User (Google OAuth) + API Key Management + Mode Demo + Super Admin
2. **Phase 2:** Anomaly Detection + Order Book Analysis + Pertahanan
3. **Phase 3:** Execution Engine + Alert System + Self-Learning
4. **Phase 4:** Mitigasi Anomali + Monitoring + Polish

## Autentikasi & User
- **Login:** Google OAuth 2.0 (tidak ada registrasi manual)
- **Roles:** super_admin, architect (default untuk user baru)
- **Super Admin pertama:** Di-seed via env var `SUPER_ADMIN_EMAIL`; fallback: user pertama yang login
- **API Key OKX per user:** Terenkripsi AES-256-GCM, disimpan di tabel `user_api_keys`, ditampilkan masked
- **Mode Demo:** Paper trading dengan saldo virtual (default 10.000 USDT), open/close posisi virtual di harga real-time, PnL dihitung real-time, tanpa API key OKX, akses penuh dashboard
- Super Admin bisa: kelola user, toggle fitur, konfigurasi sistem, lihat API key (masked)

## Catatan Penting
- VPS shared — selalu monitor RAM usage, target max ~10GB untuk ZF-Core
- Aset dengan ZF-Score < 0.6 jalankan Heartbeat Mode saja (hemat compute)
- Jangan pernah deploy tanpa backup DB terlebih dahulu
- Circuit Breaker wajib aktif sebelum Execution Engine diaktifkan
