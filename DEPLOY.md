# Deploy FocusFlow: Railway (backend) then Vercel (frontend)

Deploy the **backend first** so you have the API URL for the frontend.

---

## 1. Deploy backend on Railway

1. **Sign in:** [railway.app](https://railway.app) → sign in with GitHub.

2. **New project:**  
   **New Project** → **Deploy from GitHub repo** → select your repo (`FocusFlow` or the repo that contains this project).

3. **Set root directory:**  
   In the service → **Settings** → **Root Directory** (or **Source**) → set to **`backend`** so Railway builds and runs from the `backend` folder.

4. **Add PostgreSQL (recommended):**  
   In the same project: **New** → **Database** → **PostgreSQL**. Railway will create a DB and expose `DATABASE_URL`.  
   In your **backend service** → **Variables**, add (or confirm):
   - `DATABASE_URL` — copy from the PostgreSQL service (e.g. **Connect** → **Postgres connection URL**).

5. **Backend environment variables:**  
   In the **backend service** → **Variables**:
   - `DATABASE_URL` — from step 4 (PostgreSQL URL).
   - `SECRET_KEY` — long random string for JWT (e.g. generate with `openssl rand -hex 32`). Required for auth.
   - `GEMINI_API_KEY` — your Gemini API key (required for prioritize, chat, schedule).
   - (Optional) `GEMINI_MODEL` — e.g. `gemini-2.5-flash` (default) or `gemini-2.5-pro`.
   - (Optional) `CORS_ORIGINS` — leave empty for now; add your Vercel URL after step 2 below (e.g. `https://your-app.vercel.app`).
   - (Optional) `FRONTEND_URL` — your Vercel app URL (for password-reset emails). SMTP vars optional (see `backend/.env.example`).

6. **Start command:**  
   The repo has **`backend/railway.toml`** with the start command; push and redeploy. If you still see "No start command was found", set it in the dashboard: **Settings** → **Deploy** → **Start Command** → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Alternatively, Railway can use the **Procfile** in `backend`:
   ```text
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   If it doesn’t, set **Custom Start Command** to:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

7. **Deploy:**  
   Push to `main` or trigger a deploy. Wait until the service is **Running**.

8. **Get the API URL:**  
   In the backend service → **Settings** → **Networking** (or **Domains**) → **Generate Domain**. Copy the URL (e.g. `https://your-app.up.railway.app`).  
   This is your **backend API URL** — you’ll use it in Vercel as `NEXT_PUBLIC_API_URL`.

9. **CORS (after Vercel deploy):**  
   In Railway → backend service → **Variables** → add or set:
   - `CORS_ORIGINS` = `https://your-vercel-app.vercel.app`  
   (use your actual Vercel URL; comma-separated if you have more than one).  
   Redeploy the backend after changing variables if needed.

---

## 2. Deploy frontend on Vercel

1. **Sign in:** [vercel.com](https://vercel.com) → sign in with GitHub.

2. **Import project:**  
   **Add New** → **Project** → import the same GitHub repo.

3. **Configure:**
   - **Root Directory:** set to **`frontend`** (click **Edit** next to the root).
   - **Framework Preset:** Next.js (auto-detected).
   - **Build Command:** `npm run build` (default).
   - **Output Directory:** default (e.g. `.next`).

4. **Environment variable:**  
   **Environment Variables**:
   - Name: `NEXT_PUBLIC_API_URL`  
   - Value: your Railway API URL from step 1.8 (e.g. `https://your-app.up.railway.app`)  
   - Apply to: Production (and Preview if you want).

5. **Deploy:**  
   Click **Deploy**. Wait for the build to finish.

6. **Frontend URL:**  
   Vercel gives you a URL like `https://your-project.vercel.app`. Copy it.

7. **Back to Railway (CORS):**  
   In Railway → backend service → **Variables** → set:
   - `CORS_ORIGINS` = `https://your-project.vercel.app`  
   Redeploy the backend so CORS allows your Vercel origin.

---

## Checklist

| Step | Where | What |
|------|--------|------|
| 1 | Railway | New project from GitHub, root = `backend` |
| 2 | Railway | Add PostgreSQL, link `DATABASE_URL` to backend |
| 3 | Railway | Set `GEMINI_API_KEY` (and optional `GEMINI_MODEL`) |
| 4 | Railway | Ensure start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| 5 | Railway | Generate domain, copy API URL |
| 6 | Vercel | Import repo, root = `frontend` |
| 7 | Vercel | Set `NEXT_PUBLIC_API_URL` = Railway API URL |
| 8 | Vercel | Deploy, copy frontend URL |
| 9 | Railway | Set `CORS_ORIGINS` = Vercel URL, redeploy if needed |

---

## Migration: existing database (auth)

**Migrations run automatically** when the backend starts. On every deploy (e.g. push to `main`), the app runs migrations after creating tables: it adds `users`, `password_reset_tokens`, `user_id` on tasks/schedule/day_logs, and any new columns like `complexity` and `reasoning`. You don’t need to run anything extra.

**Optional manual run:** from the `backend` directory you can still run:
```bash
cd backend
python -m scripts.migrate_auth
```
Use this if you want to apply migrations without starting the server (e.g. one-off against a production DB from your machine).

After migration (automatic or manual):
- If the `users` table is empty, a default user is created: **email** `migrated@focusflow.local`, **password** `changeme`. Log in once, then change the password or create a new user.
- Existing tasks, schedule blocks, schedule inputs, and day logs are linked to that default user.

---

## Local .env reference

- **Backend** (`backend/.env`): `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, optional `GEMINI_MODEL`, optional `CORS_ORIGINS`, optional `FRONTEND_URL` and SMTP for password reset.
- **Frontend** (`frontend/.env.local`): `NEXT_PUBLIC_API_URL=http://localhost:8000` for local dev.
