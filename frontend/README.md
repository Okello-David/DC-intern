# Frontend — AI-Powered Student Career and Internship Assistant

This is the React frontend for the project, built with **React** and **Vite**.

## What the frontend does

Provides the MVP forms and pages a student uses to:

1. Create a student profile
2. Add skills
3. Add resume text or a career/internship goal
4. Preview a summary of everything entered

The field names and choice values in each form match the backend
`StudentProfile`, `Skill`, and `CareerInput` models exactly. As of Week 3
Day 4, submitting these forms saves the data directly to the Django REST
API — this is a working local MVP, not just a UI mockup.

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

## Install dependencies

From inside the `frontend/` folder:

```bash
npm install
```

## Run the frontend locally

```bash
npm run dev
```

The app will be available at `http://localhost:5173/`.

**The backend must also be running** (see `../backend/README.md`) at
`http://127.0.0.1:8000/` for the forms to save anything — see
[Week 3 Day 4: Frontend-Backend Integration](#week-3-day-4-frontend-backend-integration)
below for how to run both together.

## Week 3 Day 3 status

- React + Vite project scaffolded and cleaned of template boilerplate.
- Homepage (`pages/Home.jsx`) explains the project, its purpose, MVP status,
  and the 4-step user workflow.
- `ProfileForm`, `SkillsForm`, and `CareerInputForm` are working, validated
  local forms using the same field names and choice values as the backend
  models.
- `SkillsForm` and `CareerInputForm` support adding multiple entries (matching
  the backend's one-to-many relationship from a profile to its skills and
  career inputs), with the ability to remove an entry.
- `SummaryPreview` renders a live preview of everything entered, sourced
  entirely from React state.
- `src/services/api.js` exports `API_BASE_URL` pointing at the local Django
  server, ready to be used on Day 4.
- Verified manually in a headless browser: all forms update state correctly,
  the summary preview reflects live input, and the page renders cleanly on
  both desktop and mobile widths with no console errors.

## Current limitations

- **No backend integration yet.** Nothing entered in the forms is sent to
  the Django API — it only lives in local React state and disappears on
  page refresh.
- **No routing.** This is a single page; all four sections are shown
  together rather than as separate routes/steps.
- **No client-side validation beyond required-field checks** on the "Add"
  buttons for skills and career inputs.
- **No authentication.**

## Next step: connect frontend to backend API

Done — see the section below.

## Week 3 Day 4: Frontend-Backend Integration

### What was connected

- `src/services/api.js` now exports real fetch-based helper functions
  (`createStudentProfile`, `getStudentProfiles`, `createSkill`, `getSkills`,
  `createCareerInput`, `getCareerInputs`, `getRecommendations`) that call
  the Django REST API instead of just holding a base URL.
- `ProfileForm` submits directly to the backend, shows a "Saving
  profile..." loading state, a success or error message, resets only after
  a successful save, and passes the created profile (with its database
  `id`) up to `Home`.
- `SkillsForm` and `CareerInputForm` submit to the backend using the
  current profile's `id`. If no profile has been saved yet, they show a
  message asking the user to save one first instead of submitting.
- `Home.jsx` fetches existing profiles from the backend on page load (so a
  profile created in a previous session is picked up automatically),
  tracks the current profile and the skills/career inputs saved during the
  current session, and renders a simple MVP workflow status (profile
  created / skills added / career input submitted).
- `SummaryPreview` now displays data that has actually been saved to the
  backend, plus a note that AI-generated recommendations are coming in
  Week 4.
- CORS was already configured correctly in Week 3 Day 1
  (`CORS_ALLOWED_ORIGINS` in `backend/config/settings.py` includes
  `http://localhost:5173`), so no backend changes were needed for this.

### API endpoints used

| Endpoint | Used for |
|---|---|
| `GET /api/profiles/` | Loading existing profiles on page load |
| `POST /api/profiles/` | Saving the student profile form |
| `POST /api/skills/` | Saving each skill |
| `POST /api/career-inputs/` | Saving each resume/career goal entry |

`getSkills`, `getCareerInputs`, and `getRecommendations` are implemented in
`api.js` for later use but not yet called from the UI.

### How to run backend and frontend together

In one terminal:

```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/`. The page will load any existing profile from
the backend automatically; use the forms to save a new profile, add
skills, and add resume/career-goal entries.

### Current limitations

- **No routing.** Still a single page with all sections shown together.
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

### Next step: testing, cleanup, README update, and Week 3 report

- Manually re-test the full flow end to end.
- Review and clean up the frontend and backend code.
- Finalize README documentation for both halves of the app.
- Write the Week 3 summary report.
