# Cloud Deployment Notes

## Runtime

The prototype runs as a single Python service:

```powershell
python backend/app.py
```

Set these production environment variables:

- `PORT`: service port exposed by the platform.
- `GOLDTRACE_SECRET`: long random signing secret for bearer tokens.

## Recommended Cloud Architecture

```text
User Browser
  -> HTTPS Load Balancer / WAF
  -> GoldTrace API Container
  -> Managed PostgreSQL or Cloud SQL
  -> Object Storage for certificates and audit evidence
  -> SIEM / Log Sink for audit_log exports
```

For a production build, replace SQLite with managed PostgreSQL using the same relational tables. Keep `ledger_events.event_hash` and `previous_hash` immutable through database permissions or append-only triggers.

## Security Controls Implemented

- PBKDF2-SHA256 password hashing with per-user salts.
- HMAC-signed bearer tokens with expiration.
- Role-based authorization on sensitive mutations.
- Immutable-style ledger event hashes with previous-hash references.
- Request audit logging for authentication and data mutations.
- Browser security headers: CSP, frame denial, content sniffing protection, and referrer policy.
- CORS preflight handling for browser clients.

## Production Hardening Checklist

- Put the app behind HTTPS only.
- Store `GOLDTRACE_SECRET` in a cloud secret manager.
- Add rate limiting on `/api/auth/login`.
- Use managed PostgreSQL with automated backups and point-in-time recovery.
- Enable row-level security by organization for cooperative, refiner, and buyer tenants.
- Export `audit_log` to a tamper-evident SIEM.
- Store mining certificates, export documents, and assay files in encrypted object storage.
- Add MFA for regulators, auditors, refiners, and escrow approvers.
- Add external gold-price feed ingestion with source verification and stale-price alerts.

## Database Deployment

For SQLite demo:

```powershell
python backend/app.py
```

For PostgreSQL production:

1. Convert `backend/schema.sql` data types to PostgreSQL equivalents.
2. Run the schema migration with a tool such as Flyway, Liquibase, or Alembic.
3. Load controlled seed data for organizations, roles, and initial mining blocks.
4. Grant application users insert-only permission on `ledger_events`.

## Compliance Model

The portal supports:

- Traceability: batch-level custody events from block allocation to export.
- Fair trade: premium calculations above spot value for miner payment visibility.
- Security: escrow states and release conditions tied to ledger milestones.
- Compliance: ethical extraction audits and environmental block status.
- Market confidence: buyer-facing provenance, audit scores, and valuation records.
