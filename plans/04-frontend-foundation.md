# Stream 4: Frontend Foundation

> Depends on: Stream 1 selesai (S1-T02 minimal — Dockerfile frontend)
> Bisa dijalankan PARALEL dengan Stream 2 dan 3

---

## S4-T01: Next.js Boilerplate & Config

**Files:**
- `/home/ridwan/zf-core-v19/frontend/package.json`
- `/home/ridwan/zf-core-v19/frontend/next.config.ts`
- `/home/ridwan/zf-core-v19/frontend/tsconfig.json`
- `/home/ridwan/zf-core-v19/frontend/tailwind.config.ts`
- `/home/ridwan/zf-core-v19/frontend/postcss.config.js`
- `/home/ridwan/zf-core-v19/frontend/src/app/layout.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/app/page.tsx`
- `/home/ridwan/zf-core-v19/frontend/.eslintrc.json`

**Dependencies:** S1-T02

**Deskripsi:**

1. Init Next.js 15 project: `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias`
2. Install dependencies tambahan:
   ```
   npm install @tanstack/react-table recharts zustand
   npm install -D @types/node
   ```
   - `@tanstack/react-table`: virtual scroll tabel 200 aset
   - `recharts`: charts (Depth, Funding Rate)
   - `zustand`: state management (ringan, no boilerplate)
3. Setup shadcn/ui: `npx shadcn@latest init` — pilih default theme
   - Install komponen: `npx shadcn@latest add button card table badge dialog input label select tabs toast`
4. next.config.ts:
   ```ts
   const nextConfig = {
     output: 'standalone', // untuk Docker
     async rewrites() {
       return [
         { source: '/api/:path*', destination: 'http://backend:8000/api/:path*' },
         { source: '/ws/:path*', destination: 'http://backend:8000/ws/:path*' },
       ]
     }
   }
   ```
5. Root layout.tsx: HTML lang="id", meta charset, Providers wrapper (dibuat di S4-T02)
6. Root page.tsx: redirect ke `/login` jika belum auth, atau `/dashboard` jika sudah

**Acceptance Criteria:**
- `npm run dev` jalan tanpa error
- `npm run build` sukses
- Tailwind + shadcn/ui komponen render benar
- TypeScript strict mode aktif

---

## S4-T02: Auth Flow (JWT + Protected Routes)

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/lib/auth.ts`
- `/home/ridwan/zf-core-v19/frontend/src/lib/api.ts`
- `/home/ridwan/zf-core-v19/frontend/src/app/(auth)/login/page.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/app/providers.tsx`

**Dependencies:** S4-T01

**Deskripsi:**

### lib/auth.ts — JWT token management
```ts
// Storage: localStorage (access_token, refresh_token)
export function getAccessToken(): string | null
export function setTokens(access: string, refresh: string): void
export function clearTokens(): void
export function isAuthenticated(): boolean

// Auto-refresh: jika access token expired, panggil /api/auth/refresh
export async function refreshAccessToken(): Promise<string | null>
```

### lib/api.ts — REST API client
```ts
// Fetch wrapper yang auto-attach Authorization header
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T>

// Intercept 401 → try refresh → retry once → redirect to /login if fail
// Response type: { success: boolean, data: T | null, error: { code: string, message: string } | null, timestamp: string }
```

### (auth)/login/page.tsx
- Halaman login sederhana
- Logo/nama "ZF-Core V19.0"
- Tombol "Login with Google" → redirect ke `/api/auth/google`
- Setelah callback: extract tokens dari URL params atau response → simpan → redirect ke `/dashboard`
- Jika sudah login: redirect ke `/dashboard`

### providers.tsx
- AuthProvider: context yang hold user state, check token on mount
- Wrap children di root layout

**Acceptance Criteria:**
- Login button redirect ke Google OAuth
- Setelah callback, token tersimpan di localStorage
- `apiFetch` auto-attach Bearer token
- 401 response trigger refresh flow
- Protected routes redirect ke /login jika belum auth

---

## S4-T03: WebSocket Client Manager

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/lib/ws.ts`

**Dependencies:** S4-T02

**Deskripsi:**

### WebSocket client singleton

```ts
class WSManager {
  private ws: WebSocket | null = null
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  connect(token: string): void {
    // URL: ws://host/ws/dashboard?token={jwt}
    // Atau wss:// di production
    this.ws = new WebSocket(`${WS_URL}?token=${token}`)

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      // msg.type: 'asset_update' | 'alert' | 'prediction_update' | 'system_status' | 'session_comparison'
      const handlers = this.listeners.get(msg.type)
      handlers?.forEach(fn => fn(msg.data))
    }

    this.ws.onclose = () => {
      // Auto-reconnect after 3 seconds
      setTimeout(() => this.connect(token), 3000)
    }
  }

  subscribe(type: string, handler: (data: any) => void): () => void {
    // Add handler, return unsubscribe function
  }

  send(msg: object): void {
    this.ws?.send(JSON.stringify(msg))
  }

  disconnect(): void {
    this.ws?.close()
  }
}

export const wsManager = new WSManager()
```

### React hook: `useWebSocket(type: string)`
```ts
export function useWebSocket<T>(type: string): T | null {
  const [data, setData] = useState<T | null>(null)
  useEffect(() => {
    return wsManager.subscribe(type, setData)
  }, [type])
  return data
}
```

**Acceptance Criteria:**
- WebSocket connect saat user authenticated
- Messages dispatched ke subscriber berdasarkan `type`
- Auto-reconnect saat koneksi putus
- `useWebSocket` hook berfungsi di React components

---

## S4-T04: TypeScript Types & Interfaces

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/lib/types.ts`

**Dependencies:** S4-T01

**Deskripsi:**

Definisikan semua interfaces yang dipakai frontend:

```ts
// === API Response ===
interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string } | null
  timestamp: string
}

// === Asset ===
interface Asset {
  symbol: string
  price: number
  delta_24h: number          // percentage
  zf_score: number           // 0-1
  psi_total: number
  d_res: number              // percentage
  oi: number
  funding_rate: number
  volume_24h: number
  status: 'normal' | 'waspada' | 'code_red'
  mode: 'heartbeat' | 'deep_analysis'
}

interface AssetDetail extends Asset {
  cluster_id: number | null
  bid_depth_ratio: number
  ofi: number
  predicted_change_pct: number
}

// === Prediction ===
interface PredictionTop20 {
  title: string
  market_direction: 'up' | 'down' | 'neutral'
  assets: PredictionAsset[]
}

interface PredictionAsset {
  rank: number
  symbol: string
  price: number
  zf_score: number
  psi_total: number
  d_res: number
  predicted_change_pct: number
}

// === User ===
interface User {
  id: number
  email: string
  display_name: string | null
  avatar_url: string | null
  role: 'super_admin' | 'architect'
  status: 'active' | 'suspended' | 'banned'
}

// === API Key ===
interface ApiKey {
  id: number
  label: string | null
  api_key_last4: string
  permission_level: 'read_only' | 'trade' | 'withdraw' | null
  is_valid: boolean
  created_at: string
  last_tested_at: string | null
}

// === Demo ===
interface DemoWallet {
  balance: number
  initial_balance: number
  total_pnl: number
  total_trades: number
  win_trades: number
  win_rate: number
  unrealized_pnl: number
  last_reset_at: string
}

interface DemoPosition {
  id: number
  symbol: string
  side: 'long' | 'short'
  size_usdt: number
  leverage: number
  entry_price: number
  exit_price: number | null
  margin: number
  pnl: number | null
  fee: number | null
  unrealized_pnl?: number
  status: 'open' | 'closed'
  close_reason: 'manual' | 'take_profit' | 'stop_loss' | 'liquidation' | null
  opened_at: string
  closed_at: string | null
}

// === System ===
interface SystemStatus {
  circuit_breaker: boolean
  cold_mode: boolean
  assets_monitored: number
  assets_deep_analysis: number
  websocket_connected: boolean
  last_data_received: string
}

// === Session ===
interface SessionComparison {
  symbol: string
  zf_score_prev: number
  zf_score_curr: number
  delta: number
  transition: 'worsening' | 'improving' | 'stable'
}

// === WebSocket Messages ===
type WSMessageType = 'asset_update' | 'alert' | 'prediction_update' | 'system_status' | 'session_comparison'

interface WSMessage<T = any> {
  type: WSMessageType
  data: T
}

interface AlertData {
  priority: 'critical' | 'warning' | 'info'
  type: string
  symbol?: string
  message: string
}

// === Calibration ===
interface OmegaWeights {
  w1: number
  w2: number
  w3: number
}

// === Order Book ===
interface OrderBookLevel {
  price: number
  volume: number
}

interface OrderBookData {
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
  bid_depth_ratio: number
}
```

**Acceptance Criteria:**
- Semua interfaces cover response types dari backend API
- TypeScript compiler tidak error saat dipakai di komponen
- Naming konsisten dengan backend response fields

---

## S4-T05: Dashboard Layout & Navigation

**Files:**
- `/home/ridwan/zf-core-v19/frontend/src/app/(dashboard)/layout.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/app/(demo)/layout.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/app/admin/layout.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/Sidebar.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/Header.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/DemoLiveToggle.tsx`
- `/home/ridwan/zf-core-v19/frontend/src/components/StatusIndicator.tsx`

**Dependencies:** S4-T02, S4-T04

**Deskripsi:**

### Layout (shared by dashboard & demo)
- Sidebar kiri: navigasi (Dashboard, Settings, Admin jika super_admin)
- Header atas:
  - StatusIndicator: jumlah aset per status (Normal/Waspada/Code Red), badges warna
  - DemoLiveToggle: switch button Demo↔Live. Live disabled jika user tidak punya API key
  - Badge "MODE DEMO" kuning saat di demo mode
  - User avatar + dropdown (Profile, Logout)
  - Timestamp update terakhir

### (dashboard)/layout.tsx
- Protected route: redirect ke /login jika belum auth
- Wrap dengan WebSocket connection (connect on mount, disconnect on unmount)
- Background color: default (hijau subtle saat live mode)

### (demo)/layout.tsx
- Same structure as dashboard layout
- Background color: kuning subtle untuk visual distinction
- Badge "MODE DEMO" visible

### admin/layout.tsx
- Protected: require role super_admin, redirect ke /dashboard jika bukan admin
- Simpler layout: no DemoLiveToggle

### Sidebar.tsx
- Links: Dashboard (/dashboard), Settings (/dashboard/settings)
- Conditional: Admin (/admin) hanya tampil jika user.role === 'super_admin'
- Active state highlight

### StatusIndicator.tsx
- Props: `{normal: number, waspada: number, code_red: number, circuit_breaker: boolean}`
- Render: 3 badge pills (hijau/kuning/merah) + CB indicator
- Data dari `useWebSocket('system_status')`

### DemoLiveToggle.tsx
- Two-state toggle: "Demo" | "Live"
- Live disabled + tooltip "Tambahkan API key OKX dulu" jika user tidak punya key
- On switch: navigate to /demo atau /dashboard
- Visual: Demo=kuning, Live=hijau

**Acceptance Criteria:**
- Layout render dengan sidebar + header
- Protected routes redirect unauthorized users
- Toggle Demo/Live switch navigasi
- StatusIndicator update real-time via WebSocket
- Admin link hanya muncul untuk super_admin
