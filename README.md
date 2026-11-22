# JobMatch AI 🚀

**JobMatch AI** is an intelligent job application management system that automates the process of finding, analyzing, and tracking job opportunities. It uses AI to compare job descriptions with your resume and personal context to provide a compatibility score and tailored advice.

> [!IMPORTANT]
> **Project Status: Under Construction (WIP)** 🏗️
> This project is currently in active development. Features are being added and UI/UX improvements are ongoing.

---

## 🌟 Key Features

- **Smart Scraping**: Automatically extracts job details from URLs using Jina AI and Playwright fallback.
- **AI Analysis**: Powered by Google Gemini (`gemini-2.5-flash-lite`) to analyze job fit based on your unique profile.
- **Suitability Scoring**: Get an instant 0-100% score for every job.
- **Gap Analysis**: identifies exactly what's missing in your profile for a specific role.
- **Actionable Feedback**: Direct messages and recommendations on whether to apply.
- **Interactive Dashboard**: A modern React-based interface to manage your active jobs and history.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Engine**: Google Gemini API (`gemini-2.5-flash-lite`)
- **Scraper**: Jina AI + Playwright fallback
- **Database**: PostgreSQL (via `asyncpg`); the schema is created/migrated automatically on startup

### Frontend
- **Framework**: React.js (via Vite)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP**: Axios

---

## ⚙️ How it works

Every job goes through a pipeline of background workers. Each stage is a status in the `jobs` table:

```text
URL ──► PENDING_RESOLVE ──► WAITING_FOR_SCRAPE ──► WAITING_FOR_AI ──► COMPLETED
        (Resolver: e.g.     (Scraper: Jina,        (AI: Gemini compares
         HireMeTech links)   then Playwright)        job ↔ resume + context)

Manual text ─────────────────────────────────────► WAITING_FOR_AI
Failures: FAILED_RESOLVE / FAILED_SCRAPE / NO_DATA / FAILED_ANALYSIS / DUPLICATE
```

A maintenance worker runs hourly and marks applications with no response for 30+ days as "ghosted".

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 20+ & npm
- PostgreSQL 12+ with an empty database (e.g. `CREATE DATABASE jobmatch;`)
- API key for Google Gemini (Jina AI key recommended)

### 1. Configuration
Copy `.env.example` to `.env` in the project root and fill in the values.

Put your resume and personal context in:
- `data/resume.txt`
- `data/Personal Context.txt`

(or edit them later from the **Profile** tab in the dashboard).

### 2. Backend
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium      # browser for the scraping fallback

cd src
python server.py                 # http://localhost:8000  (API docs: /docs)
```
On Windows you can also run `run_server.bat` from the project root.

### 3. Frontend
```bash
cd dashboard
npm install
npm run dev                      # http://localhost:5173
```

---

## 📁 Project Structure

```text
JobMatch/
├── dashboard/              # React frontend (Vite)
│   └── src/
│       ├── components/     # UI tabs, cards, modals
│       ├── constants/      # Status definitions
│       ├── hooks/          # useJobActions
│       └── services/       # API client (taskService.js)
├── src/
│   ├── server.py           # FastAPI entry point
│   ├── engine.py           # AI analysis (Gemini)
│   ├── routes/             # API endpoints (jobs, profile)
│   ├── db/                 # PostgreSQL schema + repository
│   ├── workers/            # Background pipeline workers
│   ├── scraper_service/    # Scraper + URL resolvers
│   ├── services/           # Profile & file helpers
│   └── models/             # Pydantic request models
├── data/                   # Your resume & context (git-ignored)
└── .env                    # Secrets (git-ignored, see .env.example)
```

---

## 📝 License
This project is for personal use. All rights reserved.
