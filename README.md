# Karamoja GoldTrace Portal

A secure supply-chain ledger prototype for tracing Karamoja artisanal gold from cooperative ore allocation through refiner escrow and final export.

## What is included

- Responsive web frontend with dashboards, ledger, escrow, audit, map registry, and market analytics views.
- Python enterprise backend runtime using only the standard library.
- SQLite relational database schema with seeded cooperatives, mining blocks, batches, escrows, audits, prices, and ledger events.
- Security framework: PBKDF2 password hashing, HMAC-signed bearer tokens, role-based authorization, audit logging, CORS, and security headers.
- Reporting APIs for traceability, fair-trade pricing, escrow exposure, compliance, and gold spot analytics.
- Deployment notes for cloud/container operation.

## Quick start

```powershell
cd work/karamoja-goldtrace
python backend/app.py
```

Open http://127.0.0.1:8080

Demo users:

| Role | Email | Password |
| --- | --- | --- |
| Regulator | stella.nabachwa@goldtrace.ug | GoldTrace!2026 |
| Regulator | regulator@goldtrace.ug | GoldTrace!2026 |
| Cooperative | coop@goldtrace.ug | GoldTrace!2026 |
| Refiner | refiner@goldtrace.ug | GoldTrace!2026 |
| Buyer | buyer@goldtrace.ug | GoldTrace!2026 |

The database is created automatically at `backend/goldtrace.db` and seeded on first run.

## Architecture

```text
frontend/
  index.html      responsive app shell
  styles.css      accessible dashboard styling
  app.js          API client, charts, views, auth state
backend/
  app.py          HTTP API, auth, RBAC, reports, static serving
  schema.sql      relational schema and indexes
  seed.sql        seeded operational records
docs/
  DEPLOYMENT.md   cloud deployment and security notes
```

## Core API

- `POST /api/auth/login`
- `GET /api/me`
- `GET /api/dashboard`
- `GET /api/ledger`
- `GET /api/batches`
- `POST /api/batches`
- `GET /api/escrows`
- `POST /api/escrows/{id}/release`
- `GET /api/mining-blocks`
- `GET /api/audits`
- `POST /api/audits`
- `GET /api/prices`
