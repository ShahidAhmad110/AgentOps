# Runbook — Local Deployment & Development

## 1. Prerequisites
- Python 3.13+
- Node.js 20+ and npm
- Docker and Docker Compose
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `winget install astral-sh.uv`)

---

## 2. Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Ensure `AUTH_SECRET_KEY` and `DATABASE_URL` are appropriately set.

---

## 3. Option A — Running via Docker Compose (Recommended)

To build and launch all services (PostgreSQL, FastAPI Backend, Background Worker, and Next.js Frontend) in isolated containers:

```bash
docker compose up -d --build
```

### Verify Service Status
```bash
docker compose ps
```

### Access Points
- **Frontend Dashboard**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Backend Healthcheck**: `http://localhost:8000/health`
- **PostgreSQL Database**: `localhost:15432`

---

## 4. Option B — Running Locally for Development

### 1. Start PostgreSQL
```bash
docker compose up -d postgres
```

### 2. Apply Database Migrations
```bash
uv run python scripts/run_migrations.py
```

### 3. (Optional) Seed Initial Admin & Organization Data
```bash
uv run python scripts/seed_data.py
```

### 4. Start the FastAPI Backend
```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Start the Background Worker
```bash
uv run python -m workers.runner
```

### 6. Start the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000`.
