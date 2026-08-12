# Running the AI PR Review Agent — Step-by-Step Guide

## Overview of the Flow

```
GitHub PR opened
      ↓
GitHub sends webhook POST → your FastAPI server (/github/webhook)
      ↓
Webhook enqueues job → Redis (ARQ queue)
      ↓
Worker picks up job → runs 4 specialist agents in parallel
      ↓
Aggregator decides: APPROVE / REQUEST_CHANGES / ESCALATE_TO_HUMAN
      ↓
GitHubClient.post_review() → posts review comment on the PR
```

---

## Prerequisites (one-time setup)

You need these installed:
- Python 3.14 (already have it)
- Redis (for the job queue)
- ngrok (to expose your local server to GitHub)
- A reachable Postgres/TigerDB instance (for RAG memory + review/finding storage)
- Node.js (only if you want the Next.js dashboard in `frontend/`)

---

## Step 0 — Install Python dependencies

```powershell
cd "d:\Documents\AI PR Review Agent"
pip install -r requirements.txt
```

---

## Step 1 — Install Redis (if not already installed)

Download and run Redis on Windows using the MSI installer:
```
https://github.com/tporadowski/redis/releases
```
Or using Windows Subsystem for Linux (WSL):
```bash
sudo apt install redis-server
redis-server
```

Verify Redis is running:
```powershell
redis-cli ping
# Should return: PONG
```

---

## Step 2 — Install ngrok (if not already installed)

Download from: https://ngrok.com/download

Sign up for a free account, then authenticate:
```powershell
ngrok config add-authtoken <YOUR_NGROK_TOKEN>
```

---

## Step 3 — Verify your .env is correct

Open `.env` and confirm these are filled in:

| Variable | What it is |
|----------|-----------|
| `GITHUB_TOKEN` | Your GitHub Personal Access Token (needs `repo` scope) |
| `GITHUB_WEBHOOK_SECRET` | Random secret — you will paste this into GitHub webhook settings |
| `GEMINI_API_KEY` | Your Gemini API key (for LLM calls + embeddings) |
| `TIGER_DATABASE_URL` | Postgres/TigerDB connection string (RAG memory, reviews, findings) |
| `REDIS_URL` | `redis://localhost:6379` (default) |

Also add this line to `.env` (needed so the worker knows which repo to post reviews to):
```
GITHUB_REPO=owner/your-repo-name
```

Note: `backend/api/main.py` and `run_worker.py` both call `load_dotenv()` as
the very first thing they do, so `.env` is picked up automatically — you no
longer need to load it into the shell by hand. Just make sure you launch
these commands from the project root (`.env`'s location), and restart both
processes any time you edit `.env` (env vars are read once at startup).

---

## Step 4 — Start the FastAPI server

Open **Terminal 1** in the project folder:

```powershell
cd "d:\Documents\AI PR Review Agent"
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5 — Start the ARQ Worker

Open **Terminal 2** in the project folder:

```powershell
cd "d:\Documents\AI PR Review Agent"
python run_worker.py
```

You should see:
```
Connecting to Redis at redis://localhost:6379...
Connected to Redis successfully.
ARQ Worker Daemon started. Listening for jobs...
```

---

## Step 6 — Expose your server with ngrok

Open **Terminal 3**:

```powershell
ngrok http 8000
```

You will get a URL like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**Copy the `https://...ngrok-free.app` URL** — you need it for GitHub webhook config.

---

## Step 7 — Configure the GitHub Webhook

1. Go to your GitHub repository → **Settings** → **Webhooks** → **Add webhook**

2. Fill in:

| Field | Value |
|-------|-------|
| **Payload URL** | `https://abc123.ngrok-free.app/github/webhook` |
| **Content type** | `application/json` |
| **Secret** | Paste the value of `GITHUB_WEBHOOK_SECRET` from your `.env` |
| **Which events?** | Select "Let me select individual events" → tick only **Pull requests** |

3. Click **Add webhook**

GitHub sends a ping — your Terminal 1 should log a `200 OK`.

---

## Step 8 — Create a Pull Request on GitHub

1. On your GitHub repo, create a new branch and make any code change
2. Open a **Pull Request** from that branch to `main`

**Within 30–60 seconds**, the agent will:
- Receive the webhook event
- Run 4 specialist agents in parallel
- Post a review comment directly on the PR

---

## Step 9 — Watch the output

**Terminal 1 (FastAPI)** shows:
```
POST /github/webhook  200
```

**Terminal 2 (Worker)** shows:
```
[Worker] ---> Executing job abc123 (review_pr)
[Worker] <--- Completed job abc123 in 12.34s. Result: {'status': 'ok'}
```

Your PR on GitHub will have a **new review** posted by the bot with findings and a recommendation.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Webhook returns 401 | `GITHUB_WEBHOOK_SECRET` in `.env` doesn't match what you typed in GitHub settings. Also confirm Terminal 1 was started from the project root (`.env` must be findable) and restarted after any edit to `.env` |
| Worker not picking up jobs | Check Redis is running: `redis-cli ping` |
| Findings look identical/canned on every PR | `GEMINI_API_KEY` failed to load or is invalid — check for a `[Warning] Gemini chat completion failed` line in the worker log |
| ngrok URL changed | Free ngrok URLs reset on restart — update the webhook URL in GitHub settings |
| Gemini errors / 404 on a model | `gemini-2.5-pro` 404s on free-tier keys; the router already defaults every agent to `gemini-2.5-flash`. Check `GEMINI_API_KEY` is valid and has quota |
| Review never actually posts on GitHub | `PyGithub` isn't installed — `GitHubClient` silently falls back to a no-op stub. Run `pip install PyGithub` (now in `requirements.txt`) |
| DB/RAG errors (context retrieval, review storage) | `TIGER_DATABASE_URL` unreachable or schema not applied — run `python scripts/run_postgres_migrations.py` once against a fresh database |

---

## Optional — Step 10: Run the dashboard

`frontend/` is a Next.js dashboard (review list, findings, cost charts, HITL
queue) that talks to the FastAPI server at `http://localhost:8000` by default
(CORS is already open for local dev in `backend/api/main.py`).

Open **Terminal 4**:
```powershell
cd "d:\Documents\AI PR Review Agent\frontend"
npm install
npm run dev
```
Visit `http://localhost:3000`.

---

## Quick Reference — All 4 terminals

| Terminal | Command |
|----------|---------|
| 1 — API Server | `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload` |
| 2 — Worker | `python run_worker.py` |
| 3 — ngrok tunnel | `ngrok http 8000` |
| 4 — Dashboard (optional) | `npm run dev` (from `frontend/`) |
