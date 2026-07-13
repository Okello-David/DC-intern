# Backend — AI-Powered Student Career and Internship Assistant

This is the backend API for the project, built with **Django** and **Django REST Framework (DRF)**.

For Week 3, it uses **SQLite** for local development. It will move to
**PostgreSQL / Amazon RDS** when the project is deployed to AWS in a later week.

## What this backend does (Week 3 scope)

- Provides the Django + DRF project skeleton (`config` project, `career` app).
- Exposes a single health-check endpoint (`GET /api/health/`) so the frontend
  (built later) and any teammate can confirm the API is reachable.
- No authentication, AI integration, or deployment config yet — those are
  planned for later weeks.

## Project structure

```
backend/
├── venv/              # Python virtual environment (not committed)
├── config/             # Django project (settings, root urls)
├── career/              # Django app (health-check endpoint lives here)
├── manage.py
├── requirements.txt
└── db.sqlite3          # created after running migrations (not committed)
```

## 1. Create and activate the virtual environment

From inside the `backend/` folder:

```bash
python3 -m venv venv
```

Activate it:

- macOS / Linux:
  ```bash
  source venv/bin/activate
  ```
- Windows (PowerShell):
  ```powershell
  venv\Scripts\Activate.ps1
  ```

You'll know it's active when your terminal prompt is prefixed with `(venv)`.

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Run database migrations

```bash
python manage.py migrate
```

This creates the local `db.sqlite3` file.

## 4. Start the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

## 5. Test the health-check endpoint

With the server running, in another terminal:

```bash
curl http://127.0.0.1:8000/api/health/
```

Expected response:

```json
{
  "status": "ok",
  "message": "Backend is running",
  "project": "AI-Powered Student Career and Internship Assistant"
}
```

You can also open that URL directly in a browser.
