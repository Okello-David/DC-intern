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

### 2. Run the frontend locally

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
at `API_BASE_URL` (`http://127.0.0.1:8000/api` locally). The skill-gap request
sends **no body** — the profile id in the URL is all the backend needs — and no
credentials of any kind.

### The frontend never calls an AI provider directly

This app talks to **one server: the Django backend.** It does not import an AI
SDK, does not hold an AI API key, and does not know which provider is in use.
Django reads `AI_API_KEY` from its own server environment and makes the provider
call itself.

This is not a style preference. Anything in a React bundle is downloaded to the
user's machine, so a key placed here — including in a `VITE_*` environment
variable — is readable from the browser's network tab or the built JavaScript.
A leaked AI key can be used by anyone until it is revoked, and the bill lands on
this project's account. **Never add an AI API key to this folder.**

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
frontend-side CORS workaround is needed.

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
- **Mock AI locally.** With the backend in `AI_PROVIDER=mock` mode the analysis
  is generated by a rule-based local analyser, not a real AI model. The panel
  labels this as a local mock response.
- **No recommendation history in the UI.** Only the analysis generated during
  this session is displayed, although every one is saved to the backend and
  visible at `/api/recommendations/`.
