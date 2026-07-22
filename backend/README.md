# Backend — AI-Powered Student Career and Internship Assistant

This is the backend API for the project, built with **Django** and **Django REST Framework (DRF)**.

It uses **SQLite** for local development and **PostgreSQL on Amazon RDS** when
deployed. Which one is used is decided entirely by the `DB_HOST` environment
variable — see [Database configuration](#database-configuration).

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
├── config/                # Django project
│   ├── settings.py
│   └── database.py        # SQLite-vs-PostgreSQL selection rule
├── career/                # Django app: models, serializers, views, urls, admin
│   ├── services/
│   │   └── ai_service.py  # the only module that talks to an AI provider
│   └── management/commands/
│       └── check_database.py
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
| `DB_HOST` | **Database switch.** Empty → SQLite. Set → PostgreSQL on RDS. | *(empty)* |
| `DB_NAME` | PostgreSQL database name. | *(unused locally)* |
| `DB_USER` | PostgreSQL username. | *(unused locally)* |
| `DB_PASSWORD` | PostgreSQL password. **Secret** — server environment only. | *(unused locally)* |
| `DB_PORT` | PostgreSQL port. | `5432` |
| `DB_SSLMODE` | libpq SSL mode for the RDS connection. | `require` |
| `CSRF_TRUSTED_ORIGINS` | Origins allowed to send unsafe requests, **with scheme**. Needed once the site is reached by hostname. | *(empty)* |
| `USE_HTTPS` | Turns on secure cookies, HTTPS redirect, and HSTS. Leave `False` until TLS exists. | `False` |

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

## Database configuration

One environment variable decides everything: **`DB_HOST`**.

| `DB_HOST` | Database used | Where |
|---|---|---|
| empty / unset | SQLite file `backend/db.sqlite3` | Local development |
| set | PostgreSQL on Amazon RDS | EC2 inside the VPC |

The rule lives in `config/database.py` (`build_database_config()`), which
`settings.py` calls with values read from the environment. It is a plain
function so the behaviour is unit-tested without needing a database.

### Local development — SQLite

Nothing to configure. Leave `DB_HOST` empty (or have no `.env` at all) and
Django uses the SQLite file, exactly as in Week 3:

```bash
python manage.py migrate
python manage.py runserver
```

### Production — PostgreSQL on Amazon RDS

Set these in the **server environment** on EC2. Never in a committed file, never
in source code:

```bash
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>      # secret — AWS environment only
DB_HOST=<rds-endpoint>.rds.amazonaws.com
DB_PORT=5432
DB_SSLMODE=require
```

When `DB_HOST` is set, Django uses `django.db.backends.postgresql` (driver:
`psycopg[binary]`) with:

- `CONN_MAX_AGE = 60` and `CONN_HEALTH_CHECKS = True` — connections are reused
  for up to a minute to avoid a TCP + TLS handshake per request, but not so long
  that idle workers hold RDS connection slots, and a reused connection is
  verified before use (important after an RDS failover).
- `OPTIONS = {'sslmode': 'require', 'connect_timeout': 10}` — traffic to RDS is
  encrypted in transit, and an unreachable database fails in ~10s instead of
  hanging. Note that `require` encrypts but does **not** verify the server
  certificate; `verify-full` (plus the RDS CA bundle on the instance) is the
  stronger setting to move to, and needs no code change.

If `DB_HOST` is set but `DB_NAME`, `DB_USER`, or `DB_PASSWORD` is missing,
Django **refuses to start** and names the missing variables. It never silently
falls back to SQLite on a server — that would look like a successful deployment
with an empty database.

### `python manage.py check_database`

A diagnostic command that reports which database Django is configured to use and
then runs `SELECT 1`.

```bash
python manage.py check_database              # host masked
python manage.py check_database --show-host  # host shown in full
```

Local output:

```
Database configuration
  Alias:    default
  Engine:   django.db.backends.sqlite3
  Vendor:   sqlite
  File:     /path/to/backend/db.sqlite3
  Mode:     local development (DB_HOST is not set, so SQLite is used)

Running SELECT 1 ...
OK — the database is reachable and responding.
```

On EC2 with `DB_HOST` set, it reports the engine, database name, user, port,
SSL mode, timeout, a masked host, and whether a password is set — then verifies
the connection. It exits `1` with a readable message on failure.

**It never prints the database password**, in any mode, and it scrubs the
password out of driver error text before displaying it — so it is safe to run in
a shared terminal or paste into a report.

Run it *before* `migrate` when deploying: it separates "Django is not reading the
environment variables" from "the security group is blocking me".

### Running migrations on EC2 (Day 4)

The RDS instance is private, so migrations are run **from the EC2 instance
inside the VPC**, not from a laptop:

```bash
# On the EC2 instance, with the DB_* environment variables set:
source venv/bin/activate
python manage.py check_database     # expect: postgresql, SSL mode require, OK
python manage.py migrate            # creates the schema on RDS
python manage.py createsuperuser    # optional, for the admin site
```

Running `check_database` or `migrate` against the RDS endpoint **from a local
laptop will fail, and that is correct** — the instance is not publicly
accessible, it has a private IP, and its security group only accepts PostgreSQL
from the EC2 application security group. See
`../docs/WEEK4_AI_AND_DEPLOYMENT.md` for the network design.

## Production deployment (EC2)

The dev server (`manage.py runserver`) is never used in production. On EC2,
**Gunicorn** runs the WSGI application and **Nginx** sits in front of it.

### Directory layout on the instance

```
/opt/dc-intern/                     git clone of this repository (owned by ec2-user)
├── backend/
│   ├── venv/                       virtualenv created by the deploy script
│   ├── staticfiles/                collectstatic output, served by Nginx
│   └── manage.py
└── deploy/                         service, site, and script templates

/etc/dc-intern/backend.env          all config and secrets (root:ec2-user, 0640)
/etc/systemd/system/dc-intern-backend.service
/etc/nginx/conf.d/dc-intern.conf
```

`/etc/dc-intern/backend.env` lives **outside** the repository so `git pull` and
`git status` can never see it. It is populated from AWS Systems Manager
Parameter Store; `deploy/backend.env.example` is the placeholder-only template.

### Gunicorn

```bash
# What the systemd unit runs (do not run this by hand except to debug):
/opt/dc-intern/backend/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    config.wsgi:application
```

Binding to `127.0.0.1` — not `0.0.0.0` — means the application is unreachable
from outside the instance except through Nginx.

### One-command deployment

```bash
# On the instance, as ec2-user, in a Session Manager shell:
cd /opt/dc-intern && git pull
SERVER_NAME=<ec2-public-dns> ./deploy/scripts/deploy_backend.sh
```

The script creates/updates the virtualenv, installs requirements, runs `check`,
`check --deploy`, `check_database`, `migrate`, and `collectstatic`, installs and
restarts the systemd unit, renders and validates the Nginx site, restarts Nginx,
and smoke-tests both Gunicorn and Nginx. It never creates, fetches, or prints
any secret.

### Migrations and static files by hand

Run these from `/opt/dc-intern/backend` with the environment file loaded:

```bash
set -a; source /etc/dc-intern/backend.env; set +a

venv/bin/python manage.py check_database     # verify RDS first
venv/bin/python manage.py migrate            # create/update the schema on RDS
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py createsuperuser
```

`collectstatic` copies the Django admin and DRF browsable-API assets into
`staticfiles/`, which Nginx serves — with `DEBUG=False`, Django will not serve
them itself, so skipping this step gives you an unstyled admin page.

### systemd commands

```bash
sudo systemctl status  dc-intern-backend      # is it running?
sudo systemctl restart dc-intern-backend      # after changing backend.env or code
sudo systemctl reload  dc-intern-backend      # graceful worker reload, no dropped requests
sudo systemctl enable  dc-intern-backend      # start on boot
sudo journalctl -u dc-intern-backend -f       # follow logs
sudo journalctl -u dc-intern-backend -n 50    # last 50 lines (start here on failure)
```

Changing `/etc/dc-intern/backend.env` requires a **restart**, not a reload —
systemd only reads the environment file when the service starts.

### Nginx commands

```bash
sudo nginx -t                                 # validate config before applying it
sudo systemctl reload nginx                   # apply config with no downtime
sudo systemctl restart nginx
sudo tail -f /var/log/nginx/dc-intern.error.log
```

Always run `nginx -t` before reloading; an invalid config will otherwise take
the site down.

### HTTPS

The site currently serves plain HTTP on port 80. Secure cookies,
`SECURE_SSL_REDIRECT`, and HSTS are gated behind `USE_HTTPS`, which stays
`False` until a certificate is in place — enabling them without TLS breaks
logins rather than hardening them. When TLS is configured, set `USE_HTTPS=True`
and restart; no code change is needed.

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

26 tests in `career/tests.py` cover the health endpoint, the Week 3 CRUD
endpoints, the skill-gap endpoint (structure, saved record, own-data content),
the 404 case, the empty-profile case, the AI service's fallback behaviour, the
SQLite-vs-PostgreSQL selection rule, and the `check_database` command. No
database server, RDS instance, or network access is required to run them.

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

## Week 4 Status

**Day 2** — Added environment-driven configuration (`python-decouple`,
`.env.example`), an AI service layer, and the first AI feature: the Skill Gap
Analysis endpoint, running in local mock mode with automated tests.

**Day 3** — Added PostgreSQL support (`psycopg[binary]`, `config/database.py`,
the `check_database` command) for the private Amazon RDS instance. SQLite
remains the default for local work and all AI functionality is unchanged.
Nothing is deployed to AWS yet, and no connection to RDS has been made.

**Day 4** — Added Gunicorn, production settings (`STATIC_ROOT`,
`CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, a `USE_HTTPS` gate), and the
`deploy/` directory: a systemd unit, an Nginx site template, a deploy script,
and a placeholder environment-file template. The repository is deployment-ready;
no AWS resource has been created and nothing has been deployed.

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
- PostgreSQL support is written and unit-tested, but **no migration has been run
  against RDS** and nothing has connected to it yet — that is Day 4, from inside
  the VPC.
- `CONN_MAX_AGE` is per Gunicorn worker, so total RDS connections scale with
  worker count. Check the instance's connection limit before scaling workers up
  (RDS Proxy or PgBouncer is the fix, not more workers).
- Deployment files exist and are syntax-checked, but **nothing has been deployed
  yet** — no EC2 instance has run the script.
- **No TLS.** The planned deployment serves plain HTTP on port 80;
  `manage.py check --deploy` reports W004/W008/W012/W016 for exactly this
  reason, and `USE_HTTPS=True` clears them once a certificate exists.
- No rollback step in the deploy script; recovery from a failed deployment is
  manual.
