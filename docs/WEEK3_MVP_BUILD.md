# Week 3 — Minimum Viable Product Build

## Objective

Build a working local MVP of the AI-Powered Student Career and Internship
Assistant: a Django REST API backend with real data persistence, a React
frontend with working forms, and a frontend-backend integration that lets a
student create a profile, add skills, and submit resume/career-goal text —
all stored in a local SQLite database. No AI integration, cloud deployment,
or authentication was in scope for this week; those are Week 4+ concerns.

## What Was Built This Week

| Day | Focus | Outcome |
|---|---|---|
| 1 | Backend foundation | Django + DRF project (`backend/`), CORS configured, SQLite database, working `GET /api/health/` |
| 2 | Backend models & API | `StudentProfile`, `Skill`, `CareerInput`, `Recommendation` models, serializers, `ModelViewSet` CRUD endpoints, Django admin registration |
| 3 | Frontend setup | React + Vite project (`frontend/`), homepage, `ProfileForm`, `SkillsForm`, `CareerInputForm`, `SummaryPreview` (local state only) |
| 4 | Frontend-backend integration | Forms submit to the live API, loading/success/error states, current-profile tracking, MVP workflow status |
| 5 | Testing, cleanup, documentation | End-to-end manual testing, small code cleanup, this document, README updates for all three levels of the repo |

## Backend Features Completed

- Django REST Framework project (`config`) with a single app (`career`)
- SQLite database for local development
- `django-cors-headers` configured to allow the Vite dev server
  (`http://localhost:5173`) to call the API
- Four models with realistic choice fields matching the domain:
  - `StudentProfile` — full name, field of study, year of study, career
    interest, internship goal, timestamps
  - `Skill` — linked to a profile, name, category, confidence level,
    evidence
  - `CareerInput` — linked to a profile, input type (resume text / career
    goal / internship goal), content
  - `Recommendation` — linked to a profile, recommendation type, content
    (unused by the frontend yet; reserved for Week 4 AI output)
- A `ModelSerializer` for each model
- A `ModelViewSet` + `DefaultRouter` for each model, giving full CRUD over
  HTTP
- All four models registered in Django admin with list display, filters,
  and search
- One migration (`0001_initial.py`) capturing all four models

## Frontend Features Completed

- React + Vite project with a clean, purpose-built structure
  (`components/`, `pages/`, `services/`)
- Homepage (`pages/Home.jsx`) explaining the project, its purpose, and the
  4-step user workflow, plus a live MVP workflow status indicator
- `ProfileForm` — creates a `StudentProfile` via the API, with required-field
  validation, a loading state, and success/error messaging
- `SkillsForm` — creates a `Skill` linked to the current profile, blocked
  with a clear message if no profile has been saved yet
- `CareerInputForm` — creates a `CareerInput` linked to the current profile,
  same guard and messaging pattern as `SkillsForm`
- `SummaryPreview` — shows the current profile and everything saved during
  the session, with a note that AI-generated recommendations arrive in
  Week 4
- `services/api.js` — small `fetch`-based helper module wrapping all API
  calls used by the app
- Plain CSS (`index.css`) — clean, readable, and responsive down to mobile
  widths, no CSS framework

## API Endpoints Completed

| Endpoint | Methods | Purpose |
|---|---|---|
| `/api/health/` | `GET` | Confirms the API is reachable |
| `/api/profiles/` | `GET`, `POST` | List / create student profiles |
| `/api/profiles/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve / update / delete a profile |
| `/api/skills/` | `GET`, `POST` | List / create skills |
| `/api/skills/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve / update / delete a skill |
| `/api/career-inputs/` | `GET`, `POST` | List / create resume/career-goal entries |
| `/api/career-inputs/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve / update / delete a career input |
| `/api/recommendations/` | `GET`, `POST` | List / create recommendations (not yet used by the UI) |
| `/api/recommendations/<id>/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve / update / delete a recommendation |

The frontend currently calls `GET/POST /api/profiles/`,
`POST /api/skills/`, and `POST /api/career-inputs/`. The remaining
endpoints are implemented and manually verified but not yet wired into
the UI.

## Local Testing Checklist

### Backend tests

- [ ] Start the backend server: `cd backend && source venv/bin/activate && python manage.py runserver`
- [ ] Test `GET http://127.0.0.1:8000/api/health/` → returns `{"status": "ok", ...}`
- [ ] Test `GET http://127.0.0.1:8000/api/profiles/` → returns a list (200)
- [ ] Test `GET http://127.0.0.1:8000/api/skills/` → returns a list (200)
- [ ] Test `GET http://127.0.0.1:8000/api/career-inputs/` → returns a list (200)
- [ ] Test `GET http://127.0.0.1:8000/api/recommendations/` → returns a list (200)

### Frontend tests

- [ ] Start the frontend server: `cd frontend && npm run dev`
- [ ] Open `http://localhost:5173/` and confirm the homepage renders
- [ ] Submit a student profile → success message appears, form resets
- [ ] Submit a skill linked to the profile → success message appears
- [ ] Submit a career/resume input linked to the profile → success message appears
- [ ] Confirm all three success messages are clear and readable
- [ ] Confirm the submitted profile appears in `GET /api/profiles/`
- [ ] Confirm the submitted skill appears in `GET /api/skills/` with the correct `student_profile` id
- [ ] Confirm the submitted career input appears in `GET /api/career-inputs/` with the correct `student_profile` id
- [ ] Confirm the summary preview displays the current session's profile, skills, and career inputs
- [ ] Confirm no errors appear in the browser console

All of the above were run manually during Week 3 Day 5 using the Django
dev server and Vite dev server together, driven through a headless
browser. Result: all steps passed, zero console errors.

## Current Limitations

- **No AI integration.** `Recommendation` records exist in the data model
  but nothing generates them yet.
- **No AWS deployment.** Everything runs locally against SQLite.
- **No authentication.** Any client can read or write any record.
- **No routing** in the frontend — a single page shows all sections.
- **No edit/delete UI.** The frontend can only create records; changing or
  removing data requires the Django admin or direct API calls.
- **Session-scoped summary.** The summary preview only shows skills and
  career inputs created during the current browser session — it does not
  fetch a profile's full historical list from the backend on load.
- **Minimal validation.** Only required-field checks; no format validation
  (e.g. no length limits enforced beyond the database column sizes).

## Known Issues

None outstanding. All manual tests in the checklist above pass, `npm run
build` and `npm run lint` complete cleanly, and `python manage.py check`
reports no issues.

## Next Step: Week 4 — AI Feature and AWS Deployment

- Integrate an API-based AI provider to generate real `Recommendation`
  records (skill gap analysis, career path suggestions, project ideas,
  learning plans) from a student's profile, skills, and career inputs.
- Begin AWS deployment planning: move from SQLite to PostgreSQL/Amazon RDS,
  and deploy the backend and frontend to their planned AWS services (per
  `docs/WEEK2_SYSTEM_DESIGN.md`).
- Introduce authentication once the app needs to distinguish between
  different students' data.

---

### Weekly Internship Report — Week 3

#### 1. What I researched this week

- Django REST Framework patterns for model serialization and viewset-based
  CRUD APIs (`ModelSerializer`, `ModelViewSet`, `DefaultRouter`).
- `django-cors-headers` configuration for allowing a separately-hosted
  frontend to call the API during local development.
- React state-lifting patterns for coordinating multiple forms that share
  a common parent entity (a student profile owning skills and career
  inputs).
- Practical `fetch`-based API client patterns in React without pulling in
  a full HTTP client library.

#### 2. What I built this week

- A complete Django REST Framework backend: four data models, serializers,
  CRUD API endpoints, and Django admin registration.
- A complete React frontend: a homepage, three data-entry forms, and a
  summary preview component.
- A working frontend-to-backend integration: profile, skill, and
  career-input forms now save real data to the Django API, with loading,
  success, and error states.
- Documentation across three README files (root, backend, frontend) plus
  this Week 3 summary document.

#### 3. Key technical decisions

- **SQLite for local development, PostgreSQL/RDS later** — avoids setting
  up a database server before there's a schema worth persisting.
- **`TextChoices` for all choice fields** — keeps valid values enforced at
  the model layer and human-readable in the Django admin, instead of
  encoding choices only in the frontend.
- **`fetch` instead of axios** — the app only needs a handful of GET/POST
  calls; adding a dependency for that wasn't justified.
- **Lifting the current profile up to `Home.jsx`** rather than having each
  form manage its own copy of the profile — this is what lets `SkillsForm`
  and `CareerInputForm` know which profile to attach new records to.
- **No remove/delete UI for skills and career inputs** — once Day 4 made
  these records persist to the backend, a local-only "remove" button would
  have been misleading (it wouldn't have deleted the backend record), so
  it was dropped rather than built out further.

#### 4. Challenges faced

- Keeping the frontend's per-session skill/career-input list in sync with
  what's actually in the backend, without over-building a full
  fetch-on-load system for every related model.
- Making sure the DRF browsable API, `curl`, and the React frontend all
  agreed on the same field names and choice values, since a mismatch would
  fail silently as a 400 error with a JSON body rather than a crash.
- Verifying UI behavior without a graphical environment — this required
  driving a headless browser directly to check console errors, form state,
  and rendered output rather than relying on visual inspection alone.

#### 5. How I attempted to solve them

- Scoped the summary preview explicitly to "this session" and said so in
  the UI copy, rather than pretending it was a full historical view.
- Cross-checked model field names, `TextChoices` values, and serializer
  fields against the frontend form field names and dropdown options line
  by line before wiring up the API calls.
- Used a headless Chromium instance to load the app, fill in and submit
  each form, capture screenshots, and read back console output — the same
  checks a human would do in a browser, just automated.

#### 6. What I need guidance on

- Whether the Week 4 AI integration should call the AI provider
  synchronously from a DRF view (simplest) or whether a background task
  queue is expected at this stage of the project.
- Confirmation on which AWS services to target first for deployment
  (e.g., Elastic Beanstalk vs. ECS vs. EC2) now that the MVP is stable
  enough to deploy.

#### 7. Evidence of progress

- Working health-check endpoint: `GET /api/health/`
- Four backend models with serializers, viewsets, and admin registration
- Nine API routes across `/api/profiles/`, `/api/skills/`,
  `/api/career-inputs/`, and `/api/recommendations/`
- A React frontend with four working components and one page, all
  connected to the live API
- A full manual test pass (see checklist above) with zero console errors
  and correctly persisted records confirmed via direct API calls
- Three updated README files and this Week 3 summary document
