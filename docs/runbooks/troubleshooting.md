# Runbook — Troubleshooting & Diagnostics

## 1. Quick Diagnostics Commands

### Check Container Logs
```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend
docker compose logs -f postgres
```

### Inspect Service Health
```bash
docker compose ps
uv run python scripts/health_check.py
```

---

## 2. Common Issues & Solutions

### Issue: Backend Cannot Connect to PostgreSQL
- **Symptoms**: `ConnectionRefusedError` or `asyncpg.exceptions.CannotConnectNowError`.
- **Resolution**:
  1. Check PostgreSQL container health: `docker compose ps postgres`.
  2. Verify credentials in `.env` match `POSTGRES_USER` and `POSTGRES_PASSWORD`.
  3. Ensure port `15432` (or container internal `5432`) is not blocked by a local PostgreSQL daemon.

### Issue: Document Uploads Stuck in `PROCESSING` or `FAILED`
- **Symptoms**: Uploads fail or documents do not advance to `READY`.
- **Resolution**:
  1. Inspect worker daemon logs: `docker compose logs worker`.
  2. Ensure `/app/storage/documents` volume has write permissions for user `agentops`.
  3. Verify document is a supported format (`.pdf`, `.txt`, `.md`) under 10MB.

### Issue: Frontend Displays Unauthorized or Clears Session
- **Symptoms**: UI redirects to login or shows expired session error.
- **Resolution**:
  1. Token expiration defaults to 3600 seconds (1 hour). Re-authenticate.
  2. If backend secret was rotated, all existing JWT tokens become invalid.

### Issue: Database Migration Conflicts
- **Resolution**:
  1. Check current head revision: `uv run alembic current`.
  2. Re-run migration script: `uv run python scripts/run_migrations.py`.
