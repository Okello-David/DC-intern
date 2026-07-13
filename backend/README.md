# Backend — AI-Powered Student Career and Internship Assistant

This is the backend API for the project, built with **Django** and **Django REST Framework (DRF)**.

It uses **SQLite** for local development. It will move to
**PostgreSQL / Amazon RDS** when the project is deployed to AWS in a later week.

## What this backend does

- Django + DRF project (`config` project, `career` app) providing a REST
  API for the student career/internship assistant.
- A health-check endpoint (`GET /api/health/`) so the frontend or any
  teammate can confirm the API is reachable.
- CRUD endpoints for student profiles, skills, career/resume inputs, and
  (eventually AI-generated) recommendations, all backed by SQLite.
- No authentication, AI integration, or cloud deployment yet — those are
  planned for Week 4+.

## Project structure

```
backend/
├── venv/                 # Python virtual environment (not committed)
├── config/                # Django project (settings, root urls)
├── career/                 # Django app: models, serializers, views, urls, admin
├── manage.py
├── requirements.txt
└── db.sqlite3             # created after running migrations (not committed)
```

## Setup

### 1. Create and activate the virtual environment

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

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
python manage.py migrate
```

This creates the local `db.sqlite3` file and applies all model migrations.

### 4. Start the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### 5. Test the health-check endpoint

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

## Data Models

All models live in `career/models.py` and are linked to `StudentProfile` via
a foreign key (`on_delete=CASCADE`, so deleting a profile deletes its related
skills, career inputs, and recommendations).

- **StudentProfile** — `full_name`, `field_of_study`, `year_of_study`,
  `career_interest`, `internship_goal`, `created_at`, `updated_at`
- **Skill** — `student_profile`, `name`, `category`, `confidence_level`,
  `evidence`, `created_at`
- **CareerInput** — `student_profile`, `input_type`, `content`, `created_at`
- **Recommendation** — `student_profile`, `recommendation_type`, `content`,
  `created_at`

Choice fields (`field_of_study`, `year_of_study`, `category`,
`confidence_level`, `input_type`, `recommendation_type`) use Django
`TextChoices` so valid values are enforced and readable in the admin.

All models are registered in Django admin (`career/admin.py`) with list
display, filters, and search — and have `__str__` methods so records are
readable there.

## API Endpoints

Built with DRF `ModelViewSet` + `DefaultRouter`, wired in `career/urls.py`
and included under `/api/` in `config/urls.py`.

| Endpoint | Methods |
|---|---|
| `/api/health/` | `GET` |
| `/api/profiles/` | `GET`, `POST` |
| `/api/profiles/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/api/skills/` | `GET`, `POST` |
| `/api/skills/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/api/career-inputs/` | `GET`, `POST` |
| `/api/career-inputs/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/api/recommendations/` | `GET`, `POST` |
| `/api/recommendations/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` |

### How to test the endpoints

With the dev server running (`python manage.py runserver`):

- **Browser (DRF browsable API)** — visit `http://127.0.0.1:8000/api/profiles/`
  and the other endpoints directly. DRF renders an HTML form so you can
  submit `POST`/`PUT`/`PATCH` requests without any extra tooling.
- **curl**, example create + list:
  ```bash
  curl -X POST http://127.0.0.1:8000/api/profiles/ \
    -H "Content-Type: application/json" \
    -d '{
      "full_name": "Jane Doe",
      "field_of_study": "Computer Science",
      "year_of_study": "Year 3",
      "career_interest": "Backend Engineering",
      "internship_goal": "Get a backend internship at a tech company"
    }'

  curl http://127.0.0.1:8000/api/profiles/
  ```
- **API client** (Postman/Insomnia/Thunder Client) — point it at
  `http://127.0.0.1:8000/api/` and use the table above.
- **Admin site** — create a superuser
  (`python manage.py createsuperuser`) and browse/edit records at
  `http://127.0.0.1:8000/admin/`.

## Week 3 Status

The backend is feature-complete for the Week 3 MVP: project foundation,
all four data models, serializers, full CRUD API endpoints, admin
registration, and CORS configured for the React frontend
(`http://localhost:5173`). It is connected to and used by the frontend for
creating profiles, skills, and career inputs. See
`../docs/WEEK3_MVP_BUILD.md` for the full week summary and test checklist.

## Current Limitations

- No authentication — any client can read/write any record. Fine for local
  MVP work, not for deployment.
- No AI-generated content — `Recommendation` records have no producer yet;
  the `Placeholder` type exists for manual/testing use until real AI
  integration lands in Week 4.
- No input validation beyond DRF/Django defaults (e.g. no server-side
  resume parsing yet).
- SQLite only; no production database, hosting, or AWS config yet.
