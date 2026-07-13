# Frontend — AI-Powered Student Career and Internship Assistant

This is the React frontend for the project, built with **React** and **Vite**.

## What the frontend does

Provides the MVP forms and pages a student uses to:

1. Create a student profile
2. Add skills
3. Add resume text or a career/internship goal
4. Preview a summary of everything entered

The field names and choice values in each form match the backend
`StudentProfile`, `Skill`, and `CareerInput` models exactly, so the data is
ready to send to the API once integration happens.

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

The backend (see `../backend/README.md`) should be running separately at
`http://127.0.0.1:8000/` if you want the base API URL configured in
`src/services/api.js` to eventually resolve correctly — it isn't called yet
(see limitations below).

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

Week 3 Day 4 will:

- Use `API_BASE_URL` in `src/services/api.js` to call the `/api/profiles/`,
  `/api/skills/`, `/api/career-inputs/`, and `/api/recommendations/`
  endpoints.
- Persist the profile, skills, and career inputs entered in these forms to
  the backend instead of only keeping them in local state.
- Load and display saved data from the backend in `SummaryPreview`.
