# Frontend — AI-Powered Student Career and Internship Assistant

This is the React frontend for the project, built with **React** and **Vite**.

## What the frontend does

Provides the MVP forms and pages a student uses to:

1. Create a student profile
2. Add skills
3. Add resume text or a career/internship goal
4. Preview a summary of everything saved
5. Generate an AI-assisted **skill gap analysis** for the current profile

The field names and choice values in each form match the backend
`StudentProfile`, `Skill`, and `CareerInput` models exactly. Submitting
these forms saves the data directly to the Django REST API — this is a
working local MVP, not a UI mockup.

## Project structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ProfileForm.jsx
│   │   ├── SkillsForm.jsx
│   │   ├── CareerInputForm.jsx
│   │   ├── SummaryPreview.jsx
│   │   └── AIRecommendationPanel.jsx
│   ├── pages/
│   │   └── Home.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
└── README.md
```

## Setup

### 1. Install dependencies

From inside the `frontend/` folder:

```bash
npm install
```

### 2. Configure the API base URL (optional locally)

The frontend talks to exactly one server: the Django backend. Its address comes
from a single build-time variable.

```bash
cp .env.example .env      # optional — the default already points at local Django
```

`frontend/.env.example` contains the one variable the project uses:

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

| Environment | `VITE_API_BASE_URL` | Result |
|---|---|---|
| Local development | unset (or the value above) | `http://127.0.0.1:8000/api` |
| Production | `/api` | The page's own origin — Nginx proxies `/api/` to Django |

The production value is **relative on purpose**. No IP address or hostname is
compiled into the bundle, so the build keeps working when the EC2 instance's
public IP changes, and it keeps working the day a domain name and HTTPS are
added. It also means the browser makes no cross-origin request at all: no CORS
preflight, no origin list to keep in step with the server.

Real `.env` files are git-ignored; only `.env.example` is committed. That is
housekeeping, not security — **every `VITE_*` value is compiled into the public
bundle**, so a secret must never be put in one in the first place.

### 3. Run the frontend locally

```bash
npm run dev
```

The app will be available at `http://localhost:5173/`.

**The backend must also be running** (see `../backend/README.md`) at
`http://127.0.0.1:8000/` for the forms to save anything. To run both
together:

```bash
# Terminal 1
cd backend
source venv/bin/activate
python manage.py runserver

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173/`. The page loads any existing profile from
the backend automatically; use the forms to save a new profile, add
skills, and add resume/career-goal entries.

## Components

- **`pages/Home.jsx`** — the single page of the app. Fetches existing
  profiles from the backend on load, tracks the current profile and the
  skills/career inputs saved during the session, and shows a simple MVP
  workflow status (profile created / skills added / career input
  submitted).
- **`components/ProfileForm.jsx`** — creates a `StudentProfile` via the
  API. Validates required fields, shows a "Saving profile..." loading
  state, a success or error message, resets only after a successful save,
  and passes the created profile (with its database `id`) up to `Home`.
- **`components/SkillsForm.jsx`** — creates a `Skill` linked to the
  current profile's `id`. Shows a message asking the user to save a
  profile first if none exists yet.
- **`components/CareerInputForm.jsx`** — creates a `CareerInput` linked to
  the current profile's `id`, with the same guard and messaging pattern as
  `SkillsForm`.
- **`components/SummaryPreview.jsx`** — displays the current profile and
  everything saved during the session.
- **`components/AIRecommendationPanel.jsx`** — the Week 4 AI feature. See
  below.
- **`services/api.js`** — small `fetch`-based helper module wrapping every
  API call the app makes.

## Skill Gap Analysis feature (Week 4)

`AIRecommendationPanel.jsx` adds a **"Generate Skill Gap Analysis"** button
below the summary preview.

- The button is **disabled until a student profile exists** — the analysis needs
  a profile to work from — and while a request is in flight.
- Clicking it calls `POST /api/profiles/<id>/generate-skill-gap/` on the Django
  backend.
- While the request runs, the button reads "Generating analysis..." and a
  loading hint is shown.
- On success the panel renders the recommendation type, when it was generated,
  the analysis text, and any `notes` the backend returned (for example, that the
  profile had no skills saved, so the analysis is limited).
- On failure it shows a readable error message and leaves the previous result
  in place; the page never crashes.
- A standing note explains: *"This is the Week 4 AI-assisted feature. In local
  mode, it may use a mock AI response unless a real AI provider is configured."*

### How the frontend calls the backend

Every request goes through `src/services/api.js`, which wraps `fetch` and points
at `API_BASE_URL` (`/api` in production, `http://127.0.0.1:8000/api` locally).
The skill-gap request sends **no body** — the profile id in the URL is all the
backend needs — and no credentials of any kind.

Error text shown to a user is written in `api.js`. The backend's own
`error`/`detail` messages are safe to display, but anything else — a network
failure, an Nginx HTML error page, an unparseable body — is replaced with a plain
sentence. **No stack trace, server traceback, or AWS error payload is ever
rendered.**

### What the panel tells the user about the AI

The backend reports which implementation actually produced the text, and the
panel repeats it verbatim:

| Response | Shown as |
|---|---|
| `provider: "bedrock"` | "Generated by Amazon Bedrock · amazon.nova-micro-v1:0" |
| `provider: "mock"`, `fallback_used: true` | "Generated by the local rule-based analyser on the server — no AI model was used" |

If a Bedrock call fails and the server falls back, the panel also shows the
backend's `notes` explaining why. **A rule-based response is never presented as
model output.**

Every result carries a standing disclaimer: the analysis is AI-assisted, may be
incomplete or wrong, cannot verify claimed skills, is not a guarantee of an
internship or a job, and should be reviewed with a lecturer, mentor, or
supervisor.

### The frontend never calls an AI provider directly

This app talks to **one server: the Django backend.** It does not import an AI
SDK, holds no credential, and does not know which provider is in use. On AWS,
Django calls Amazon Bedrock using the EC2 instance's IAM role — there is no API
key anywhere in the system, and certainly not here.

This is not a style preference. Anything in a React bundle is downloaded to the
user's machine, so a key placed here — including in a `VITE_*` environment
variable — is readable from the browser's network tab or the built JavaScript.
A leaked AI key can be used by anyone until it is revoked, and the bill lands on
this project's account. **Never add an AI credential to this folder.**

## API Integration

`src/services/api.js` exports:

| Function | Endpoint |
|---|---|
| `getStudentProfiles()` | `GET /api/profiles/` |
| `createStudentProfile(data)` | `POST /api/profiles/` |
| `getSkills()` | `GET /api/skills/` |
| `createSkill(data)` | `POST /api/skills/` |
| `getCareerInputs()` | `GET /api/career-inputs/` |
| `createCareerInput(data)` | `POST /api/career-inputs/` |
| `getRecommendations()` | `GET /api/recommendations/` |
| `generateSkillGapAnalysis(profileId)` | `POST /api/profiles/<id>/generate-skill-gap/` |

The UI currently calls `getStudentProfiles` (on page load),
`createStudentProfile`, `createSkill`, `createCareerInput`, and
`generateSkillGapAnalysis`. The `get*` helpers for skills, career inputs, and
recommendations are implemented and ready to use but not yet called from the UI.

CORS is configured on the backend (`CORS_ALLOWED_ORIGINS` in
`backend/config/settings.py`) to allow `http://localhost:5173`, so no
frontend-side CORS workaround is needed. **In production there is no
cross-origin request at all** — Nginx serves this app and the API from one
origin.

## Production build and deployment (Week 4 Day 5)

```bash
# Build for the deployed, same-origin setup
VITE_API_BASE_URL=/api npm run build      # output: dist/

# Build with the local default (http://127.0.0.1:8000/api)
npm run build
```

On the EC2 instance, `deploy/scripts/deploy_frontend.sh` does the whole thing:
`npm ci`, build with `VITE_API_BASE_URL=/api`, publish `dist/` to
`/var/www/dc-intern` with read-only permissions, validate and reload Nginx, and
smoke-test `/`, a deep link, and `/api/health/`. It **fails the deployment** if
`127.0.0.1:8000` appears in a same-origin build — the signature of a stale
`.env`.

Nginx serves the app with `try_files $uri $uri/ /index.html`, so a refresh or a
shared deep link returns the app rather than a 404. Vite's fingerprinted files
in `/assets/` are cached for a year as `immutable`; `index.html` is served
`no-cache`, because it is not fingerprinted and is what points at the hashed
bundles.

Node.js is needed **only to build**. Nothing runs Node in production.

> **Status:** the build has been verified locally in both modes; the deployment
> script has not yet been run on the EC2 instance. See
> [`../docs/WEEK4_DEPLOYMENT_NOTES.md`](../docs/WEEK4_DEPLOYMENT_NOTES.md).

## Week 3 Status

The frontend is feature-complete for the Week 3 MVP: project scaffold,
homepage, three working forms, a live summary preview, and full
integration with the backend API. Verified manually end to end — see
`../docs/WEEK3_MVP_BUILD.md` for the full week summary and test checklist.

## Week 4 Day 2 Status

Added `AIRecommendationPanel.jsx` and the `generateSkillGapAnalysis` API helper,
so a student can request an AI-assisted skill gap analysis through the backend.
See `../docs/WEEK4_AI_AND_DEPLOYMENT.md` for the request flow and the local
testing checklist.

## Week 4 Day 5 Status

Production-ready and buildable for deployment:

- `VITE_API_BASE_URL` drives the API base URL; **no IP or hostname is compiled
  into the bundle** (verified by grepping both builds).
- `.env.example` added; real `.env*` files are git-ignored.
- Error messages are written for users — no traceback, no raw server body.
- The AI panel shows a spinner with an `aria-live` status, an honest provider
  label, the backend's fallback notes, preserved line breaks, and a standing
  "AI-assisted — please review" disclaimer.
- Built and lint-checked locally: 205 KB bundle (64 KB gzipped), no lint errors.

## Current Limitations

- **No routing.** Single page with all sections shown together.
- **Session-scoped skills/career-input list.** The summary preview only
  shows skills and career inputs saved *during the current browser
  session* — it doesn't fetch a saved profile's existing skills/career
  inputs from the backend on load (only the profile itself is loaded).
- **No update/delete from the UI.** Only creating new records is
  supported; editing or removing a saved profile, skill, or career input
  requires the Django admin or API directly.
- **Minimal validation.** Only checks that required fields are non-empty;
  no format validation.
- **No authentication.** Any visitor can create and view any data.
- **Skill gap analysis only.** Career path suggestions, project ideas, and
  learning plans are not wired up yet.
- **Mock AI by default.** With the backend in `AI_PROVIDER=mock` mode the
  analysis is generated by a rule-based local analyser, not an AI model. The
  panel says so explicitly. Amazon Bedrock is implemented on the backend but has
  not been enabled or called.
- **No client-side routing**, so the SPA fallback in Nginx currently only serves
  refreshes of `/`. It is in place ahead of routing being added.
- **No recommendation history in the UI.** Only the analysis generated during
  this session is displayed, although every one is saved to the backend and
  visible at `/api/recommendations/`.
