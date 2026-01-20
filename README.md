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
- **AI Engine**: Google Gemini API
- **Scraper**: Jina AI + Playwright
- **Database**: Local JSON-based storage (for speed and simplicity)

### Frontend
- **Framework**: React.js (via Vite)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js & npm
- API Keys for Google Gemini and Jina AI

### 1. Backend Setup
1. Navigate to the `src` directory:
   ```bash
   cd src
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `src` directory:
   ```env
   GEMINI_API_KEY=your_gemini_key
   JINA_API_KEY=your_jina_key
   ```
5. Run the server:
   ```bash
   python server.py
   ```

### 2. Frontend Setup
1. Navigate to the `dashboard` directory:
   ```bash
   cd dashboard
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 📁 Project Structure

```text
JobMatch/
├── dashboard/          # React Frontend (Vite)
├── src/
│   ├── routes/         # API Endpoints
│   ├── services/       # Business Logic (Scraping, Processing)
│   ├── models/         # Data Structures (Pydantic)
│   ├── db/             # JSON Database management
│   ├── engine.py       # AI Analysis Engine
│   ├── scraper.py      # Web Scraping Logic
│   └── server.py       # FastAPI Entry Point
├── data/               # User data (Resume, Context)
└── results.json        # Stored job analyses (Local DB)
```

---

## 📝 License
This project is for personal use. All rights reserved.
