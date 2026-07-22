# Technology Comparison — Week 2 Technical Research

**Document status:** Week 2 deliverable — System Design and Technical Research
**Purpose:** Compare candidate technologies for each layer of the AI-Powered Student Career and Internship Assistant and justify the final selection. The evaluation criteria are: strengths, weaknesses, suitability for this specific project, and learning value for a cloud-engineering-focused internship.

## 1. Frontend

| Option | Strengths | Weaknesses | Suitability for This Project | Learning Value | Recommendation |
|---|---|---|---|---|---|
| **React + Vite** | Component-based UI, fast dev server and builds, huge ecosystem, industry-standard skill, clean separation from backend API | Requires a build step; more initial setup than plain HTML | High — the app is form-heavy and stateful (profile, skills, results history), which suits components and client-side state | High — React is the most requested frontend skill in internship/job postings | ✅ **Selected** |
| Plain HTML/CSS/JavaScript | Zero tooling, simplest possible start, easy to serve from Django templates | State management and dynamic result rendering become messy quickly; hard to maintain past a trivial size; weak portfolio signal | Low–medium — workable for a demo but would slow down Weeks 3–4 as features grow | Low — does not demonstrate modern frontend practice | ❌ Rejected |
| Next.js | SSR/SSG, file-based routing, production-grade framework | Server-rendering features are unnecessary here; adds deployment complexity that conflicts with the AWS plan; steeper learning curve on top of React | Low — solves problems this project does not have | Medium — valuable skill, but overkill for a 6-week SPA | ❌ Rejected |

## 2. Backend

| Option | Strengths | Weaknesses | Suitability for This Project | Learning Value | Recommendation |
|---|---|---|---|---|---|
| **Django REST Framework** | Batteries included: ORM, migrations, admin panel, authentication, serializers with built-in validation; mature security defaults (CSRF, SQL-injection protection via ORM, password hashing) | Heavier than micro-frameworks; some boilerplate | High — the project needs users, auth, relational data, and strict input validation, all of which DRF provides out of the box; the admin panel accelerates debugging during the MVP week | High — Django + DRF is widely used and pairs naturally with PostgreSQL and the intern's existing Python/Django experience | ✅ **Selected** |
| FastAPI | Modern async support, automatic OpenAPI docs, excellent performance, lightweight | No built-in ORM, auth, or admin — each must be assembled (SQLAlchemy, Alembic, auth libraries), increasing integration risk within the timeline | Medium — technically capable, but assembling the pieces consumes MVP time | High — but better suited to a project where async I/O is the core requirement | ❌ Rejected for this project |
| Node.js + Express | Same language as frontend, large ecosystem, flexible | Minimal structure; validation, ORM, and auth are all separate decisions; the intern's stronger backend language is Python | Medium | Medium — valuable, but splits focus away from the established Python skill path | ❌ Rejected |

## 3. Database

| Option | Strengths | Weaknesses | Suitability for This Project | Learning Value | Recommendation |
|---|---|---|---|---|---|
| **PostgreSQL** | Robust relational integrity, first-class Django support, available as managed Amazon RDS, handles structured profile/skills/history data naturally | Requires running a server (solved by RDS); slightly more setup than SQLite | High — the data model (users → profiles → skills → recommendations) is clearly relational | High — PostgreSQL + RDS is a standard production pairing and core cloud-engineering experience | ✅ **Selected** |
| SQLite | Zero configuration, file-based, perfect for the first days of local development | Not suitable for a deployed multi-user app; no managed cloud offering; weak concurrency | Low for production; used only as the local development database in the current MVP before RDS is provisioned | Low | ❌ Rejected for deployment (in use for local MVP only) |
| MongoDB / Firebase | Flexible schema, fast prototyping; Firebase adds auth and hosting | The data is relational, not document-shaped; Firebase locks the project into Google's ecosystem and away from the AWS learning goal; weaker fit with Django ORM | Low | Medium — but misaligned with both the data model and the AWS objective | ❌ Rejected |

## 4. AWS Deployment

| Option | Strengths | Weaknesses | Suitability for This Project | Learning Value | Recommendation |
|---|---|---|---|---|---|
| **EC2 + RDS** | Full control of the Linux server; hands-on experience with SSH, security groups, environment configuration, service setup (Gunicorn/Nginx), and managed databases | More manual setup; the intern is responsible for hardening and updates | High — matches the internship's cloud engineering goal precisely: this option teaches what the abstractions hide | Very high — Linux administration, networking, and deployment are exactly the target skills | ✅ **Selected** (Phase 1 now; ALB + private subnets + NAT as the documented Phase 2 target) |
| AWS Amplify + backend API | Very fast frontend hosting with CI/CD from Git | Optimized for frontend + serverless patterns; a Django backend still needs separate hosting, so it only solves half the problem | Medium — could host the React build later, but does not remove the need for EC2 | Medium | ❌ Rejected as primary approach |
| Elastic Beanstalk | Automates provisioning, load balancing, and deployment of Django apps | Abstracts away the underlying configuration the internship is meant to teach; debugging the abstraction can be harder than doing the setup manually | Medium | Medium — good to know, but hides the learning | ❌ Rejected |
| App Runner | Simplest container-based deployment, scales to zero | Requires Docker knowledge as a prerequisite; less direct exposure to EC2/Linux fundamentals | Medium | Medium–high, but sequenced wrong — containers are a natural *next* step after manual deployment is understood | ❌ Rejected for this phase |

## 5. AI Integration

| Option | Strengths | Weaknesses | Suitability for This Project | Learning Value | Recommendation |
|---|---|---|---|---|---|
| OpenAI API | Mature API, strong documentation, widely used | Paid; requires billing setup; quota management | High | High | 🔶 Candidate — **final provider TBD** |
| Google Gemini API | Free tier available, competitive quality, simple REST interface | Free-tier rate limits; API surface changes relatively often | High — the free tier is attractive for a student budget | High | 🔶 Candidate — **final provider TBD** |
| Anthropic API | High-quality structured outputs, strong safety behavior | Paid; requires billing setup | High | High | 🔶 Candidate — **final provider TBD** |
| Simple rule-based logic | Free, fully offline, deterministic, excellent for early testing | Not real AI; limited usefulness; cannot generalize | In use as the current local MVP stub while the AI provider decision is finalized | Medium — teaches the value of a provider-agnostic service layer | ✅ In use as **temporary fallback**, not the final AI layer |

**AI decision approach:** the backend implements a single `recommendation_service` module with a provider-agnostic interface. The local MVP runs with the rule-based stub behind that interface; the final API provider (OpenAI, Gemini, or Anthropic) will be selected in Week 4 based on cost, free-tier availability, and mentor approval. This decouples the MVP timeline from the provider decision.

## 6. Summary of Decisions

| Layer | Decision |
|---|---|
| Frontend | React + Vite |
| Backend | Django REST Framework |
| Database | PostgreSQL (Amazon RDS in deployment; SQLite in the current local MVP only) |
| Cloud | AWS EC2 + Amazon RDS (Phase 1), ALB + private subnets + NAT Gateway (Phase 2 target) |
| Storage | Amazon S3 (frontend hosting in Phase 2; resume uploads later via pre-signed URLs) |
| Monitoring | Amazon CloudWatch |
| Secrets | SSM Parameter Store (free tier); Secrets Manager as a future upgrade for rotation |
| Security | AWS IAM instance roles, layered security groups, server-side validation, authentication planning |
| AI Layer | API-based provider behind an abstraction layer — provider TBD; rule-based stub in the current MVP |

The full justification is written in `docs/WEEK2_SYSTEM_DESIGN.md`, and the design review that finalized the secrets and phasing decisions is in `docs/ARCHITECTURE_REVIEW.md`.
