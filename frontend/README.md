# Frontend — AI-Powered Student Career and Internship Assistant

This is the React frontend for the project, built with **React** and **Vite**.

## What the frontend does

Provides the MVP forms and pages a student uses to:

1. Create a student profile
2. Add skills
3. Add resume text or a career/internship goal
4. Preview a summary of everything saved

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
│   │   └── SummaryPreview.jsx
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
  everything saved during the session, plus a note that AI-generated
  recommendations are coming in Week 4.
- **`services/api.js`** — small `fetch`-based helper module wrapping every
  API call the app makes.

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

The UI currently calls `getStudentProfiles` (on page load),
`createStudentProfile`, `createSkill`, and `createCareerInput`. The `get*`
helpers for skills, career inputs, and recommendations are implemented and
ready to use but not yet called from the UI.

CORS is configured on the backend (`CORS_ALLOWED_ORIGINS` in
`backend/config/settings.py`) to allow `http://localhost:5173`, so no
frontend-side CORS workaround is needed.

## Week 3 Status

The frontend is feature-complete for the Week 3 MVP: project scaffold,
homepage, three working forms, a live summary preview, and full
integration with the backend API. Verified manually end to end — see
`../docs/WEEK3_MVP_BUILD.md` for the full week summary and test checklist.

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
- **No AI-generated recommendations yet** — that's Week 4.
