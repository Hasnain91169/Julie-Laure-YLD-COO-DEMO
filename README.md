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

## Voice + n8n Demo

### Overview

The voice intake feature allows users to report friction points through voice conversation powered by VAPI, with automated report generation via n8n workflows.

**Flow:** User speaks → VAPI bot → API ingestion → n8n workflow → AI-generated report

### Setup

#### 1) Configure VAPI (Optional - for actual voice calls)

1. Create a VAPI account at [vapi.ai](https://vapi.ai)
2. Create a new assistant configured to:
   - Ask about friction points, team, frequency, impact
   - Include `session_id` and `respondent_id` in metadata
   - Send webhook to your API `/intake/vapi` endpoint
3. Add credentials to `.env.local`:
```env
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_assistant_id
VAPI_WEBHOOK_SECRET=generate_a_secret
```

#### 2) Set up n8n Workflow

1. Install n8n (cloud or self-hosted):
```bash
# Docker
docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n

# Or use n8n cloud at n8n.io
```

2. Import workflow:
   - Go to Workflows → Import from File
   - Select `examples/n8n_workflow.json`

3. Configure environment variables in n8n:
   - `API_BASE_URL`: Your API URL (e.g., `http://host.docker.internal:8000`)
   - `APP_PASSWORD`: Your app password
   - `N8N_WEBHOOK_SECRET`: Generate a secret
   - Add OpenAI API credentials for AI analysis

4. Activate the workflow and copy the webhook URL

5. Update API `.env`:
```env
N8N_WEBHOOK_SECRET=same_secret_as_n8n
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/friction-finder
```

#### 3) Test the Flow

**Option A: With VAPI (full integration)**
1. Visit `http://localhost:3000/voice`
2. Fill in your info and click "Start Voice Call"
3. Talk to the VAPI bot about friction points
4. After call ends, wait for n8n to generate report
5. View report when ready

**Option B: Without VAPI (test workflow only)**
1. Create a session:
```bash
curl -X POST http://localhost:8000/intake/session \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","team":"Engineering","role":"Developer"}'
```

2. Submit a VAPI webhook (simulate call):
```bash
curl -X POST http://localhost:8000/intake/vapi \
  -H "Content-Type: application/json" \
  -H "x-webhook-secret: your_vapi_secret" \
  -d @examples/vapi_webhook.json
```

3. n8n workflow will trigger automatically
4. Check report:
```bash
curl http://localhost:8000/report/latest \
  -H "x-app-password: changeme"
```

### Architecture: VAPI → API → n8n

```
┌──────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────┐
│ Voice UI │ ──> │ VAPI Bot    │ ──> │ API      │ ──> │ n8n     │
│ (React)  │     │ (Phone AI)  │     │ /intake  │     │ Workflow│
└──────────┘     └─────────────┘     └──────────┘     └─────────┘
                                            │                │
                                            ▼                ▼
                                      ┌──────────┐     ┌─────────┐
                                      │ Database │     │ OpenAI  │
                                      │ (Pain Pt)│     │ (Summary│
                                      └──────────┘     └─────────┘
                                            │                │
                                            ▼                ▼
                                      ┌───────────────────────┐
                                      │ /report/attach        │
                                      │ (Report registry)     │
                                      └───────────────────────┘
```

### n8n Workflow Details

See [docs/n8n_workflow.md](docs/n8n_workflow.md) for complete documentation.

**Workflow steps:**
1. Webhook receives trigger from API
2. Fetches interview and pain point data
3. AI analyzes and generates summary + recommendations
4. Attaches report to database
5. (Optional) Sends Slack/email notifications

### Troubleshooting

**n8n workflow not triggering:**
- Check `N8N_WEBHOOK_URL` is correct in API `.env`
- Verify `N8N_WEBHOOK_SECRET` matches in both API and n8n
- Check n8n workflow is activated
- Test webhook manually with curl

**VAPI not sending data:**
- Check VAPI assistant is configured with correct webhook URL
- Ensure `metadata` includes `session_id` from `/intake/session`
- Verify `VAPI_WEBHOOK_SECRET` in API `.env`

**Report not appearing:**
- Check n8n execution logs for errors
- Verify OpenAI API key is configured in n8n
- Check `/report/latest` endpoint manually
- Look for errors in API logs

## Tests

```bash
cd api
pytest
```
