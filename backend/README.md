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
  recommendations, all backed by SQLite.
- An AI service layer plus a **Skill Gap Analysis** endpoint (Week 4) that
  generates a recommendation from a student's profile, skills, and career
  inputs. The AI provider is called **server-side only**.
- Configuration read from environment variables, so no secret is hard-coded.
- No authentication or cloud deployment yet — those are planned for Week 4+.

## Project structure

```
backend/
├── venv/                  # Python virtual environment (not committed)
├── config/                # Django project (settings, root urls)
├── career/                # Django app: models, serializers, views, urls, admin
│   └── services/
│       └── ai_service.py  # the only module that talks to an AI provider
├── manage.py
├── requirements.txt
├── .env.example           # documented placeholders (committed)
├── .env                   # real values (git-ignored, never committed)
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

### 3. Configure environment variables

Settings that change between machines (local laptop vs. AWS server) are read
from environment variables using
[`python-decouple`](https://pypi.org/project/python-decouple/), which reads
`backend/.env` first and falls back to real environment variables. **No secret
is hard-coded in `settings.py`.**

`.env.example` is committed and lists every variable the project expects, with
placeholder values only. `.env` holds real values and is git-ignored — never
commit it.

```bash
cp .env.example .env
```

The defaults work for local development as-is, so this step is optional today;
it becomes mandatory on deployment.

| Variable | Purpose | Default if unset |
|---|---|---|
| `DEBUG` | Django debug mode. Must be `False` in deployment. | `True` |
| `SECRET_KEY` | Django signing key. | dev-only placeholder (allowed only while `DEBUG=True`) |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django will serve. | `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to call the API. | `http://localhost:5173,http://127.0.0.1:5173` |
| `AI_PROVIDER` | AI implementation to use. `mock` = local fallback, no network call. | `mock` |
| `AI_API_KEY` | Provider API key. **Server-side only** — never sent to the frontend. | *(empty)* |
| `AI_MODEL` | Model identifier passed to the provider. | `mock-local` |

Two safety behaviours are built in:

- With `DEBUG=False` and no `SECRET_KEY`, Django refuses to start rather than
  falling back to a public default. Verify with:
  ```bash
  DEBUG=False python manage.py check   # expect ImproperlyConfigured
  ```
- With `DEBUG=False`, secure cookie and content-type-nosniff settings switch on
  automatically.

### 4. Run database migrations

```bash
python manage.py migrate
```

This creates the local `db.sqlite3` file and applies all model migrations.

### 5. Start the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### 6. Test the health-check endpoint

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
| `/api/profiles/<id>/generate-skill-gap/` | `POST` |

## Skill Gap Analysis Endpoint (Week 4)

```
POST /api/profiles/<id>/generate-skill-gap/
```

No request body is needed — the profile id in the URL is enough. The view
(`StudentProfileViewSet.generate_skill_gap`) loads the profile's `Skill` and
`CareerInput` records, calls
`career/services/ai_service.py::generate_skill_gap_analysis()`, saves the result
as a `Recommendation` with `recommendation_type="Skill Gap Analysis"`, and
returns it.

Response (`201 Created`):

```json
{
  "profile_id": 1,
  "recommendation_id": 3,
  "recommendation_type": "Skill Gap Analysis",
  "content": "SKILL GAP ANALYSIS\nStudent: ...",
  "created_at": "2026-07-22T10:31:57.802323Z",
  "ai_provider": "mock",
  "ai_model": "mock-local",
  "used_fallback": true,
  "notes": []
}
```

The analysis content has seven sections: career readiness summary, strengths,
missing technical skills, missing professional skills, suggested projects, a
4-week learning plan, and limitations.

### Error handling

| Situation | Response |
|---|---|
| Profile id does not exist | `404` with a JSON `detail` message |
| Profile has no skills and/or no career inputs | `201` — a limited analysis is still generated, and `notes` explains what was missing |
| Configured AI provider fails or is unavailable | `503` with a readable `error` message — never a traceback |
| Any other unexpected error | `500` with a generic `error` message; the full traceback is logged server-side only |

### Mock mode and the API key rule

`AI_PROVIDER=mock` (the default) makes **no external network call**. The service
layer builds the analysis locally from the student's own data, so the feature
works offline, costs nothing, and sends no student data to a third party.
`used_fallback: true` in the response says so honestly.

The same fallback is used if `AI_PROVIDER` names a real provider but `AI_API_KEY`
is empty — a misconfiguration degrades to a working demo instead of an error.

**The AI API key is read from the server environment and used only inside
`ai_service.py`. It is never returned by the API and never reaches the browser.**
A key in frontend code is public the moment the page loads: it can be read from
the network tab or the built JavaScript, and any resulting API charges land on
this project's account.

### How to test it locally

```bash
# 1. Create a profile and note its id
curl -X POST http://127.0.0.1:8000/api/profiles/ \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Jane Doe","field_of_study":"Software Engineering","year_of_study":"Year 3","career_interest":"Cloud Engineering","internship_goal":"AWS cloud internship"}'

# 2. Add a skill and a career input for that profile (replace 1 with the id)
curl -X POST http://127.0.0.1:8000/api/skills/ \
  -H "Content-Type: application/json" \
  -d '{"student_profile":1,"name":"Linux command line","category":"Cloud Computing","confidence_level":"Intermediate","evidence":"Daily Ubuntu use"}'

curl -X POST http://127.0.0.1:8000/api/career-inputs/ \
  -H "Content-Type: application/json" \
  -d '{"student_profile":1,"input_type":"Career Goal","content":"Become an AWS cloud engineer"}'

# 3. Generate the analysis
curl -X POST http://127.0.0.1:8000/api/profiles/1/generate-skill-gap/

# 4. Confirm it was saved
curl http://127.0.0.1:8000/api/recommendations/

# 5. Confirm a missing profile returns 404
curl -i -X POST http://127.0.0.1:8000/api/profiles/99999/generate-skill-gap/
```

### Automated tests

```bash
python manage.py test
```

12 tests in `career/tests.py` cover the health endpoint, the Week 3 CRUD
endpoints, the skill-gap endpoint (structure, saved record, own-data content),
the 404 case, the empty-profile case, and the AI service's fallback behaviour.

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

## Week 4 Day 2 Status

Added environment-driven configuration (`python-decouple`, `.env.example`), an
AI service layer, and the first AI feature: the Skill Gap Analysis endpoint,
running in local mock mode with automated tests. Nothing is deployed to AWS yet.
See `../docs/WEEK4_AI_AND_DEPLOYMENT.md`.

## Current Limitations

- No authentication — any client can read/write any record, and any client can
  generate an analysis for any profile. Fine for local MVP work, not for
  deployment.
- No real AI provider connected — `AI_PROVIDER=mock` returns a rule-based local
  analysis. `_call_provider()` in `ai_service.py` is a documented stub, so
  adding a provider is a single-function change.
- Only one recommendation type has a producer. `Career Path`,
  `Project Recommendation`, `Learning Plan`, and `Resume Feedback` remain
  unimplemented.
- No rate limiting on the skill-gap endpoint — required before a paid provider
  is connected.
- No input validation beyond DRF/Django defaults (e.g. no server-side
  resume parsing yet).
- SQLite only; no production database, hosting, or AWS config yet.
