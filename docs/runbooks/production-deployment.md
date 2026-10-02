# Runbook — Production Deployment & Operations

## 1. Architecture Overview
In production, AgentOps operates as a distributed system:
- **Frontend Layer**: Next.js 15 App Router running on Node.js in non-root containers, behind an ingress / reverse proxy (e.g. Nginx, Cloudflare, Traefik).
- **Backend API**: Stateless FastAPI application workers managed via Uvicorn/Gunicorn.
- **Workers**: Dedicated asynchronous workers handling document chunking, embeddings, and periodic maintenance.
- **Database**: PostgreSQL 16+ with connection pooling and automated backups.
- **Storage**: Persistent volume mounted at `/app/storage/documents` for uploaded files.

---

## 2. Hardening & Security Guidelines

### 1. Environment Secrets
- Rotate `AUTH_SECRET_KEY` with a cryptographically secure 64-character token (`openssl rand -hex 32`).
- Never commit `.env` or production secrets into source control.
- Enforce HTTPS and TLS 1.3 at the reverse proxy boundary.

### 2. Container Security
- Backend and worker containers run under unprivileged user `agentops` (`uid: 1000`).
- Frontend containers run under unprivileged user `nextjs` (`uid: 1001`).
- Root filesystems are restricted; only `/app/storage` is writable.

### 3. Database Security & Migrations
- Run Alembic database migrations prior to routing traffic to new container versions:
  ```bash
  docker compose run --rm backend python scripts/run_migrations.py
  ```
- Schedule daily PostgreSQL backups using `pg_dump`.

---

## 3. Deployment Procedure

1. **Pull Latest Artifacts & Release Tag**:
   ```bash
   git pull origin main
   ```
2. **Build Production Images**:
   ```bash
   docker compose build --no-cache
   ```
3. **Execute Migrations**:
   ```bash
   docker compose run --rm backend python scripts/run_migrations.py
   ```
4. **Deploy / Restart Services with Zero-Downtime Rollout**:
   ```bash
   docker compose up -d --remove-orphans
   ```
5. **Verify Cluster Health**:
   ```bash
   docker compose run --rm backend python scripts/health_check.py
   curl -f http://localhost:8000/health
   ```
