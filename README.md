# JobMatch

Paste job posts the way you get them - whole WhatsApp / Telegram messages full of links - and
JobMatch finds the job links, scrapes each posting, scores it against your resume with Google
Gemini (free tier) and keeps everything in Postgres. A React dashboard shows the scores and
tracks your applications.

```
raw message text
   │  POST /api/jobs/raw   (link extraction: drops app-store / group / non-job links, utm, duplicates)
   ▼
PENDING_RESOLVE ──resolver──▶ WAITING_FOR_SCRAPE ──scraper──▶ WAITING_FOR_AI ──AI──▶ COMPLETED
   (HireMeTech → company site)   (ATS API / Jina / HTML / Playwright)   (Gemini, model chain)   score + analysis in the DB
```

The three workers run inside the API process and use the `jobs` table as a queue
(`FOR UPDATE SKIP LOCKED`). Failures end in `FAILED_RESOLVE` / `FAILED_SCRAPE` /
`FAILED_ANALYSIS` / `NO_DATA` (closed job, login wall...) / `DUPLICATE`, each with a message in
`error_log` that the dashboard shows.

## Running locally

### With Docker (everything, on an empty database)

```bash
cp .env.example .env          # fill in GEMINI_API_KEY, JINA_API_KEY (HIRE_ME_TECH_TOKEN optional)
docker compose up --build
```

Open http://localhost:8000 - the server serves the dashboard too. Postgres runs in the `db`
container (exposed on `127.0.0.1:5434`); the schema is created on start-up. Your resume and
personal context are read once from `data/resume.txt` and `data/Personal Context.txt` (or the
`RESUME_TEXT` / `PERSONAL_CONTEXT_TEXT` env vars) and then live in the database - edit them in
the Profile tab.

### Without Docker

Python 3.12 recommended (3.10 works), Node 22, a Postgres 12+.

```bash
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium                          # browser for the scraper fallback / HireMeTech
run_server.bat                                       # or: python -m uvicorn src.server:app --reload
cd dashboard && npm ci && npm run dev                # http://localhost:5173 (talks to :8000)
```

### Tests

```bash
docker compose up -d db
docker compose exec db createdb -U jobmatch jobmatch_test      # once
# .env: TEST_DATABASE_URL=postgresql://jobmatch:jobmatch@127.0.0.1:5434/jobmatch_test
pytest
```

DB tests are skipped without `TEST_DATABASE_URL` (its database name must contain `test`: the
tests drop the schema). Use `127.0.0.1`, not `localhost`, on Windows.

### Checking the scraper and the AI on real data

```bash
python scripts/test_scraper.py data/links.txt     # resolve + scrape, no AI; table per site
python scripts/test_analysis.py --runs 2          # AI on scraped jobs, twice each: validity + score spread
```

Reports go to `logs/`.

## Configuration

See `.env.example` for every variable. The important ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (Neon/Supabase). Or `PG_*` locally. |
| `GEMINI_API_KEY` | Google AI Studio key (free tier). |
| `JINA_API_KEY` | Jina Reader key (scraper). |
| `API_TOKEN` | Shared secret: every `/api/*` call needs `Authorization: Bearer <token>`. Unset = open API (local only). |
| `HIRE_ME_TECH_TOKEN` | `auth_token` from hiremetech.com localStorage (sign in, DevTools → Application → Local Storage). Expires after **7 days**. Without a valid one HireMeTech jobs are still scored from HireMeTech's public API (full description, no company name or apply link). With one, the API gives the company's apply link - no browser needed, so it works on Render free too. |
| `GEMINI_MODEL` / `GEMINI_MODELS` | One model, or a chain. Default chain: `gemini-3.5-flash-lite, gemini-2.5-flash-lite, gemini-3-flash-preview`. |
| `GEMINI_RPM` / `GEMINI_RPD` | Local rate limit (default 10/min, no daily cap). |
| `ENABLE_PLAYWRIGHT` | `false` = no browser (saves ~300 MB RAM). |
| `IDLE_POLL_MAX_SECONDS` | Safety-net queue polling when idle (default 3600). |
| `RESUME_TEXT`, `PERSONAL_CONTEXT_TEXT` (or `*_FILE`) | Seed the profile on first run. |
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ALLOWED_NUMBERS` | The WhatsApp bot (all five, or the bot is off). See [WhatsApp bot](#whatsapp-bot). `WHATSAPP_GRAPH_VERSION` is optional (default `v27.0`). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS` | The Telegram bot: the token from @BotFather turns it on; only the listed chat ids get answers (until then the bot answers only `/id`). See [Telegram bot](#telegram-bot). |
| `RENDER_EXTERNAL_URL` | Set by Render itself (the service's full onrender.com URL). The bots link to the dashboard with it, and the Telegram webhook is registered at it on every start. Not set locally. |

The personal context file is part of the prompt and its rules win: hard filters (student
roles, mandatory degree...), scoring tiers and how to judge the chance of an interview.

## API (for the dashboard and future bots)

| Endpoint | |
|---|---|
| `POST /api/jobs/raw` `{text}` | Extract job links from raw text and queue them. Returns `added_jobs: [{id, url}]`, `skipped_urls` (existing jobs, with `id`) and `ignored` (non-job links with a reason). |
| `POST /api/jobs/extract-links` `{text}` | Preview only, nothing saved. |
| `GET /api/jobs/{id}` | One job: `status`, `suitability_score`, `recommendation`, `showstoppers`, `model`... |
| `GET /api/results` | All jobs. |
| `GET /api/jobs/queue` | Counts per status + a version (cheap polling) + whether the AI is paused by the quota. |
| `POST /api/jobs/text` | A job pasted as text (skips scraping). |
| `POST /api/jobs/retry?url=` | Retry from the failed stage. |
| `GET/POST /api/profile/resume`, `/api/profile/context` | The profile (stored in the DB). |
| `GET /health` | DB, workers, AI quota state, HireMeTech token expiry. 503 when degraded. |
| `GET /ping` | Liveness without touching the DB (for health checks / keep-alive). |
| `GET /webhooks/whatsapp` | Meta's one-time webhook verification (echoes `hub.challenge`). 404 while the bot is not configured. |
| `POST /webhooks/whatsapp` | Incoming WhatsApp messages. No `API_TOKEN`: checked by the `X-Hub-Signature-256` signature (App Secret). |
| `POST /webhooks/telegram` | Incoming Telegram updates. No `API_TOKEN`: checked by the `X-Telegram-Bot-Api-Secret-Token` header (derived from the bot token). 404 while the bot is not configured. |

A bot only needs `POST /api/jobs/raw` with the message text and then `GET /api/jobs/{id}` until
the status is `COMPLETED` (or a failure status). The WhatsApp bot does this inside the server: it
queues the message's links and sends the score back when each job finishes.

## Limits of the free services (checked 2026-11-22)

**Gemini.** Google does not publish the per-model free-tier numbers in its docs - they are shown
in AI Studio (https://aistudio.google.com/rate-limit) and are per project, per model; daily
quotas reset at midnight Pacific. Measured from Gemini's own 429:
`GenerateRequestsPerDayPerProjectPerModel-FreeTier = 20` for `gemini-2.5-flash-lite`.
`gemini-3.5-flash-lite` handled 40+ requests the same day without a 429. Free-tier prompts may
be used by Google to improve its products. What JobMatch does about it:
- a model chain: when a model's daily quota is used up, the next model takes over, and the
  first one comes back after the reset; each analysis records its `model`, because different
  models score differently (the same job got 60-88 across four models);
- a 429 never fails a job: it goes back to the queue and the AI pauses (until midnight Pacific
  for a daily quota); the dashboard shows a banner with the resume time;
- the job description is cleaned and cut to `MAX_DESCRIPTION_CHARS` (8000) - about half the
  tokens on real postings;
- `GEMINI_RPM` (10) spaces the requests.

**Jina Reader** (jina.ai/reader): a new key gets 10M free tokens. The same page lists 500 RPM for
a free key in its table and 100 RPM in its FAQ. JobMatch sends a few requests per job.

**Render (free web service).** 0.1 CPU / 512 MB, an ephemeral disk, 750 free instance hours per
workspace per month, and it **spins down after 15 minutes without inbound HTTP traffic**
(about a minute to wake up). While it sleeps the workers don't run - queued jobs wait until the
next request wakes it. Render's docs also say it may suspend a free service that generates an
unusually high volume of outbound traffic (JobMatch makes a handful of requests per job).

**Neon (free).** 1 GB storage per project, 100 CU-hours per project per month (400 h at the
smallest 0.25 CU), the compute scales to zero after 5 min without queries (suspended time is
free), 5 GB egress, and no deletion for inactivity. JobMatch is built to let it sleep: workers
are woken by new jobs instead of polling, idle polling is hourly, and `/ping` doesn't query.

**Telegram Bot API** (checked 2026-11-26, core.telegram.org/bots). Free: bots message their users
at no cost (paid broadcasts start above ~30 messages/second). Webhook only over HTTPS on ports 443,
80, 88 or 8443; a webhook and `getUpdates` can't be used together. A request that doesn't get a
2XX is retried "a reasonable number of attempts", and undelivered updates are kept up to 24 hours,
so a message sent while Render sleeps still arrives; `update_id` dedupes repeats. Sending: avoid
more than one message per second in a single chat; `text` is up to 4096 characters (the
`sendMessage` reference, read from a summary of the page).

**WhatsApp Cloud API** (checked 2026-11-26; pricing: https://developers.facebook.com/docs/whatsapp/pricing). Messages from the
user to the bot are free. Replies inside the 24-hour customer service window (opened by the user's
message) are *service* messages: 1,000 free per business phone number per month, then charged
(since 2026-10-01; the rate card is a separate file - a payment method must be on file or
service messages stop after the free tier). Free-form text is allowed only inside that window,
so the bot answers only people who wrote to it, and the score usually arrives within minutes.
Text body: max 4096 characters. Throughput: 1 message per 6 seconds to the same user (bursts
allowed). A webhook that is not answered with 200 is retried for up to 7 days and may arrive
more than once - the bot deduplicates by message id. Some webhooks are not sent while the Meta
app is in Dev mode. The temporary access token from the dashboard expires within hours; use a
System User token.

**Supabase (free)** would also work (500 MB database), but free projects are **paused after one
week of inactivity**. **Render's free Postgres** is deleted 30 days after creation.

## Deploying (Render + Neon)

1. Create a Neon project and copy its connection string (the direct one, or the `-pooler` one -
   both work).
2. Render: New → Blueprint → this repository. `render.yaml` creates one Docker web service.
   Fill in `DATABASE_URL`, `GEMINI_API_KEY`, `JINA_API_KEY`, `RESUME_TEXT`,
   `PERSONAL_CONTEXT_TEXT` (and `HIRE_ME_TECH_TOKEN` if you have one). Render generates
   `API_TOKEN`; copy it from the service's Environment page - the dashboard asks for it once.
   A Docker service on the free instance type worked (deployed 2026-11-25).
3. Open `https://<service>.onrender.com`. `/health` should report `"status": "ok"`.

Instead of `RESUME_TEXT`, you can add Render *secret files* named `resume.txt` and
`personal_context.txt` (mounted at `/etc/secrets/`).

### Keeping it awake (optional)

On the free plan the service sleeps after 15 minutes without requests. To keep the workers
running, ping `https://<service>.onrender.com/ping` every 10-14 minutes from an external
scheduler:
- **cron-job.org** - free (donation-funded), down to once a minute;
- **UptimeRobot** - free plan: 50 monitors, 5-minute interval, commercial use allowed.

Cost: $0. Trade-offs: one always-on service uses ~744 of the 750 free Render hours per month,
so there is nothing left for other free services in the same workspace; and Neon is unaffected
because `/ping` doesn't touch the database. Without the ping, things still work - jobs just
wait until the next visit or message wakes the service (~1 minute). The alternative is Render's
paid `starter` instance (0.5 CPU / 512 MB, no spin-down) - its price was not on the Render docs
pages checked; see the pricing page.

## WhatsApp bot

Forward a job message to the bot's WhatsApp number; it answers with how many jobs it queued, then
sends the score of each job when the analysis finishes (or why it failed). Only the numbers in
`WHATSAPP_ALLOWED_NUMBERS` get an answer. Step-by-step setup in Meta and Render (Hebrew):
[docs/whatsapp-setup.md](docs/whatsapp-setup.md). Without the five `WHATSAPP_*` variables the
webhook answers 404 and nothing else changes.

On the free Render plan a message that arrives while the service sleeps wakes it; Meta retries
until it gets a 200, so nothing is lost, but the first answer can take a minute or more.

## Telegram bot

The same as the WhatsApp bot, with a simpler setup: create a bot with @BotFather, put its token in
`TELEGRAM_BOT_TOKEN` on Render and deploy. On every start the server registers its webhook at
`RENDER_EXTERNAL_URL`/webhooks/telegram with a secret derived from the token. Send the bot `/id`,
put the number it answers in `TELEGRAM_ALLOWED_CHAT_IDS` and deploy again. Step by step (Hebrew):
[docs/telegram-setup.md](docs/telegram-setup.md).

## Project layout

```
src/
  server.py               FastAPI app: /api, /webhooks, /health, /ping, serves dashboard/dist
  workers/                resolver / scraper / AI / maintenance loops, rate limiter, wake-ups
  engine.py               Gemini call, prompt, response schema (Pydantic)
  scraper_service/        resolvers (HireMeTech), Jina + Playwright scraper, ATS APIs, validation
  services/               link extraction, intake, description condensing, profile, auth
  db/                     schema (idempotent migrations) and queries
  routes/                 API routes
dashboard/                React + Vite + Tailwind
scripts/                  test_scraper.py, test_analysis.py
tests/                    pytest (DB tests need TEST_DATABASE_URL)
```
