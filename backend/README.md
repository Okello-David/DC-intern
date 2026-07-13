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
├── career/              # Django app (models, serializers, views, urls, admin)
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

## Week 3 Day 2: Backend Models and API Endpoints

### Models created

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

### API endpoints created

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

### Current limitations

- No authentication — any client can read/write any record. Fine for local
  MVP work, not for deployment.
- No AI-generated content — `Recommendation` records are created manually
  for now; the `Placeholder` type exists for this reason. Real AI
  integration is planned for Week 4.
- No input validation beyond DRF/Django defaults (e.g. no server-side
  resume parsing yet).
- SQLite only; no production database, hosting, or AWS config yet.

### Next step: frontend setup

Week 3 Day 3+ will scaffold the React (Vite) frontend and connect it to
these endpoints, starting with the health-check and `StudentProfile`
create/list flows.
