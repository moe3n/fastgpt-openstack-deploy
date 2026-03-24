# FastGPT OpenStack Deployment

CI/CD pipeline for deploying FastGPT v4.14.9 to an OpenStack Nova instance using GitHub Actions with a self-hosted runner.

## Architecture

```
Developer pushes to main
        │
        ▼
GitHub Actions (self-hosted runner on DevStack host)
        │
        ├── 1. Validate docker-compose config
        ├── 2. SCP deployment files → OpenStack instance (172.24.4.84)
        ├── 3. SSH → docker compose up -d
        └── 4. Health check (HTTP 200 on port 3000)
```

## Pipeline Stages

| Stage | Description |
|---|---|
| **Checkout** | Pull latest deployment config from GitHub |
| **Validate** | Run `docker-compose config` to catch syntax errors |
| **Deploy files** | SCP updated compose/config files to OpenStack instance |
| **Deploy stack** | SSH into instance, run `docker compose up -d` |
| **Health check** | Poll `http://172.24.4.84:3000` until HTTP 200 |
| **API verify** | Confirm `/api/common/system/getInitData` responds |

## Stack

- **FastGPT** v4.14.9 — AI knowledge base platform
- **MongoDB** 4.4.18 — document store + vector change streams
- **PostgreSQL** + pgvector — vector similarity search
- **Redis** 7.2 — caching
- **Mock OpenAI** — local LLM/embedding service (no external API calls)

## Trigger

Pipeline runs automatically on every push to `main` that modifies files in `deployment/`.
