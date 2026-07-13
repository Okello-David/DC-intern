# Week 2 — System Design and Technical Research

**Project:** AI-Powered Student Career and Internship Assistant
**Phase:** Week 2 of 6 — System Design and Technical Research
**Status:** Complete (design only — no application code built in this phase, by plan)

## 1. Objective of Week 2

Week 1 established the problem, target users, proposed features, and initial direction. The objective of Week 2 was to answer one question: *how, technically, should this system be built?* That required comparing realistic technology options at every layer, selecting a final stack with written justification, and producing the design artifacts (architecture diagram, data flow diagram) that Weeks 3–6 will implement against.

A deliberate constraint throughout was realistic scoping. The design avoids components the project does not need (orchestration, load balancing, microservices) so that the six-week timeline stays achievable and every included technology can be genuinely learned rather than superficially wired together.

## 2. Design Summary

The system is a three-tier web application:

- A **React + Vite** single-page frontend handling forms, validation feedback, and result display.
- A **Django REST Framework** backend on **AWS EC2** acting as the single trusted component: authentication, authoritative input validation, persistence, AI prompt construction, and provider calls.
- A **PostgreSQL** database on **Amazon RDS** storing users, profiles, skills, resume/career-goal text, and recommendation history.

Supporting services: **Amazon S3** (reserved for future resume uploads and static assets), **AWS IAM** (least-privilege roles for the EC2 instance), **Amazon CloudWatch** (logs and monitoring), and environment-variable-based secrets management. The external AI provider is called only from the backend through a provider-agnostic service layer.

Full diagrams: `docs/ARCHITECTURE.md` and `docs/DATA_FLOW.md`.
Full option analysis: `docs/TECHNOLOGY_COMPARISON.md`.

## 3. Final Technology Stack Decision

After comparing three frontend options, three backend options, three database options, four AWS deployment approaches, and four AI integration approaches (see `docs/TECHNOLOGY_COMPARISON.md`), the following stack is adopted for the remainder of the internship.

### 3.1 Frontend — React with Vite

React was selected because the application is form-heavy and stateful: profile editing, skill lists, and recommendation history all benefit from component-based state management. Vite provides a fast development loop and produces an optimized static build that can be served simply now and moved to S3/CloudFront later without rework. Plain HTML/CSS/JavaScript was rejected because maintaining dynamic result rendering without a framework would consume MVP time in Weeks 3–4, and Next.js was rejected because its server-rendering capabilities solve problems this project does not have while complicating the AWS deployment plan.

### 3.2 Backend — Django REST Framework

Django REST Framework was selected because the project's core backend requirements — user accounts, authentication, relational data modeling, and strict input validation — are exactly what DRF provides out of the box through its ORM, serializers, and authentication classes. Django's mature security defaults (ORM-parameterized queries, password hashing, CSRF protection) directly support the Week 5 security review. FastAPI is an excellent framework but would require assembling the ORM, migrations, admin, and auth from separate libraries, adding integration risk to a six-week timeline. Node.js/Express was rejected primarily on structure and skill-path grounds: Python is the stronger established backend language for this internship, and Express provides little built-in structure for a data-validation-heavy application.

### 3.3 Database — PostgreSQL on Amazon RDS

The data model is clearly relational: users own profiles, profiles contain skills, and recommendations reference both. PostgreSQL handles this naturally, has first-class Django support, and is available as a managed service through Amazon RDS — which itself teaches core cloud engineering skills (parameter groups, security groups, backups, restricted network access). SQLite is permitted only for the first local development runs before RDS is provisioned. Document databases were rejected because the data is not document-shaped and Firebase in particular would pull the project away from its AWS learning objective.

### 3.4 Cloud — AWS EC2 + Amazon RDS

AWS was confirmed as the cloud platform, and EC2 + RDS as the deployment model, because this combination provides the most direct cloud engineering practice available within the project scope: provisioning and hardening a Linux instance, configuring security groups, managing environment variables, running the application behind a production server (Gunicorn/Nginx), and connecting to a managed database over a restricted network path. Elastic Beanstalk and App Runner automate precisely the steps this internship is meant to teach, and Amplify addresses only frontend hosting. Beyond the immediate deployment, AWS supports the project's full trajectory: S3 for future resume uploads and static assets, IAM for least-privilege access control, and CloudWatch for logging and monitoring — and it carries strong portfolio value for cloud engineering and backend roles.

### 3.5 Storage — Amazon S3 (future phase)

S3 is designated for resume file uploads (via backend-generated pre-signed URLs) and potentially for hosting the frontend static build. It is intentionally excluded from the MVP: Week 3 uses pasted resume text only, which keeps file-handling risks (type validation, size limits, malware considerations) out of scope until the core flow works.

### 3.6 Monitoring — Amazon CloudWatch

CloudWatch is adopted for application logs, error events, and basic metrics. Beyond operational visibility, it provides the audit trail required by the Week 5 security review and demonstrates monitoring practice for the final report.

### 3.7 Security — IAM, environment variables, validation, authentication planning

Security decisions locked in at design time: the EC2 instance runs under an IAM role granting only CloudWatch (and later S3) access, with no long-lived keys on the server; all secrets (database credentials, AI API key, Django `SECRET_KEY`) live in environment variables and never in the repository; every input is re-validated server-side through DRF serializers regardless of client-side checks; and authentication uses Django's built-in user model with hashed passwords, with session or token authentication finalized at MVP build time. AI output is rendered as plain text to prevent injection through the recommendation channel.

### 3.8 AI Layer — API-based provider (TBD), behind an abstraction

The AI feature will use an external API provider — OpenAI, Google Gemini, or Anthropic — with the final choice **TBD pending cost analysis, free-tier availability, and mentor approval**. To prevent this open decision from blocking progress, the backend will expose a single provider-agnostic `recommendation_service` interface. Week 3 may ship with a simple rule-based stub behind this interface for testing; Week 4 swaps in the approved provider without changes elsewhere in the codebase. Prompt templates, required inputs, expected outputs, and documented limitations will be produced in Week 4 per the roadmap.

## 4. Risks Identified During Design

| Risk | Mitigation planned |
|---|---|
| AI provider cost or quota limits | Provider-agnostic service layer; rule-based fallback; decision deferred to Week 4 with mentor input |
| AWS free-tier limits (EC2/RDS) | Use free-tier-eligible instance classes; stop instances outside working sessions; monitor billing alerts |
| Resume text is sensitive personal data | Minimum-necessary fields sent to the AI provider; explicit privacy treatment in Week 5 review |
| Single EC2 instance is a single point of failure | Accepted consciously for scope; documented as a known limitation in the final report |
| Timeline pressure in Weeks 3–4 | Batteries-included stack (DRF) chosen specifically to reduce integration work |

## 5. Week 2 Deliverables Checklist

- [x] Architecture diagram (`docs/ARCHITECTURE.md`)
- [x] Technology comparison table (`docs/TECHNOLOGY_COMPARISON.md`)
- [x] Final technology stack decision (this document, Section 3)
- [x] Data flow diagram (`docs/DATA_FLOW.md`)
- [x] Updated README with planned system design (Week 2 section)

## 6. Next Step — Week 3

Week 3 begins MVP development: user profile form, skills input, resume/career-goal input, working backend API endpoint, database persistence, and a basic frontend — with GitHub commits showing incremental progress and a weekly report covering what was built, what failed, what was learned, and where guidance is needed.
