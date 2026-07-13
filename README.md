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
