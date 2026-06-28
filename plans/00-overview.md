# ZF-Core V19.0 Phase 1 MVP — Implementation Plan

## Dependency Graph Antar Stream

```
Stream 1 (Infra & Foundation) ─────┬──► Stream 2 (Core Engine)
                                   ├──► Stream 3 (Auth & User)
                                   ├──► Stream 4 (Frontend Foundation)
                                   └──► Stream 6 (CI/CD)

Stream 2 (Core Engine) ───────────┬──► Stream 5 (Frontend Components)
Stream 3 (Auth & User) ───────────┘
Stream 4 (Frontend Foundation) ────────► Stream 5 (Frontend Components)
```

**Urutan mulai:**
1. Stream 1 HARUS selesai duluan (foundation)
2. Stream 2, 3, 4, 6 bisa PARALEL setelah Stream 1
3. Stream 5 mulai setelah Stream 2 + 3 + 4 selesai

## Daftar Stream

| Stream | File Plan | Task Count | Depends On |
|--------|-----------|------------|------------|
| 1. Infrastructure & Foundation | `01-infrastructure.md` | 6 tasks | - |
| 2. Backend Core Engine | `02-core-engine.md` | 7 tasks | Stream 1 |
| 3. Backend Auth & User | `03-auth-user.md` | 7 tasks | Stream 1 |
| 4. Frontend Foundation | `04-frontend-foundation.md` | 5 tasks | Stream 1 |
| 5. Frontend Components | `05-frontend-components.md` | 7 tasks | Stream 2,3,4 |
| 6. CI/CD & DevOps | `06-cicd.md` | 3 tasks | Stream 1 |

## Konvensi Task ID

Format: `S{stream}-T{number}` — contoh: `S1-T01`

## Konvensi Kode

- Python: PEP 8, type hints, async/await for I/O
- TypeScript: strict mode
- Kode & komentar: English
- Variabel rumus: sesuai dokumen asli (Ψ_total, D_res, ZF-Score)
- Input validation di trust boundary (API endpoint)
- Secrets via environment variable ONLY
