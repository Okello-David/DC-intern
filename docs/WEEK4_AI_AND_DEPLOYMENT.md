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
| **Day 2** | **First AI feature (Skill Gap Analysis) locally + production-ready Django settings** | **This document** |
| Day 3+ | Amazon RDS, EC2 deployment, environment variables on the server | Next |

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

Expected: `Ran 12 tests ... OK`.

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

---

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
- **Still SQLite.** No production database yet.
- **The frontend still shows only session-scoped skills/career inputs**, so an
  analysis generated for a reloaded profile may be richer than what the summary
  panel displays.

---

## Next Step — AWS RDS and Deployment Preparation

1. Provision PostgreSQL on Amazon RDS (free tier), locked to the EC2 security
   group only.
2. Add `psycopg` and read `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
   `DB_PORT` from the environment — the same pattern established today.
3. Run migrations against RDS and confirm the API works against PostgreSQL.
4. Provision and harden an EC2 instance; deploy Django behind Gunicorn and Nginx
   with `DEBUG=False` and a real `SECRET_KEY` in the server environment.
5. Build and serve the React production build; set `CORS_ALLOWED_ORIGINS` and
   `ALLOWED_HOSTS` to the deployed origins.
6. Attach a least-privilege IAM role and ship logs to CloudWatch.
7. Only then evaluate connecting a real AI provider, with a spending cap and
   rate limiting in place first.
