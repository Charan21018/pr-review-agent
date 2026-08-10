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
| `OPENAI_API_KEY` | Your OpenAI API key (for LLM calls) |
| `REDIS_URL` | `redis://localhost:6379` (default) |

Also add this line to `.env` (needed so the worker knows which repo to post reviews to):
```
GITHUB_REPO=owner/your-repo-name
```

---

## Step 4 — Load the .env and start the FastAPI server

Open **Terminal 1** in the project folder:

```powershell
cd "d:\Documents\AI PR Review Agent"

# Load .env variables into current shell
Get-Content .env | Where-Object { $_ -notmatch "^#" -and $_ -ne "" } | ForEach-Object { $parts = $_ -split "=", 2; [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim()) }

# Start the FastAPI server
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

# Load .env
Get-Content .env | Where-Object { $_ -notmatch "^#" -and $_ -ne "" } | ForEach-Object { $parts = $_ -split "=", 2; [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim()) }

# Start the worker
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
| Webhook returns 401 | `GITHUB_WEBHOOK_SECRET` in `.env` doesn't match what you typed in GitHub settings |
| Worker not picking up jobs | Check Redis is running: `redis-cli ping` |
| "GitHub token not provided" | `GITHUB_TOKEN` not loaded in Terminal 2 — re-run the env load step |
| ngrok URL changed | Free ngrok URLs reset on restart — update the webhook URL in GitHub settings |
| OpenAI errors | Check `OPENAI_API_KEY` is valid and has credits |

---

## Quick Reference — All 3 terminals

| Terminal | Command |
|----------|---------|
| 1 — API Server | `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload` |
| 2 — Worker | `python run_worker.py` |
| 3 — ngrok tunnel | `ngrok http 8000` |
