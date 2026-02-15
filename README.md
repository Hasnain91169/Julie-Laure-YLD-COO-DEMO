# Friction Finder MVP

Portfolio-grade MVP to identify operational friction across People, Finance, Engineering, Client Services, and Commercial, then produce a ranked automation backlog and COO-ready report.

## Monorepo Structure

```text
.
+- api/                   FastAPI backend, adapters, scoring, reporting, seed data, tests
+- web/                   Next.js admin UI
+- examples/              Sample intake payloads
+- docker-compose.yml     Full stack compose (api + web + optional postgres)
+- .env.example
```

## Core Architecture

- Provider-agnostic intake via adapter contract (`api/app/adapters/base.py`):
  - `VapiIntakeAdapter` (`/intake/vapi`)
  - `InternalIntakeAdapter` (`/intake/internal`)
- Both map payloads into a canonical schema: `CanonicalIntake` (`api/app/schemas/intake.py`)
- Ingestion writes canonical data to shared tables and computes deterministic scores.

## Backend Features

- Intake endpoints:
  - `POST /intake/vapi`
  - `POST /intake/internal`
- CRUD:
  - `respondents`, `interviews`, `pain-points`
- Scoring:
  - `POST /scores/recompute`
- Analytics/reporting:
  - `GET /dashboard`
  - `GET /report` (HTML)
  - `GET /report.pdf` (PDF)
- Demo mode:
  - `POST /demo/seed?interview_count=24&reset=true`

### Scoring Model (transparent)

- `impact_hours_per_week = (frequency_per_week * minutes_per_occurrence / 60) * max(1, people_affected)`
- `effort_score` is rule-based from complexity/system count (1..5)
- `confidence_score` is deterministic from completeness + repeated mentions + clarity
- `priority_score = (impact_hours_per_week * confidence_score) / effort_score`
- `quick_win` when `effort_score <= 2` and impact >= `REPORT_QUICKWIN_IMPACT_THRESHOLD_HOURS`

### Privacy Guardrails

- `consent` gates storage of `transcript_raw`
- Regex redaction pipeline for email/phone/name hints
- `sensitive_flag` hides transcript context and excludes quotes from report appendix
- External AI calls disabled by default (`AI_PROVIDER=none`)

## Frontend Features

Pages:

- `/login`
- `/dashboard`
- `/pain-points`
- `/pain-points/[id]`
- `/report`
- `/demo`

Simple password gate uses `APP_PASSWORD` via `x-app-password` header.

## Local Run

### 1) API

```bash
cd api
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2) Web

```bash
cd web
npm install
copy .env.example .env.local
npm run dev
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

## Demo Mode

Seed via API:

```bash
curl -X POST "http://localhost:8000/demo/seed?interview_count=24&reset=true" \
  -H "x-app-password: changeme"
```

Or use the `/demo` page button.

CLI seed option:

```bash
cd api
python -m scripts.seed_demo --count 24 --reset
```

## Webhook Examples

### VAPI webhook intake

```bash
curl -X POST http://localhost:8000/intake/vapi \
  -H "Content-Type: application/json" \
  -d @examples/vapi_webhook.json
```

### Internal intake

```bash
curl -X POST http://localhost:8000/intake/internal \
  -H "Content-Type: application/json" \
  -d @examples/internal_intake.json
```

## Report Export

- HTML preview: `GET /report` (requires `x-app-password`)
- PDF: `GET /report.pdf` (requires `x-app-password`)

Example:

```bash
curl "http://localhost:8000/report.pdf" \
  -H "x-app-password: changeme" \
  --output friction-finder-report.pdf
```

## Docker Compose

```bash
docker compose up --build
```

Optional Postgres service:

```bash
docker compose --profile postgres up --build
```

If using Postgres, set:

```env
DATABASE_URL=postgresql+psycopg://friction:friction@db:5432/friction_finder
```

## Tests

```bash
cd api
pytest
```
