# FocusFlow – AI-powered task command center

To-Do app with tasks (detail, due date, frequency, comments), LLM prioritization, AI Chat, and Week Planner. Backend: Python (FastAPI). Frontend: Next.js. Deploy backend on Railway, frontend on Vercel.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` with:

- `GEMINI_API_KEY=...` (required for AI: prioritize, chat, schedule)
- `DATABASE_URL=sqlite:///./focusflow.db` (default; use PostgreSQL URL for production)

Then:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if the API is elsewhere.

## Features

- **Phase 1 – Tasks:** CRUD, due date, frequency, comments, importance (P1/P2/P3), time horizon, tags. List by Urgent / Important / Someday, DEADLINE RISK badge, expandable row, search and filters.
- **Phase 2 – Prioritize:** AI Insights card; “Prioritize my tasks” runs LLM to set time_horizon and importance for all incomplete tasks.
- **Phase 3 – AI Chat:** Suggested prompts (“What should I do today?”, “I have 30 minutes”, “What’s at risk?”, etc.); free-form questions; replies based on your tasks.
- **Phase 4 – Week Planner:** Describe your current week (per day), choose desired activities, “Plan My Week with AI” to generate a 7-day schedule; save schedule.
- **Phase 5 – Deploy:** Backend env (DATABASE_URL, GEMINI_API_KEY). Frontend env (NEXT_PUBLIC_API_URL). Railway for API, Vercel for frontend.

## Deployment

- **Railway (backend):** Connect repo, set root to `backend`, add env vars `DATABASE_URL` (PostgreSQL), `GEMINI_API_KEY`. Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Vercel (frontend):** Connect repo, set root to `frontend`, add env var `NEXT_PUBLIC_API_URL` to your Railway API URL.
