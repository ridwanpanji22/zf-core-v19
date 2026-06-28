# Stream 3: Backend Auth & User

> Depends on: Stream 1 selesai (S1-T01 sampai S1-T06)
> Bisa dijalankan PARALEL dengan Stream 2

---

## S3-T01: API Dependencies & Auth Middleware

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/__init__.py`
- `/home/ridwan/zf-core-v19/backend/app/api/deps.py`

**Dependencies:** S1-T03, S1-T04

**Deskripsi:**

### deps.py — Shared dependencies untuk semua API endpoints

#### `get_db() -> AsyncGenerator[AsyncSession]`
- Yield database session dari `async_session_maker`
- Auto-close on exit

#### `get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User`
- Extract JWT dari Authorization header (Bearer token)
- Decode JWT menggunakan `python-jose`: verify signature dengan `JWT_SECRET`, algorithm HS256
- Extract `sub` (user_id) dari payload
- Query user dari DB
- Jika user tidak ditemukan, status suspended/banned: raise `HTTPException(401)`
- Return User object

#### `require_role(*roles: str)`
- Decorator/dependency yang check `current_user.role in roles`
- Jika tidak: raise `HTTPException(403, "Insufficient permissions")`
- Usage: `@router.get("/admin/users", dependencies=[Depends(require_role("super_admin"))])`

#### JWT Helper functions
- `create_access_token(user_id: int) -> str`: expire = settings.JWT_ACCESS_EXPIRE_MINUTES
- `create_refresh_token(user_id: int) -> str`: expire = settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 60
- `decode_token(token: str) -> dict`: decode & verify

**Acceptance Criteria:**
- `get_current_user` bisa extract user dari valid JWT
- Invalid/expired JWT raise 401
- `require_role("super_admin")` block non-admin users dengan 403

---

## S3-T02: Google OAuth 2.0 Flow

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/auth.py`

**Dependencies:** S3-T01

**Deskripsi:**

### Endpoints:

#### `GET /api/auth/google`
- Redirect user ke Google consent screen
- URL: `https://accounts.google.com/o/oauth2/v2/auth`
- Params: client_id, redirect_uri, response_type=code, scope="openid email profile", access_type=offline
- Library: `authlib` `OAuth` client

#### `GET /api/auth/google/callback?code={code}`
1. Tukar authorization code → access token via `https://oauth2.googleapis.com/token`
2. Fetch user info: `https://www.googleapis.com/oauth2/v3/userinfo` → email, name, picture, sub (google_id)
3. Cek apakah email sudah ada di tabel `users`:
   - Jika belum: INSERT user baru, role='architect', status='active'
   - Jika sudah:
     - Cek status: jika 'suspended' atau 'banned' → return error
     - Update `last_login`, merge google data (nama, avatar) jika berubah
4. Generate JWT access token (1 jam) + refresh token (7 hari)
5. Return JSON: `{"access_token": "...", "refresh_token": "...", "user": {...}}`
   - Atau redirect ke frontend dengan token di query param (tergantung frontend flow)

#### `POST /api/auth/refresh`
- Body: `{"refresh_token": "..."}`
- Decode refresh token, verify belum expired
- Generate new access token
- Return: `{"access_token": "..."}`

#### `GET /api/auth/me`
- Auth: Bearer JWT
- Return current user profile: id, email, display_name, avatar_url, role, status

#### `POST /api/auth/logout`
- Auth: Bearer JWT
- Blacklist refresh token (simpan di Redis dengan TTL = remaining expire time)
- Return: `{"success": true}`

**Acceptance Criteria:**
- Full OAuth flow: redirect → Google → callback → JWT returned
- User baru otomatis terdaftar sebagai 'architect'
- User suspended/banned ditolak login
- Refresh token bisa generate access token baru
- Logout invalidate refresh token

---

## S3-T03: Super Admin Seeding

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/main.py` (edit lifespan)

**Dependencies:** S3-T02, S1-T04

**Deskripsi:**

Pada lifespan `on_startup` di `main.py`, tambahkan logic seeding:

```python
async def seed_super_admin(db: AsyncSession):
    # 1. Cek apakah ada user dengan role = 'super_admin'
    result = await db.execute(select(User).where(User.role == "super_admin"))
    if result.scalar_one_or_none():
        return  # sudah ada super admin

    # 2. Jika SUPER_ADMIN_EMAIL di-set:
    if settings.SUPER_ADMIN_EMAIL:
        admin = User(
            email=settings.SUPER_ADMIN_EMAIL,
            role="super_admin",
            status="active",
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Super admin seeded: {settings.SUPER_ADMIN_EMAIL}")
    # 3. Fallback: user pertama yang login akan jadi super admin
    #    (handled di auth.py callback — jika no users exist, set role = super_admin)
```

Juga edit `auth.py` callback: jika `users` table kosong saat user pertama login, set `role = 'super_admin'`.

**Acceptance Criteria:**
- Startup dengan `SUPER_ADMIN_EMAIL=x@y.com`: user placeholder terbuat di DB
- Login pertama kali oleh email tersebut: merge data Google + role tetap super_admin
- Jika env var kosong: user pertama yang login jadi super_admin

---

## S3-T04: Admin Endpoints

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/api/admin.py`

**Dependencies:** S3-T01, S3-T02

**Deskripsi:**

Semua endpoint require `require_role("super_admin")`.

### Endpoints:

#### `GET /api/admin/users`
- Query semua users
- Return: list of `{id, email, display_name, avatar_url, role, status, created_at, last_login, api_key_count}`
- `api_key_count`: subquery count dari `user_api_keys`

#### `GET /api/admin/users/{id}`
- Detail user + list API keys (masked: hanya `label`, `api_key_last4`, `permission_level`, `is_valid`, `created_at`)

#### `PATCH /api/admin/users/{id}/status`
- Body: `{"status": "active"|"suspended"|"banned"}`
- Validate: tidak bisa suspend/ban diri sendiri
- Log ke `system_events` (event_type='admin_action')

#### `PATCH /api/admin/users/{id}/role`
- Body: `{"role": "architect"|"super_admin"}`
- Constraint: minimal 1 super_admin harus tetap ada (tidak bisa demote diri sendiri jika satu-satunya)
- Log ke `system_events`

#### `DELETE /api/admin/users/{id}`
- Hard delete user + cascade (api_keys, demo_wallet, demo_positions)
- Constraint: tidak bisa delete diri sendiri
- Log ke `system_events`

#### `GET /api/admin/config`
- Return semua rows dari `system_config`

#### `PUT /api/admin/config`
- Body: `{"key": "...", "value": ...}`
- Upsert ke `system_config`, set `updated_by` = current_user.id

#### `GET /api/admin/stats`
- Return: `{total_users, active_users, suspended_users, total_api_keys, demo_users_active}`

**Acceptance Criteria:**
- Semua 8 endpoints return data benar
- Non-admin mendapat 403
- Constraint (min 1 admin, tidak bisa delete diri) enforced
- Semua admin actions ter-log di `system_events`

---

## S3-T05: API Key Encryption & CRUD

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/crypto.py`
- `/home/ridwan/zf-core-v19/backend/app/api/api_keys.py`

**Dependencies:** S3-T01, S1-T04

**Deskripsi:**

### crypto.py — AES-256-GCM encryption

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt(plaintext: str, key: bytes) -> tuple[bytes, bytes]:
    """Return (ciphertext, nonce)."""
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce

def decrypt(ciphertext: bytes, nonce: bytes, key: bytes) -> str:
    """Return plaintext string."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
```

Key: `settings.API_KEY_ENCRYPTION_SECRET` — harus 32 bytes. Derive dari string env var via SHA-256 hash.

### api_keys.py — Endpoints

#### `POST /api/user/api-keys`
- Body: `{"api_key": "...", "secret_key": "...", "passphrase": "...", "label": "optional"}`
- Validasi: max 3 keys per user (count existing)
- Test call: instantiate ccxt.okx with credentials, call `fetch_balance()`. Jika gagal → return error.
- Determine permission_level dari OKX response (read_only/trade/withdraw)
- **Warning:** Jika permission includes 'withdraw', return warning message
- Encrypt api_key, secret_key, passphrase dengan AES-256-GCM (same nonce per row)
- Simpan: encrypted fields + nonce + last 4 chars api_key + permission_level
- Return: `{id, label, api_key_last4, permission_level, created_at}`

#### `GET /api/user/api-keys`
- Return list API keys milik current_user (masked — no decrypt)
- Fields: id, label, api_key_last4, permission_level, is_valid, created_at, last_tested_at

#### `DELETE /api/user/api-keys/{id}`
- Verify ownership (user_id == current_user.id)
- Hard delete

#### `POST /api/user/api-keys/{id}/test`
- Decrypt credentials
- Test call ke OKX
- Update `is_valid` dan `last_tested_at`
- Return: `{is_valid: bool, permission_level: str, error: str|null}`

**Acceptance Criteria:**
- Encrypt → decrypt roundtrip menghasilkan plaintext asli
- API key tersimpan encrypted di DB (kolom `api_key_encrypted` bukan plaintext)
- Max 3 keys per user enforced
- Test call ke OKX berfungsi
- User hanya bisa lihat/hapus key miliknya sendiri

---

## S3-T06: Mode Demo (Paper Trading)

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/demo.py`
- `/home/ridwan/zf-core-v19/backend/app/api/demo.py`

**Dependencies:** S3-T01, S1-T04, S2-T01 (untuk harga real-time dari Redis)

**Deskripsi:**

### services/demo.py — Business logic

#### `async create_wallet(db, user_id) -> DemoWallet`
- Insert demo_wallets dengan balance=initial_balance dari system_config (default 10000)

#### `async reset_wallet(db, user_id) -> DemoWallet`
- Close semua posisi open (pnl = berdasarkan harga saat ini)
- Reset balance ke initial_balance
- Reset stats (total_pnl=0, total_trades=0, win_trades=0)
- Update last_reset_at

#### `async open_position(db, user_id, symbol, side, size_usdt, leverage) -> DemoPosition`
- Validasi:
  - leverage: 1-10 (max dari system_config DEMO_MAX_LEVERAGE)
  - size_usdt > 0
  - margin = size_usdt / leverage
  - margin <= available balance
  - symbol harus ada di asset_registry
- Ambil mark price saat ini dari Redis key `tick:{symbol}`
- Fee = size_usdt * 0.0005 (0.05% taker fee)
- Deduct margin + fee dari wallet balance
- Insert DemoPosition: status='open', entry_price=mark_price
- Return position

#### `async close_position(db, user_id, position_id, reason='manual') -> DemoPosition`
- Verify ownership
- Verify status='open'
- Ambil mark price saat ini dari Redis
- Hitung PnL:
  - Long: `(mark_price - entry_price) / entry_price * size_usdt * leverage`
  - Short: `(entry_price - mark_price) / entry_price * size_usdt * leverage`
- Close fee = size_usdt * 0.0005
- Update position: exit_price, pnl, fee, status='closed', close_reason, closed_at
- Return margin + pnl - close_fee ke wallet balance
- Update wallet stats: total_pnl += pnl, total_trades++, win_trades++ jika pnl > 0

#### `async check_liquidations(db)`
- Query semua DemoPosition where status='open'
- Per posisi: ambil mark price dari Redis
- Hitung unrealized PnL
- Jika unrealized loss >= margin: auto-close dengan close_reason='liquidation'
- Ini dipanggil oleh Celery task `check_demo_liquidations` tiap 10 detik

### api/demo.py — Endpoints

#### `GET /api/demo/wallet`
- Auth: any logged-in user
- Jika wallet belum ada: auto-create
- Return: balance, initial_balance, total_pnl, total_trades, win_trades, win_rate (calculated), last_reset_at
- Juga return unrealized_pnl dari semua posisi open (hitung dari mark price Redis)

#### `POST /api/demo/wallet/reset`
- Panggil `reset_wallet()`
- Return wallet baru

#### `GET /api/demo/positions`
- Query demo_positions where user_id=current, status='open'
- Per posisi: tambahkan `unrealized_pnl` dari mark price saat ini
- Return list

#### `POST /api/demo/positions`
- Body: `{"symbol": "BTC-USDT-SWAP", "side": "long", "size_usdt": 1000, "leverage": 5}`
- Panggil `open_position()`
- Return position

#### `POST /api/demo/positions/{id}/close`
- Panggil `close_position()`
- Return closed position

#### `GET /api/demo/history`
- Query demo_positions where user_id=current, status='closed'
- Ordered by closed_at desc
- Pagination: `?page=1&limit=20`

**Acceptance Criteria:**
- Wallet auto-create saat pertama kali akses
- Open position mengurangi balance sebesar margin + fee
- Close position mengembalikan margin + PnL - fee
- Liquidation otomatis saat unrealized loss >= margin
- Reset wallet close semua posisi dan reset balance
- Statistik (win_rate, total_pnl) akurat

---

## S3-T07: Implement Remaining Celery Tasks

**Files:**
- `/home/ridwan/zf-core-v19/backend/app/services/tasks.py` (edit — tambahkan implementasi)

**Dependencies:** S3-T06

**Deskripsi:**

Implementasi 3 task tersisa:

### `check_demo_liquidations()` (tiap 10 detik)
- Panggil `demo.check_liquidations(db)`

### `refresh_asset_registry()` (daily 00:30 UTC)
- Panggil `asset_swarm.refresh_registry(exchange)`

### `backup_database()` (daily 02:00 UTC)
- Run `pg_dump` via subprocess ke file `/backups/zfcore_{date}.sql`
- Rotasi: hapus backup > 7 hari
- Log hasil ke `system_events`

**Acceptance Criteria:**
- Liquidation check berjalan tiap 10 detik
- Asset registry refresh berjalan
- Backup file terbuat dan rotasi bekerja
