# Stream 5: Frontend Components & Pages

> Depends on: Stream 2 & Stream 3 & Stream 4 selesai
> Modul API, Auth, dan WS backend harus sudah berfungsi.

---

## S5-T01: Asset Table (Main Dashboard)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/app/(dashboard)/page.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/AssetTable.tsx`

**Dependencies:** S4-T03, S4-T05

**Deskripsi:**

### components/AssetTable.tsx
- Tampilkan tabel berisi 200 aset.
- Kolom: #, Aset (symbol), Harga, Δ 24h, ZF-Score, Ψ_total, D_res, OI, FR, Volume 24h, Status, Mode.
- Library: `@tanstack/react-table`
- Optimasi render: virtual scrolling/windowing (gunakan react-window atau @tanstack/react-virtual jika data lag, atau render virtual 50 item).
- Color-coding ZF-Score:
  - `< 0.5`: Hijau
  - `0.5 - 0.79`: Putih/Abu
  - `0.8 - 0.84`: Kuning (Waspada)
  - `0.85 - 0.98`: Merah (Disintegrasi)
  - `0.99 - 1.00`: Merah Gelap Berkedip (Force Exit)
- Sortable: klik header kolom untuk mengurutkan (default: ZF-Score descending).
- Filter: input search untuk symbol, dropdown filter status (Normal/Waspada/Code Red), dropdown filter mode (Heartbeat/Deep Analysis).
- Click row: arahkan navigasi ke detail aset `/[symbol]`.
- WebSocket integration: dengerin `asset_update` event via `useWebSocket`, lalu perbarui state baris yang bersangkutan secara real-time.

### (dashboard)/page.tsx
- Render AssetTable.
- Render StatusIndicator global.

**Acceptance Criteria:**
- Menampilkan 200 aset dalam tabel dengan update real-time via WS tanpa crash/lag.
- Filter dan sorting bekerja dengan benar.
- Baris dengan ZF-Score tinggi memiliki highlight warna yang sesuai.
- Klik baris redirect ke detail symbol.

---

## S5-T02: Prediction Table (Top 20)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/components/PredictionTable.tsx`

**Dependencies:** S4-T03, S4-T04

**Deskripsi:**

- Buat komponen `PredictionTable` untuk menampilkan data Top 20 prediksi kenaikan/peluruhan.
- State: Ambil data dari WebSocket event `prediction_update` (atau initial REST fetch ke `/api/predictions/top20`).
- Render judul tabel secara dinamis berdasarkan data `market_direction` dari API payload:
  - `"down"`: **"Pasar Dominan Turun — 20 Koin Prediksi Anjlok dalam 10 Hari"** (Tema merah)
  - `"up"`: **"Pasar Dominan Naik — 20 Koin Prediksi Naik dalam 10 Hari"** (Tema hijau)
  - `"neutral"`: **"Pasar Netral — 20 Koin dengan Potensi Pergerakan Tertinggi dalam 10 Hari"** (Tema abu-abu)
- Kolom: #, Aset, Harga, ZF-Score, Ψ_total, D_res, Prediksi 10 Hari (%).
- Urutan: Berdasarkan persentase absolute predicted change descending.
- Integrasi real-time via WebSocket.

**Acceptance Criteria:**
- Judul berubah secara dinamis sesuai arah pasar dari payload API.
- Menampilkan maksimal 20 aset prediksi.
- Urutan ranking sesuai dengan potensi pergerakan terbesar (absolute %).

---

## S5-T03: Charts Component (Order Book Depth, Heatmap, FR)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/components/DepthChart.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/LiquidationHeatmap.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/FundingRateChart.tsx`

**Dependencies:** S4-T01, S4-T04

**Deskripsi:**

### DepthChart.tsx
- Props: `symbol: string`. Initial load REST `/api/assets/{symbol}/orderbook`.
- Library: `recharts` (mirrored AreaChart).
- Sisi kiri (Bids, Hijau), Sisi kanan (Asks, Merah).
- Highlight level harga yang bertindak sebagai "Liquidity Cluster" (volume > 3x standar deviasi).

### LiquidationHeatmap.tsx
- Props: `symbol: string`. Initial REST fetch `/api/assets/{symbol}/liquidation-map`.
- Visualisasi horizontal bar chart atau scatter plot overlay pada price range.
- Gunakan gradient warna (kuning ke merah) untuk menandakan densitas level likuidasi.

### FundingRateChart.tsx
- Props: `symbol: string`. Fetch `/api/assets/{symbol}/history` (ambil data 7 hari terakhir).
- Line chart menunjukkan fluktuasi Funding Rate.
- Tandai (dot marker merah) jika nilai FR > 2x rata-rata historis (FR_avg).

**Acceptance Criteria:**
- Ketiga chart ter-render dengan benar saat memuat halaman detail aset.
- Data ter-load via REST API.
- Highlight klaster likuiditas dan FR ekstrim ber-fungsi visual.

---

## S5-T04: Session Comparison Component

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/components/SessionComparison.tsx`

**Dependencies:** S4-T03, S4-T04

**Deskripsi:**

- Buat komponen `SessionComparison` untuk membandingkan transisi fase aset dari sesi sebelumnya ke sesi saat ini.
- Dengerin WebSocket update `session_comparison` (atau fallback REST `/api/sessions`).
- Kolom: Aset, ZF-Score (Sebelumnya), ZF-Score (Sekarang), Δ ZF-Score, Arah.
- Render baris hanya jika ada perubahan absolut ZF-Score > 0.05.
- Berikan ikon arah:
  - `↑` (Merah/Memburuk) jika ZF-Score naik > 0.05.
  - `↓` (Hijau/Membaik) jika ZF-Score turun > 0.05.
- Urutkan berdasarkan delta perubahan terbesar.

**Acceptance Criteria:**
- Komponen memfilter aset yang perubahannya ≤ 0.05 (hanya tampilkan yang signifikan).
- Ikon arah dan warna sesuai kondisi transisi (merah memburuk, hijau membaik).

---

## S5-T05: Halaman Detail Aset (Symbol Page)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/app/(dashboard)/[symbol]/page.tsx`

**Dependencies:** S5-T03, S4-T05

**Deskripsi:**

- Buat halaman dinamis detail koin `/[symbol]` (misal: `/BTC-USDT-SWAP`).
- Panggil REST `/api/assets/{symbol}` di client-side untuk metadata detail.
- Layout halaman terbagi menjadi:
  - **Kiri atas**: Ringkasan metrik real-time koin (Harga, ZF-Score, Ψ_total, D_res, OFI, Bid/Ask ratio).
  - **Kiri bawah**: DepthChart dan LiquidationHeatmap secara tab.
  - **Kanan atas**: Form Quick Execution untuk Mode Demo (jika di mode demo) / Mode Live (jika live).
  - **Kanan bawah**: FundingRateChart.
- WebSocket subscription: subscribe ke room/channel symbol bersangkutan untuk memperbarui data header di halaman secara real-time.

**Acceptance Criteria:**
- Halaman memuat metadata aset dengan benar dari URL parameter.
- Semua sub-komponen chart ter-render sesuai aset yang dipilih.
- Subscribe WS bekerja pada mount, unsubscribe pada unmount.

---

## S5-T06: Panel Demo (Paper Trading UI)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/app/(demo)/page.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/DemoPanel.tsx`

**Dependencies:** S3-T06, S4-T02

**Deskripsi:**

### components/DemoPanel.tsx
- UI terbagi menjadi 3 bagian:
  1. **Wallet Stats Card**: Menampilkan Saldo Virtual, Total PnL, Win Rate (%), Unrealized PnL (real-time), dan tombol "Reset Saldo".
  2. **Order Form**: Form untuk membuka posisi virtual baru.
     - Inputs: Aset (combobox/select dari 200 koin), Side (Long/Short toggle), Size USDT (input number), Leverage (slider 1x-10x).
     - Tombol "Open Position".
  3. **Positions & History Tabs**:
     - **Tab Posisi Aktif**: Tabel posisi open dengan kolom Symbol, Side, Size, Entry Price, Mark Price, Leverage, Margin, Unrealized PnL (real-time), Close Button.
     - **Tab Histori**: Tabel posisi closed dengan kolom Symbol, Side, Size, Entry, Exit, PnL, Fee, Close Reason, Timestamp.
- Integrasi REST API `/api/demo/*` untuk submit order, close order, reset balance, dan fetch data.
- Update Unrealized PnL real-time: ambil mark price ter-update dari state WebSocket global, hitung PnL di client-side.

### (demo)/page.tsx
- Render `DemoPanel` di layout kuning demo mode.

**Acceptance Criteria:**
- Menampilkan saldo virtual dan update unrealized PnL posisi aktif secara real-time.
- Slider leverage terbatas maksimal 10x.
- Submit order sukses membuat posisi virtual baru dan memotong margin + fee dari saldo.
- Close order manual berhasil dan mengembalikan saldo virtual.
- Tombol reset saldo memicu konfirmasi dialog dan mengembalikan saldo ke 10.000 USDT.

---

## S5-T07: Panel Admin & Settings UI

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/app/admin/page.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/AdminPanel.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/app/(dashboard)/settings/page.tsx`

**Dependencies:** S3-T04, S3-T05, S4-T02

**Deskripsi:**

### settings/page.tsx (API Keys)
- Menampilkan daftar API Key OKX milik user (masked).
- Form "Tambah API Key": input label, api_key, secret_key, passphrase.
- Saat user save, panggil `POST /api/user/api-keys`. Tampilkan loading state selama test call OKX berjalan di backend. Show success toast jika valid.
- Tampilkan warning jika API key terdeteksi memiliki permission 'withdraw'.
- Tombol "Delete API Key" dengan konfirmasi.

### admin/page.tsx & components/AdminPanel.tsx
- Hanya bisa diakses jika role = 'super_admin'.
- **Tab Kelola User**: Tabel daftar semua user. Aksi: Suspend (suspend/activate), Ban (ban/unban), Promote/Demote (super_admin ↔ architect), Delete.
- **Tab Config Editor**: Tampilkan key-value configs (JSON Editor/Form) untuk edit data di database `system_config`.
- **System Actions Panel**: Tombol "Reset Circuit Breaker" dan "Trigger Re-kalibrasi Manual".

**Acceptance Criteria:**
- Form settings mem-validasi API key ke bursa sebelum disimpan.
- Daftar API key ter-render masked.
- Dashboard admin memblokir user non-admin (redirect/403).
- Semua aksi admin (suspend, ban, role, config update) berhasil memanggil API dan ter-update di UI.
