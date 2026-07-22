# Week 4 — AI Integration and Deployment Preparation

## Week 4 Objective

Turn the Week 3 MVP into an application that (a) produces real AI-assisted
recommendations and (b) is configured well enough to be deployed to AWS —
moving from a hard-coded development setup to environment-driven
configuration, and from SQLite to PostgreSQL on Amazon RDS.

Week 4 is split across days:

| Day | Focus | Status |
|---|---|---|
| Day 1 | AWS account safety: MFA, budget alert, credit check, AWS CLI profile | Done |
| Day 2 | First AI feature (Skill Gap Analysis) locally + production-ready Django settings | Done |
| Day 3 | VPC, subnets, security groups, private Amazon RDS PostgreSQL + Django PostgreSQL support | Done |
| Day 4 | Deploy Django to EC2: Gunicorn, Nginx, systemd, production settings | Done (repository prepared) |
| Day 5+ | Deploy the frontend, complete Week 4 documentation | Next |

---

## Day 2 — Work Completed

1. **Environment-driven configuration.** Added `python-decouple` and moved
   `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and the AI
   provider settings out of `settings.py` and into environment variables.
   `backend/.env.example` documents every variable with placeholder values only.
2. **AI service layer.** Created `backend/career/services/ai_service.py` — the
   single place in the project that is allowed to talk to an AI provider.
3. **Skill Gap Analysis feature.** Added
   `POST /api/profiles/<id>/generate-skill-gap/`, which gathers a profile's
   skills and career inputs, generates an analysis, saves it as a
   `Recommendation`, and returns it.
4. **Safe local fallback.** With `AI_PROVIDER=mock` (or with no `AI_API_KEY`
   configured), the backend produces a structured, rule-based analysis locally.
   The feature is fully demonstrable offline, at zero cost, and with no student
   data leaving the machine.
5. **Error handling.** Missing profile → `404`. AI provider failure → a clean
   JSON error, never a traceback. Missing skills or career inputs → the analysis
   is still generated, with explicit `notes` explaining what was limited.
6. **Tests.** 12 automated tests covering the health endpoint, the four Week 3
   CRUD endpoints, the skill-gap endpoint, the 404 case, the empty-profile case,
   and the AI service's fallback behaviour.
7. **Frontend integration.** New `AIRecommendationPanel.jsx` with a
   "Generate Skill Gap Analysis" button, loading state, error state, and the
   rendered recommendation. The frontend calls **only** the Django API.

No AWS deployment was performed on Day 2 — that is deliberate and scheduled for
Day 3+.

---

## Why Skill Gap Analysis Was Chosen as the First AI Feature

- **It is the core of the problem statement.** The project exists because
  students do not know which skills they are missing for their target role.
  Skill gap analysis answers exactly that question; everything else (project
  ideas, learning plans, career paths) is downstream of it.
- **The data it needs already exists.** `StudentProfile`, `Skill`, and
  `CareerInput` were all built in Week 3, so no new models or migrations were
  required — the feature slots onto the existing MVP.
- **The output is easy to judge.** A reviewer can look at a student's skills and
  a target role and immediately tell whether the analysis is sensible. That makes
  it a good first feature to validate the whole AI pipeline.
- **It fits the existing `Recommendation` model.** `Skill Gap Analysis` was
  already one of the `RecommendationType` choices defined in Week 3.
- **It degrades gracefully.** A rule-based local version is genuinely useful,
  which makes a safe offline fallback possible — something a feature like
  free-form resume rewriting could not offer.

---

## How the AI Request Flow Works

```
Browser (React)                Django backend (server)              AI provider
─────────────────              ───────────────────────              ───────────
Click "Generate
Skill Gap Analysis"
      │
      │  POST /api/profiles/<id>/generate-skill-gap/
      │  (no API key, no prompt — just the profile id)
      ▼
                      StudentProfileViewSet.generate_skill_gap()
                        1. get_object()  ──► 404 if the profile is gone
                        2. load profile.skills + profile.career_inputs
                        3. call ai_service.generate_skill_gap_analysis()
                                │
                                ├─ AI_PROVIDER=mock or no API key
                                │    └─► build_local_analysis()  (no network call)
                                │
                                └─ real provider configured
                                     └─ build_prompt() ────────────►  API call
                                                                      (key read
                                                                       from server
                                        text response  ◄───────────    environment)
                        4. save a Recommendation row
                        5. return JSON
      │
      ▼
Render the analysis
in AIRecommendationPanel
```

Response shape:

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

`used_fallback` tells the UI (and any reviewer) honestly whether a real AI model
was involved. `notes` explains any limitation, e.g. a profile with no skills.

---

## Why API Keys Must Stay on the Backend

Anything shipped to the browser is public. A React app is downloaded to the
user's machine, so any key inside it — even in an environment variable compiled
into the bundle — can be read from the network tab or the built JavaScript in
seconds.

The consequences of leaking an AI API key are concrete:

- **Cost.** AI APIs bill per request. A leaked key can be used by anyone until it
  is revoked, and the bill lands on this project's account.
- **No control.** Requests made with a leaked key cannot be rate-limited,
  validated, or logged by us.
- **No auditability.** There would be no record of what was sent to the provider
  on the project's behalf.

Keeping the call server-side also buys things beyond secrecy: the backend can
validate input, control exactly which student data is included in the prompt
(privacy), log usage, cap request rates, and swap providers without touching the
frontend. This matches the Week 2 architecture decision that **the backend is
the single trusted component**.

The same rule applies to the Django `SECRET_KEY` and, from Day 3, the RDS
database credentials.

---

## Environment Variables Used

Defined in `backend/.env.example`; real values go in `backend/.env` (git-ignored)
locally, and in the server environment on AWS.

| Variable | Purpose | Local value |
|---|---|---|
| `DEBUG` | Django debug mode. Must be `False` in any deployment. | `True` |
| `SECRET_KEY` | Django cryptographic signing key. | dev placeholder |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django will serve. | `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to call the API. | `http://localhost:5173,http://127.0.0.1:5173` |
| `AI_PROVIDER` | Which AI implementation to use. `mock` = local fallback, no network call. | `mock` |
| `AI_API_KEY` | Provider API key. Server-side only; empty in mock mode. | *(empty)* |
| `AI_MODEL` | Model identifier passed to the provider. | `mock-local` |
| `DB_HOST` | **The database switch.** Empty → SQLite. Set → PostgreSQL on RDS. | *(empty)* |
| `DB_NAME` | PostgreSQL database name. | *(unused locally)* |
| `DB_USER` | PostgreSQL username. | *(unused locally)* |
| `DB_PASSWORD` | PostgreSQL password. **Secret** — AWS environment only. | *(unused locally)* |
| `DB_PORT` | PostgreSQL port. | `5432` |
| `DB_SSLMODE` | libpq SSL mode; encrypts traffic to RDS. | `require` |

Two safety behaviours are built into `config/settings.py`:

- With `DEBUG=False` and no `SECRET_KEY`, Django refuses to start
  (`ImproperlyConfigured`) rather than running on a public default value.
- With `DEBUG=False`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_CONTENT_TYPE_NOSNIFF`, and `X_FRAME_OPTIONS=DENY` switch on
  automatically. HTTPS redirect and HSTS are deliberately deferred until TLS is
  terminated in front of the app on AWS.

---

## Local Testing Checklist

### Automated

```bash
cd backend
source venv/bin/activate
python manage.py test
```

Expected: `Ran 26 tests ... OK`. These require no database server, no RDS
instance, and no network access.

### Manual

| # | Step | Expected result |
|---|---|---|
| 1 | `python manage.py check` | `System check identified no issues` |
| 2 | `DEBUG=False python manage.py check` | Fails with `ImproperlyConfigured: SECRET_KEY ... required` — proves no hard-coded secret |
| 3 | Start backend, `curl http://127.0.0.1:8000/api/health/` | `{"status": "ok", ...}` |
| 4 | `GET` each of `/api/profiles/`, `/api/skills/`, `/api/career-inputs/`, `/api/recommendations/` | All `200` — Week 3 endpoints still work |
| 5 | Create a profile, a skill, and a career input through the frontend forms | Saved, visible in the summary preview |
| 6 | Click **Generate Skill Gap Analysis** | Button shows "Generating analysis...", then the analysis appears with all 7 sections |
| 7 | Read the analysis | It names the student, their target role, and their own skills — not generic filler |
| 8 | `GET /api/recommendations/` | The generated analysis is saved with `recommendation_type: "Skill Gap Analysis"` |
| 9 | `curl -X POST http://127.0.0.1:8000/api/profiles/99999/generate-skill-gap/` | `404`, clean JSON |
| 10 | Generate for a profile with no skills and no career inputs | Still returns `201`, with two entries in `notes` |
| 11 | Stop the backend, click the button again | Clear error message in the UI, no crash |
| 12 | Open the browser network tab during generation | Only `127.0.0.1:8000` is contacted — no AI provider, no API key |

### Manual — database configuration (Day 3)

| # | Step | Expected result |
|---|---|---|
| 13 | `python manage.py check_database` | Reports `sqlite3` and `OK — the database is reachable` |
| 14 | `DB_HOST=careerdb.example.invalid DB_NAME=x DB_USER=y DB_PASSWORD=z python manage.py check_database` | Reports `postgresql`, `SSL mode: require`, `Password: set (not shown)`, masked host, then fails cleanly on DNS — proves the PostgreSQL path is wired without contacting AWS |
| 15 | `DB_HOST=careerdb.example.invalid python manage.py check_database` | `ImproperlyConfigured` naming `DB_NAME, DB_USER, DB_PASSWORD` — no silent fallback to SQLite |
| 16 | Unset `DB_HOST` and re-run the app | Everything still works on SQLite; the skill-gap feature is unaffected |

Step 14 uses a deliberately unreachable placeholder host. **Do not point it at
the real RDS endpoint from a laptop** — see "Why the RDS endpoint cannot be
tested from the local laptop" above.

---

## Day 3 — Amazon RDS PostgreSQL Preparation

### Objective

Build the network and database foundation the application will run in, and make
Django able to talk to PostgreSQL — **without breaking local SQLite development
and without deploying anything yet.** Day 3 is infrastructure plus code
readiness; the application itself is still local.

### VPC and subnet design

A custom VPC was created rather than using the default VPC, so the network
boundaries are explicit and the database can be genuinely private.

```
                          ┌──────────── Custom VPC ────────────┐
                          │                                    │
   Internet ──► IGW ──────┼─►  Public subnet (AZ-a)            │
                          │      EC2 application instance      │
                          │      SG: app-sg                    │
                          │            │                       │
                          │            │ PostgreSQL 5432       │
                          │            ▼                       │
                          │    Private subnet (AZ-a) ┐         │
                          │      Amazon RDS          │ DB      │
                          │      PostgreSQL          │ subnet  │
                          │      SG: rds-sg          │ group   │
                          │                          │         │
                          │    Private subnet (AZ-b) ┘         │
                          │      (standby capacity, no         │
                          │       internet route)              │
                          └────────────────────────────────────┘
```

| Layer | Subnets | Internet route | Purpose |
|---|---|---|---|
| Application | Public, one per AZ | Yes, via Internet Gateway | EC2 instance serving Django; must be reachable over HTTPS/SSH |
| Database | **Private**, two AZs | **No** | RDS subnet group; PostgreSQL only |

Two private subnets in **two Availability Zones** are used because an RDS DB
subnet group requires subnets in at least two AZs. This is what makes a future
Multi-AZ failover possible without rebuilding the network.

### The RDS instance is private

The database is created with **public accessibility disabled** and lives only in
the private subnets, which have no route to the Internet Gateway. There is no
path from the public internet to the database — not a blocked path, an absent
one. The only way in is from inside the VPC.

### Security groups

| Security group | Inbound rule | Source |
|---|---|---|
| `app-sg` (EC2) | HTTPS / SSH | Administrator IP or load balancer (Day 4) |
| `rds-sg` (RDS) | **PostgreSQL, TCP 5432, only** | **`app-sg`** — the security group itself, not an IP range |

Referencing the application security group as the source (rather than a CIDR
block like `10.0.0.0/16`) means access is granted by *identity*, not by address:
any instance that joins `app-sg` can reach the database, and anything else in
the VPC cannot — even if it has an address in the same range, and even if
instance IPs change.

### Why the RDS endpoint cannot be tested from the local laptop

This is expected behaviour, not a fault to debug:

1. The RDS instance is **not publicly accessible** and sits in private subnets
   with no internet route, so its endpoint is not reachable from outside the VPC.
2. The RDS endpoint resolves to a **private IP address** (e.g. `10.0.x.x`). From
   a laptop, DNS either fails or returns an address that is not routable across
   the internet.
3. Even with a route, `rds-sg` only accepts traffic **from `app-sg`**, and a
   laptop is not a member of that security group.

So `psql` or `manage.py check_database` run from the laptop against the RDS
endpoint will time out or fail to resolve — **and that is the correct result.**
A database that a laptop could reach directly would mean the security design had
failed. The database is verified from the EC2 instance on Day 4 instead.

To keep this honest, no attempt was made to reach RDS from the local machine
today. The PostgreSQL code path was exercised locally using a deliberately
unreachable placeholder host, which proves Django builds the right configuration
without contacting AWS at all.

### How Django receives database configuration

Same pattern as Day 2: environment variables, no hard-coded values, one switch.

```
DB_HOST empty                 DB_HOST set (on EC2)
      │                              │
      ▼                              ▼
 SQLite file                  PostgreSQL on RDS
 backend/db.sqlite3           DB_NAME / DB_USER / DB_PASSWORD
                              DB_PORT (5432) / DB_SSLMODE (require)
                              CONN_MAX_AGE=60, CONN_HEALTH_CHECKS
                              connect_timeout=10s
```

The rule lives in `backend/config/database.py` as `build_database_config()`,
which `settings.py` calls with values read from the environment. Keeping it in a
function rather than inline in `settings.py` means the selection logic is unit
tested — nine tests cover it — with no database connection required.

Design details worth noting:

- **`DB_HOST` alone decides.** A leftover `DB_NAME` in a local `.env` cannot
  accidentally switch a laptop to PostgreSQL.
- **Fail loudly, not silently.** If `DB_HOST` is set but `DB_NAME`, `DB_USER`,
  or `DB_PASSWORD` is missing, Django refuses to start and names the missing
  variables — it never silently falls back to SQLite on a production server,
  which would look like a working deployment with an empty database.
- **`DB_SSLMODE` defaults to `require`**, so traffic between EC2 and RDS is
  encrypted in transit even though both are inside the VPC.
- **`CONN_MAX_AGE=60` with `CONN_HEALTH_CHECKS=True`.** Persistent connections
  avoid a TCP + TLS handshake on every request, but 60 seconds is short enough
  that idle Gunicorn workers do not hold RDS connection slots, and the health
  check prevents a stale connection being reused after an RDS failover.
- **`connect_timeout=10`.** Without it, a security-group misconfiguration
  presents as a hung application rather than a fast, obvious error.

### The `check_database` diagnostic command

```bash
python manage.py check_database
```

Prints which engine Django is configured to use, then runs `SELECT 1`. On Day 4
this is the first command to run on EC2: it distinguishes "Django is not reading
the environment variables" from "the security group is blocking me".

It **never prints the database password** — only whether one is set — masks the
host by default (`--show-host` to reveal), and scrubs the password from any
driver error text before displaying it. That makes it safe to run in a shared
terminal or paste into a report.

### Day 3 code changes

- `psycopg[binary]` added to `requirements.txt`; SQLite support untouched.
- `backend/config/database.py` — new, holds `build_database_config()`.
- `backend/config/settings.py` — `DATABASES` now built from `DB_*` environment
  variables.
- `backend/career/management/commands/check_database.py` — new diagnostic command.
- 14 new tests (26 total). All Day 2 AI functionality is unchanged and still passing.

No AWS resources were created or contacted by the code changes, and no
credentials were written to any file.

## Day 4 — Deploy the Django Backend to Amazon EC2

### Objective

Make the repository deployable: production Django settings, a Gunicorn service,
an Nginx site, and a repeatable deploy script — so that running one command on
the instance produces a working backend. **The repository work is complete; no
AWS resources were created and nothing has been deployed yet.**

### Who does what

```
   Internet
      │  HTTP :80
      ▼
 ┌─────────────────── EC2 (Amazon Linux 2023, public subnet) ───────────────┐
 │                                                                          │
 │   Nginx  ── public, port 80 ──────────────────────────────────┐          │
 │     • terminates the client connection                        │          │
 │     • serves /static/ from disk (Django will not, DEBUG=False)│          │
 │     • sets X-Forwarded-For / -Proto / -Host                   │          │
 │     • enforces client_max_body_size and proxy timeouts        │          │
 │                                    │ proxy_pass               │          │
 │                                    ▼                          │          │
 │   Gunicorn ── 127.0.0.1:8000, loopback only ──────────────────┘          │
 │     • runs config.wsgi:application, 2 worker processes                   │
 │     • managed by systemd (dc-intern-backend.service)                     │
 │     • logs to stdout/stderr -> journald                                  │
 │     • reads all config from /etc/dc-intern/backend.env                   │
 │                                    │                                     │
 └────────────────────────────────────┼─────────────────────────────────────┘
                                      │ PostgreSQL 5432, TLS
                                      ▼
                        Amazon RDS (private subnets, no public route)
```

| Component | Responsibility | Why it is not the other's job |
|---|---|---|
| **Nginx** | Public listener, static files, timeouts, request size limits, forwarded headers | Gunicorn is an application server, not a hardened edge server; it should never face the internet directly |
| **Gunicorn** | Runs the Django WSGI application in worker processes | Nginx cannot execute Python; `runserver` is a development server and must never be used in production |
| **systemd** | Starts Gunicorn at boot, restarts it on failure, captures logs | Keeps the service alive across reboots and crashes without anyone logging in |

Gunicorn binds to **127.0.0.1:8000**, not `0.0.0.0`. That single choice means the
application cannot be reached from outside the instance except through Nginx,
regardless of what the security group allows.

### Administration through Session Manager

Instance access uses **AWS Systems Manager Session Manager**, not SSH.

- The EC2 security group needs **no inbound SSH rule at all** — port 22 stays
  closed, which removes the single most-attacked entry point on a public
  instance.
- There is no SSH key pair to distribute, lose, or leak, and no `.pem` file to
  accidentally commit.
- Access is controlled by **IAM**, so it can be granted and revoked per person,
  and every session is logged in CloudTrail.
- It works because the instance runs the SSM agent (pre-installed on Amazon
  Linux 2023) and has an instance profile with
  `AmazonSSMManagedInstanceCore` — an outbound connection, so no inbound port
  is opened.

```bash
aws ssm start-session --target i-xxxxxxxxxxxx --profile <your-cli-profile>
sudo su - ec2-user       # sessions start as ssm-user
```

### Connecting to the private RDS instance

Nothing about Day 3's network design changes: RDS stays private, and the
security group still admits PostgreSQL only from the EC2 application security
group. What changes is that there is now something *inside* that group.

The application connects because it is running on the EC2 instance — the
credentials in `/etc/dc-intern/backend.env` are only half the story; the
instance's **security group membership** is what actually grants access. This
is why migrations are run from the instance and never from a laptop.

`DB_SSLMODE=require` keeps the EC2 → RDS hop encrypted even though both sit
inside the VPC.

### Environment file security

All configuration and every secret live in **`/etc/dc-intern/backend.env`**,
outside the repository, on the instance only.

| Property | Value | Reason |
|---|---|---|
| Path | `/etc/dc-intern/backend.env` | Outside `/opt/dc-intern`, so `git pull` and `git status` can never see or offer to commit it |
| Owner | `root:ec2-user` | Only root can modify it |
| Mode | `0640` | Only the service account can read it; other users on the box cannot |
| Source of values | AWS Systems Manager Parameter Store | Secrets have one authoritative home; the file is a local materialisation |

systemd reads the file as root (`EnvironmentFile=`) *before* dropping to
`ec2-user`, so nothing in the application ever needs elevated privileges to
obtain its own configuration.

`deploy/backend.env.example` is the committed, placeholder-only template.
`deploy/scripts/deploy_backend.sh` **never creates, fetches, edits, or prints**
the real file — it only verifies that the required keys exist, using `grep -q`,
which matches without echoing. The script also carries an explicit warning never
to enable `set -x`, which would dump every secret into the terminal.

### Production settings added today

| Setting | Value | Purpose |
|---|---|---|
| `STATIC_ROOT` | `BASE_DIR / 'staticfiles'` | Target for `collectstatic`; Nginx serves this directory |
| `CSRF_TRUSTED_ORIGINS` | from env, empty locally | Lets the admin and unsafe requests work through the EC2 hostname |
| `SECURE_PROXY_SSL_HEADER` | `('HTTP_X_FORWARDED_PROTO', 'https')` | Django learns the original scheme from Nginx — ready for HTTPS |
| `SECURE_REFERRER_POLICY`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS` | on when `DEBUG=False` | Safe over plain HTTP |
| `USE_HTTPS` | **`False`** | Gates the settings that need TLS |

**Why `USE_HTTPS` exists.** Before today, `SESSION_COOKIE_SECURE` and
`CSRF_COOKIE_SECURE` were switched on by `DEBUG=False`. On a Day 4 deployment
that serves plain HTTP on port 80, that combination does not harden anything —
it *breaks* the site, because a browser will not send a `Secure` cookie over
HTTP, so admin login and every cookie-authenticated request fails with a
confusing CSRF error. Those settings, plus `SECURE_SSL_REDIRECT` and HSTS, now
live behind `USE_HTTPS`, which is set to `True` on the day a certificate exists.
No code change is needed then — just one environment variable.

Running `python manage.py check --deploy` today therefore reports warnings
W004, W008, W012, and W016. **That is expected**, and it is exactly the list
that `USE_HTTPS=True` clears.

### AI keys are not exposed

Audited today, and unchanged by the deployment work:

- The skill-gap endpoint returns only `content`, `recommendation_type`,
  identifiers, timestamps, and provider *names* — never a key.
- The only log line that mentions the key mentions its *absence*
  (`"AI_PROVIDER=%s but no AI_API_KEY is set"`) and interpolates the provider
  name, not the key.
- `check_database` prints `Password: set (not shown)` and scrubs the password
  out of driver error text.
- Django's `SafeExceptionReporterFilter` hides settings whose names match
  `API`, `KEY`, `SECRET`, `PASS`, or `TOKEN`, so `AI_API_KEY`, `SECRET_KEY`, and
  the database password are redacted in error reports even if `DEBUG` were ever
  turned on by mistake.

### Deployment files added

```
deploy/
├── backend.env.example                 placeholders for /etc/dc-intern/backend.env
├── nginx/
│   └── dc-intern.conf.template         port 80, SERVER_NAME_PLACEHOLDER, static + proxy
├── systemd/
│   └── dc-intern-backend.service       Gunicorn, 2 workers, 127.0.0.1:8000
└── scripts/
    └── deploy_backend.sh               venv → checks → migrate → collectstatic → services
```

### Deployment verification checklist

Run on the instance, in this order. Each step isolates one layer, so a failure
tells you *where* the problem is.

| # | Command | Expected |
|---|---|---|
| 1 | `sudo systemctl status dc-intern-backend` | `active (running)` |
| 2 | `python manage.py check_database` | `postgresql`, `SSL mode: require`, `OK` |
| 3 | `curl http://127.0.0.1:8000/api/health/` | `{"status": "ok", ...}` — Gunicorn works |
| 4 | `curl http://127.0.0.1/api/health/` | Same JSON — Nginx proxying works |
| 5 | `curl http://<public-dns>/api/health/` from a laptop | Same JSON — security group and `ALLOWED_HOSTS` are right |
| 6 | `curl http://<public-dns>/api/profiles/` | `200` with a JSON list |
| 7 | `curl -X POST http://<public-dns>/api/profiles/<id>/generate-skill-gap/` | `201`, `used_fallback: true` — the AI feature survived deployment |
| 8 | Open `http://<public-dns>/admin/` | Login page **with CSS** — proves `collectstatic` + Nginx `/static/` |
| 9 | `sudo journalctl -u dc-intern-backend -n 50` | Access log lines, no tracebacks, **no secrets** |
| 10 | `sudo systemctl restart dc-intern-backend && curl http://127.0.0.1/api/health/` | Recovers automatically |
| 11 | Reboot the instance, then repeat step 4 | Still works — `systemctl enable` did its job |

### Common failure modes

| Symptom | Most likely cause | Check |
|---|---|---|
| `502 Bad Gateway` from Nginx | Gunicorn is not running | `sudo systemctl status dc-intern-backend`, then `journalctl -u dc-intern-backend -n 50` |
| Service fails instantly at boot | Bad or missing `/etc/dc-intern/backend.env`; `ImproperlyConfigured` for `SECRET_KEY` or a `DB_*` value | `journalctl -u dc-intern-backend -n 50` — the exception names the missing variable |
| `DisallowedHost` / `400 Bad Request` | The hostname used is not in `ALLOWED_HOSTS` | Add the EC2 public DNS name to `ALLOWED_HOSTS`, restart the service |
| `check_database` hangs then fails | RDS security group does not admit this instance's security group | Confirm the RDS inbound rule's source is the **EC2 security group**, not a CIDR |
| `check_database` fails instantly with a DNS error | `DB_HOST` typo, or the command is being run outside the VPC | Re-run on the instance; compare against Parameter Store |
| Admin page loads with no styling | `collectstatic` not run, or Nginx cannot read `staticfiles/` | Re-run the deploy script; `sudo -u nginx ls /opt/dc-intern/backend/staticfiles/` — `/opt/dc-intern` needs `o+rx` |
| CSRF failure in the admin | Hostname missing from `CSRF_TRUSTED_ORIGINS` (needs the scheme) | Add `http://<public-dns>`, restart |
| Everything works over HTTP, then breaks after enabling `USE_HTTPS` | TLS is not actually terminated yet | Set `USE_HTTPS=False` until a certificate is in place |
| Browser calls from the frontend fail with a CORS error | Frontend origin missing from `CORS_ALLOWED_ORIGINS` | Add the exact origin **with scheme and port**, restart |
| `504 Gateway Time-out` on the AI endpoint | `proxy_read_timeout` shorter than the AI call | Only relevant once a real provider is connected; raise it in the Nginx template |

## Current Limitations

- **No real AI provider is connected yet.** `AI_PROVIDER=mock` returns a
  rule-based local analysis. A provider has not been approved on cost grounds,
  and `_call_provider()` in `ai_service.py` is a documented stub.
- **The mock analyser is rule-based**, so it only reasons about the skills listed
  in `ROLE_PROFILES`. It matches skills by name, so unusual spellings may be
  reported as missing.
- **One AI feature only.** Career path suggestions, project recommendations, and
  learning plans are separate `RecommendationType` values with no producer yet.
- **No authentication.** Any client can generate an analysis for any profile.
  Adding auth is required before this is exposed publicly.
- **No rate limiting.** Once a paid provider is connected, the endpoint needs a
  throttle so repeated clicks cannot run up a bill.
- **Still SQLite in practice.** PostgreSQL support is written and tested, but no
  migration has been run against RDS and no application has connected to it. The
  PostgreSQL code path has only been exercised against a placeholder host.
- **No connection pooler.** `CONN_MAX_AGE=60` is per Gunicorn worker, so total
  connections scale with worker count. If workers are scaled up, RDS connection
  limits need checking (PgBouncer or RDS Proxy is the answer, not more workers).
- **`DB_SSLMODE=require` encrypts the connection but does not verify the server
  certificate.** It stops passive eavesdropping, not an active
  machine-in-the-middle. Full verification needs `DB_SSLMODE=verify-full` plus
  the Amazon RDS CA bundle on the instance and an `sslrootcert` option — worth
  doing once the CA bundle is downloaded on EC2 in Day 4. The setting is already
  environment-driven, so this is a configuration change, not a code change.
- **Database backups, snapshots, and rotation of the RDS password are not yet
  configured.**
- **No TLS.** The site is served over plain HTTP on port 80, so traffic between
  a browser and EC2 is unencrypted. `USE_HTTPS` is the switch that fixes this
  once a certificate exists; until then, do not use the deployment for anything
  involving real personal data.
- **No deployment has actually been run.** Every file in `deploy/` has been
  syntax-checked and the script's preflight and Django stages were exercised
  locally against a scratch copy, but no EC2 instance has executed it.
- **The deploy script assumes `git pull` has already happened** and has no
  rollback step. If a deployment fails after `migrate`, recovery is manual.
- **No process supervision beyond `Restart=on-failure`** and no health check
  wired to anything that would notice an outage.
- **The frontend still shows only session-scoped skills/career inputs**, so an
  analysis generated for a reloaded profile may be richer than what the summary
  panel displays.

---

## Executing the Day 4 Deployment

The repository is ready; these are the steps to run on the instance. Everything
happens **from inside the VPC**, because that is the only place the database is
reachable from.

1. Launch the EC2 instance (Amazon Linux 2023) into a public application subnet
   with the application security group and an instance profile granting
   `AmazonSSMManagedInstanceCore`. **No inbound SSH rule.**
2. Connect with Session Manager, install prerequisites, and clone the repo:
   ```bash
   sudo dnf install -y git python3.12 python3.12-pip nginx
   sudo install -d -o ec2-user -g ec2-user /opt/dc-intern
   git clone <repo-url> /opt/dc-intern
   ```
3. Create the environment file from the committed template and fill in the real
   values from Parameter Store:
   ```bash
   sudo install -d -m 750 -o root -g ec2-user /etc/dc-intern
   sudo cp /opt/dc-intern/deploy/backend.env.example /etc/dc-intern/backend.env
   sudo chown root:ec2-user /etc/dc-intern/backend.env && sudo chmod 640 /etc/dc-intern/backend.env
   sudo nano /etc/dc-intern/backend.env
   ```
4. Make sure Nginx can traverse to the static directory:
   `sudo chmod o+rx /opt/dc-intern /opt/dc-intern/backend`
5. Deploy:
   ```bash
   SERVER_NAME=<ec2-public-dns> /opt/dc-intern/deploy/scripts/deploy_backend.sh
   ```
   The script creates the virtualenv, installs requirements, runs `check`,
   `check --deploy`, `check_database`, `migrate`, and `collectstatic`, installs
   and starts the systemd unit, renders and validates the Nginx site, restarts
   Nginx, and smoke-tests both layers.
6. Create an admin user: `python manage.py createsuperuser` (with the
   environment file sourced).
7. Work through the verification checklist above.

## Next Step — Day 5: Deploy the Frontend and Complete Week 4 Documentation

1. Build the React app (`npm run build`) with the API base URL pointing at the
   deployed backend instead of `127.0.0.1:8000` — it is currently hard-coded in
   `frontend/src/services/api.js` and needs to become a build-time variable.
2. Serve the built frontend: either from Nginx on the same instance, or from S3
   (with CloudFront later). Decide and document the trade-off.
3. Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the frontend's real
   origin and restart the backend service.
4. Verify the full user journey against the deployed stack: create a profile,
   add skills, add a career input, generate a skill-gap analysis.
5. Add TLS (certificate + port 443 server block + redirect), then set
   `USE_HTTPS=True` and re-run `manage.py check --deploy` — the four expected
   warnings should disappear.
6. Ship application logs to CloudWatch and confirm the billing alert still
   reflects the running resources.
7. Complete the Week 4 report: architecture as-built, screenshots, costs, and
   the security decisions taken.
8. Only after all of the above, evaluate connecting a real AI provider — with a
   spending cap and endpoint rate limiting in place first.
