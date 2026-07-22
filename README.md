# AI-Powered Student Career and Internship Assistant

A web application that helps university students in IT-related fields prepare for internships and early-career opportunities. Students create a profile, list their technical skills, provide resume text or a career goal, and receive AI-assisted recommendations on career paths, missing skills, project ideas, learning plans, and internship readiness.

**Internship context:** Six-week software engineering internship project at Definite Creations, combining cloud engineering (AWS), AI integration, cybersecurity, and software engineering practice.

---

## Week 1 — Project Selection and Research Proposal

> If your repository already contains the original Week 1 section, keep that version and replace this summary — do not lose the sealed proposal wording.

### Problem Statement

Many undergraduate students in IT-related fields, particularly in Uganda, struggle to translate classroom learning into employable technical skills. They often do not know which career path fits their skills, which skills they are missing for their target roles, or what practical projects would strengthen their internship applications. Career guidance is limited and rarely personalized to a student's actual skill profile.

### Target Users

Undergraduate students in Software Engineering, Computer Science, Information Technology, Information Systems, Cybersecurity, Data Science, Computer Engineering, and related IT fields preparing for internships or early-career opportunities.

### Proposed Features

- Student profile creation (name, institution, program, year of study)
- Technical skills input with self-assessment
- Resume text or career-goal input
- AI-assisted recommendations: career paths, skill-gap analysis, project ideas, learning plans, internship readiness
- Recommendation history

### Initial Direction

AWS was selected as the cloud platform to align the project with cloud engineering learning goals. A GitHub repository was created with this README, and the one-page proposal, problem statement, and project timeline were completed and approved.

---

## Week 2 — System Design and Technical Research

Week 2 focused on answering how the system will be built: comparing technology options at every layer, locking in a final stack, and producing the design artifacts that guide the MVP build in Week 3. No application code was written in this phase, by design.

### Planned System Architecture

![System Architecture](docs/diagrams/architecture.png)

The system is a three-tier web application. A React (Vite) single-page frontend communicates with a Django REST Framework backend hosted on AWS EC2, which persists data to PostgreSQL on Amazon RDS. The backend is the single trusted component: it performs authoritative input validation, stores data, constructs AI prompts, and calls the external AI provider — the frontend never touches the AI API or its key. AWS IAM enforces least-privilege access for the EC2 instance, Amazon CloudWatch collects logs and monitoring events, and Amazon S3 is reserved for future resume uploads and static assets. Secrets (database credentials, AI API key, Django `SECRET_KEY`) are managed through environment variables and never committed to the repository.

Full diagram and component responsibilities: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

### Final Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | Django REST Framework |
| Database | PostgreSQL (Amazon RDS) |
| Cloud | AWS EC2 + Amazon RDS |
| Storage | Amazon S3 (future resume uploads / static assets) |
| Monitoring | Amazon CloudWatch |
| Security | AWS IAM, environment variables, server-side validation, authentication planning |
| AI Layer | API-based provider (OpenAI / Gemini / Anthropic — TBD, pending cost review and mentor approval) |

### Why Each Technology Was Selected

**React + Vite** — the application is form-heavy and stateful (profiles, skill lists, recommendation history), which suits component-based state management; Vite gives a fast development loop and a clean static build. **Django REST Framework** — provides the ORM, migrations, serializers, authentication, and security defaults this project needs out of the box, reducing integration risk within a six-week timeline. **PostgreSQL on RDS** — the data model is relational (users → profiles → skills → recommendations), and RDS adds managed-database cloud experience. **EC2 + RDS** — chosen over Elastic Beanstalk, App Runner, and Amplify because manual Linux provisioning, security groups, and environment configuration are exactly the cloud engineering skills this internship targets. **AI provider TBD** — the backend uses a provider-agnostic service layer so the final provider decision (based on cost and mentor approval) does not block MVP progress; a rule-based stub can serve for early testing.

Full comparison tables: [`docs/TECHNOLOGY_COMPARISON.md`](docs/TECHNOLOGY_COMPARISON.md)

### AWS Deployment Plan

1. Provision a free-tier-eligible EC2 instance (Ubuntu), hardened with security groups allowing only HTTPS/SSH.
2. Provision PostgreSQL on Amazon RDS, network-restricted so only the EC2 security group can connect.
3. Deploy the Django application behind Gunicorn and Nginx, with secrets injected via environment variables.
4. Serve the React production build (initially from the same instance; S3/CloudFront is a documented future option).
5. Attach an IAM role to the EC2 instance granting least-privilege access (CloudWatch; S3 later).
6. Ship application logs and error events to CloudWatch; enable billing alerts to stay within free-tier limits.

### Data Flow Summary

![Data Flow Sequence Diagram](docs/diagrams/data_flow.png)

The student fills in profile, skills, and resume/career-goal text → the frontend performs basic validation and sends JSON to the backend → the backend re-validates and sanitizes all input, stores it in PostgreSQL, builds a structured prompt, and calls the external AI API → the AI response (career advice, skill-gap analysis, project ideas, or a learning plan) is stored as recommendation history and returned to the frontend for display → CloudWatch records logs and monitoring events throughout.

Full sequence diagram and step-by-step description: [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md)

### Security Considerations (Design Phase)

- All input is re-validated server-side (DRF serializers); client-side validation is UX only.
- AI API key, database credentials, and `SECRET_KEY` exist only in server environment variables.
- Database access is restricted at the network level to the EC2 security group; all queries go through the ORM.
- The EC2 instance uses an IAM role — no long-lived access keys on the server.
- AI output is rendered as plain text to prevent injection through the recommendation channel.
- Resume text is treated as sensitive personal data; the amount forwarded to the AI provider is minimized and will be reviewed explicitly in Week 5.

### Week 2 Deliverables Completed

- [x] Architecture diagram (rendered PNG/SVG + Mermaid source) — `docs/ARCHITECTURE.md`, `docs/diagrams/`
- [x] Technology comparison table — `docs/TECHNOLOGY_COMPARISON.md`
- [x] Final technology stack decision — `docs/WEEK2_SYSTEM_DESIGN.md`
- [x] Data flow diagram (rendered PNG/SVG + Mermaid source) — `docs/DATA_FLOW.md`, `docs/diagrams/`
- [x] Updated README explaining the planned system design (this section)

### Repository Documentation

```
docs/
├── WEEK2_SYSTEM_DESIGN.md      Main design document, final stack decision, risks
├── ARCHITECTURE.md             Architecture diagram + component responsibilities
├── TECHNOLOGY_COMPARISON.md    Full option comparison tables
├── DATA_FLOW.md                Data flow sequence diagram + data sensitivity
└── diagrams/
    ├── architecture.png / .svg
    └── data_flow.png / .svg
```

### Next Step — Week 3: MVP Development

Build the first working version: profile form, skills input, resume/career-goal input, a working backend API endpoint with database persistence, and a basic frontend — committed incrementally to GitHub with a weekly report.

## Week 3 Status: Minimum Viable Product Build

Week 3 delivered a working local MVP: a Django REST API backend with real
data persistence, a React frontend with working forms, and a full
frontend-backend integration — all running locally against SQLite.

### Deliverables Completed

- [x] **Backend foundation** — Django + Django REST Framework project
  (`backend/`), configured with `django-cors-headers` and SQLite for local
  development
- [x] **Health-check API** — `GET /api/health/` confirms the backend is
  reachable
- [x] **Models and API endpoints** — `StudentProfile`, `Skill`,
  `CareerInput`, and `Recommendation` models, with serializers,
  `ModelViewSet`-based CRUD endpoints (`/api/profiles/`, `/api/skills/`,
  `/api/career-inputs/`, `/api/recommendations/`), and Django admin
  registration
- [x] **React frontend** — created with Vite (`frontend/`), homepage
  explaining the project, purpose, and user workflow
- [x] **Frontend forms** — `ProfileForm`, `SkillsForm`, `CareerInputForm`,
  and a live `SummaryPreview`, using the same field names and choice
  values as the backend models
- [x] **Frontend-backend integration** — forms submit directly to the
  Django API with loading, success, and error states; the app loads
  existing profiles from the backend on page load and tracks a simple MVP
  workflow status (profile created / skills added / career input
  submitted)
- [x] **Local MVP works end to end** — a student can create a profile, add
  skills, and submit resume/career-goal input, all persisted to the local
  database and verifiable via the Django REST API
- [x] **Testing, cleanup, and documentation** — manual end-to-end test
  pass, small code cleanup, and finalized documentation across the root,
  backend, and frontend READMEs plus `docs/WEEK3_MVP_BUILD.md`

### Repository Documentation

See `backend/README.md` and `frontend/README.md` for setup and run
instructions for each half of the app, and `docs/WEEK3_MVP_BUILD.md` for
the full Week 3 summary, testing checklist, and weekly report.

### Next Step — Week 4: AI Integration and AWS Deployment

Integrate an API-based AI provider to generate real recommendations
(skill gap analysis, career path suggestions, project ideas, learning
plans) from a student's profile, skills, and career inputs, and begin AWS
deployment — moving from SQLite to PostgreSQL/Amazon RDS and deploying the
backend and frontend per the plan in `docs/WEEK2_SYSTEM_DESIGN.md`.

## Week 4 Status: AI Feature and Deployment Preparation

Week 4 moves the project from "a working local MVP" to "an application that
produces AI-assisted recommendations and is configured to be deployed." Days 1
to 3 are complete; deploying to EC2 is next.

### Day 1 — AWS account prepared safely

Before provisioning anything, the AWS account was secured: **MFA enabled** on
the root account, a **budget alert** created so spending cannot escalate
unnoticed, the available **AWS credit** checked, and a named **AWS CLI profile**
configured for local use. No billable resources were created.

### Day 2 — Environment variables and the first AI feature

- **Environment-driven configuration.** Added `python-decouple`, and moved
  `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and the AI
  provider settings into environment variables. `backend/.env.example`
  documents every variable with placeholders; the real `.env` is git-ignored and
  never committed. With `DEBUG=False` and no `SECRET_KEY`, Django now refuses to
  start rather than falling back to a public default.
- **Backend AI service layer.** `backend/career/services/ai_service.py` is the
  single place in the project allowed to talk to an AI provider. It is
  provider-agnostic, so swapping OpenAI / Gemini / Anthropic later touches one
  file.
- **Skill Gap Analysis added locally.** `POST /api/profiles/<id>/generate-skill-gap/`
  gathers a student's skills and career inputs, generates an analysis (career
  readiness summary, strengths, missing technical skills, missing professional
  skills, suggested projects, a 4-week learning plan, and limitations), saves it
  as a `Recommendation`, and returns it. Skill gap analysis was chosen first
  because it answers the exact question in the problem statement and needs no
  new data models.
- **Safe local fallback.** With `AI_PROVIDER=mock` the backend produces the
  analysis locally with no external call — the feature is fully demonstrable
  offline, at zero cost, with no student data leaving the machine. The API
  reports `used_fallback: true` so the mode is never ambiguous.
- **Frontend requests AI recommendations through the backend.** A new
  `AIRecommendationPanel.jsx` adds a "Generate Skill Gap Analysis" button with
  loading and error states. The frontend calls **only** the Django API — it holds
  no AI key and never contacts an AI provider, because anything in a React
  bundle is public the moment the page loads.
- **Tested.** 12 automated tests cover the health endpoint, the Week 3 CRUD
  endpoints, the new endpoint, the 404 case, the empty-profile case, and the AI
  service's fallback behaviour. All Week 3 features still work.

### Day 3 — Private Amazon RDS PostgreSQL prepared

- **A custom VPC with a public application tier and a private database tier.**
  The EC2 application subnets are public; the database subnets are private,
  spread across two Availability Zones (required for an RDS subnet group, and a
  prerequisite for Multi-AZ failover later).
- **The RDS PostgreSQL instance is private.** Public accessibility is disabled
  and it sits only in the private subnets, which have no route to the Internet
  Gateway — there is no path from the internet to the database, not merely a
  blocked one.
- **The RDS security group accepts PostgreSQL (TCP 5432) only from the EC2
  application security group.** Access is granted by security-group identity
  rather than by IP range, so only instances that join the application group can
  reach the database, whatever their address. A consequence worth stating plainly:
  the RDS endpoint **cannot** be reached from a local laptop, and that is the
  design working, not a fault to debug.
- **PostgreSQL environment-variable support added to Django.** `psycopg[binary]`
  was added, and `DB_HOST` now acts as a single switch: empty means the local
  SQLite file (unchanged local workflow), set means PostgreSQL on RDS using
  `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` (default `5432`), and
  `DB_SSLMODE` (default `require`). No endpoint, username, password, or database
  name is hard-coded anywhere. If `DB_HOST` is set but a credential is missing,
  Django refuses to start instead of silently falling back to SQLite.
- **A `python manage.py check_database` diagnostic command** reports the
  configured engine and runs `SELECT 1`. It never prints the database password,
  masks the host by default, and gives a readable failure message — it will be
  the first command run on EC2 to tell a configuration problem apart from a
  network one.
- **Tested without touching AWS.** 26 automated tests now cover the database
  selection rule and the diagnostic command alongside the existing AI feature —
  none of them require a database server, an RDS instance, or network access.
  Nothing was deployed and no connection to RDS was attempted.

Full write-up, network diagram, request-flow diagram, and testing checklist:
[`docs/WEEK4_AI_AND_DEPLOYMENT.md`](docs/WEEK4_AI_AND_DEPLOYMENT.md)

### Next Step — Day 4: Database migration to RDS and EC2 deployment

Launch and harden the EC2 instance in the application subnet, set the
environment variables on the server, and — **from inside the VPC, the only place
the database is reachable from** — run `check_database` and then
`python manage.py migrate` to create the schema on RDS. After that: Gunicorn and
Nginx in front of Django, the React production build served, a least-privilege
IAM role attached, and logs shipped to CloudWatch. Connecting a real, paid AI
provider comes last, after a spending cap and rate limiting are in place.
