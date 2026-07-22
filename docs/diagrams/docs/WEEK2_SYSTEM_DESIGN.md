# Week 2 — System Design and Technical Research

**Project:** AI-Powered Student Career and Internship Assistant
**Phase:** Week 2 of 6 — System Design and Technical Research
**Status:** Complete, including post-review corrections (see `docs/ARCHITECTURE_REVIEW.md`)

## 1. Objective of Week 2

Week 1 established the problem, target users, proposed features, and initial direction. The objective of Week 2 was to answer one question: *how, technically, should this system be built?* That required comparing realistic technology options at every layer, selecting a final stack with written justification, producing the design artifacts (architecture diagrams, data flow diagram) that Weeks 3–6 will implement against, and subjecting the design to a structured review before build begins.

A deliberate constraint throughout was realistic scoping: the design distinguishes between what is deployed during the internship (Phase 1) and the documented production target (Phase 2), so that the six-week timeline stays achievable and every deployed technology can be genuinely learned rather than superficially wired together.

## 2. Design Summary

The system is a three-tier web application:

- A **React + Vite** single-page frontend handling forms, validation feedback, and result display.
- A **Django REST Framework** backend on **AWS EC2** acting as the single trusted component: authentication, authoritative input validation, persistence, AI prompt construction, and provider calls.
- A **PostgreSQL** database on **Amazon RDS** storing users, profiles, skills, resume/career-goal text, and recommendation history.

Supporting services: **Amazon S3** (frontend hosting in Phase 2; resume uploads later), **AWS IAM** (least-privilege instance roles), **Amazon CloudWatch** (logs, metrics, billing alarms), and **SSM Parameter Store** for secrets. The external AI provider is called only from the backend through a provider-agnostic service layer; the current local MVP runs a rule-based stub behind that interface.

Full diagrams: `docs/ARCHITECTURE.md` and `docs/DATA_FLOW.md`.
Full option analysis: `docs/TECHNOLOGY_COMPARISON.md`.
Design review findings: `docs/ARCHITECTURE_REVIEW.md`.

## 3. Final Technology Stack Decision

### 3.1 Frontend — React with Vite

React was selected because the application is form-heavy and stateful: profile editing, skill lists, and recommendation history all benefit from component-based state management. Vite provides a fast development loop and produces an optimized static build that can be served simply now and moved to S3/CloudFront in Phase 2 without rework. Plain HTML/CSS/JavaScript was rejected because maintaining dynamic result rendering without a framework would consume MVP time in Weeks 3–4, and Next.js was rejected because its server-rendering capabilities solve problems this project does not have while complicating the AWS deployment plan.

### 3.2 Backend — Django REST Framework

Django REST Framework was selected because the project's core backend requirements — user accounts, authentication, relational data modeling, and strict input validation — are exactly what DRF provides out of the box through its ORM, serializers, and authentication classes. Django's mature security defaults (ORM-parameterized queries, password hashing, CSRF protection) directly support the Week 5 security review. FastAPI is an excellent framework but would require assembling the ORM, migrations, admin, and auth from separate libraries, adding integration risk to a six-week timeline. Node.js/Express was rejected primarily on structure and skill-path grounds: Python is the stronger established backend language for this internship, and Express provides little built-in structure for a data-validation-heavy application.

### 3.3 Database — PostgreSQL on Amazon RDS

The data model is clearly relational: users own profiles, profiles contain skills, and recommendations reference both. PostgreSQL handles this naturally, has first-class Django support, and is available as a managed service through Amazon RDS — which itself teaches core cloud engineering skills (subnet groups, security groups, backups, restricted network access). SQLite is used only in the current local MVP before RDS is provisioned. Document databases were rejected because the data is not document-shaped and Firebase in particular would pull the project away from its AWS learning objective.

### 3.4 Cloud — AWS, deployed in two phases

AWS was confirmed as the cloud platform because it provides the most direct cloud engineering practice available within the project scope and carries strong portfolio value. The deployment is phased following the design review:

- **Phase 1 (Weeks 3–4, deployed):** a single EC2 instance in a public subnet (SSH restricted to a known IP, HTTPS via Nginx) with RDS PostgreSQL in private subnets, reachable only from the instance's security group. This preserves the core security principles at near-zero cost and keeps Week 4 focused on its actual deliverable — the AI feature.
- **Phase 2 (documented target):** Application Load Balancer in public subnets, backend in private application subnets with no public IP, NAT Gateway for outbound traffic, and the React build served from S3 through CloudFront. All subnet tiers span two Availability Zones.

Elastic Beanstalk and App Runner automate precisely the steps this internship is meant to teach, and Amplify addresses only frontend hosting; all three were rejected as the primary approach.

### 3.5 Storage — Amazon S3 (Phase 2 and later)

S3 is designated for hosting the frontend static build behind CloudFront (Phase 2) and for resume file uploads via backend-generated pre-signed URLs (later phase). It is intentionally excluded from the MVP: the MVP uses pasted resume text only, which keeps file-handling risks out of scope until the core flow works.

### 3.6 Monitoring — Amazon CloudWatch

CloudWatch is adopted for application logs, error events, basic metrics, and billing alarms. Beyond operational visibility, it provides the audit trail required by the Week 5 security review and demonstrates monitoring practice for the final report.

### 3.7 Secrets and Security — SSM Parameter Store, IAM, layered security groups

Following the design review's cost analysis, **SSM Parameter Store** (free standard tier, SecureString parameters) is the selected secrets store for database credentials, the AI API key, and the Django `SECRET_KEY`; AWS Secrets Manager ($0.40/secret/month) is documented as a future upgrade for automatic rotation. The EC2 instance runs under an IAM role granting least-privilege access to its parameters, CloudWatch, and (later) scoped S3 — no long-lived keys on the server. Security groups are layered so each tier accepts traffic only from the tier in front of it. Every input is re-validated server-side through DRF serializers, and AI output is rendered as plain text.

### 3.8 AI Layer — API-based provider (TBD), behind an abstraction

The AI feature will use an external API provider — OpenAI, Google Gemini, or Anthropic — with the final choice **TBD pending cost analysis, free-tier availability, and mentor approval**. The backend exposes a single provider-agnostic `recommendation_service` interface; the current local MVP runs a rule-based stub behind it, and Week 4 swaps in the approved provider without changes elsewhere in the codebase. Prompt templates, required inputs, expected outputs, and documented limitations will be produced in Week 4 per the roadmap.

## 4. Risks Identified During Design

| Risk | Mitigation planned |
|---|---|
| AI provider cost or quota limits | Provider-agnostic service layer; rule-based fallback; decision deferred to Week 4 with mentor input |
| AWS free-tier limits (EC2/RDS) | Phase 1 layout with free-tier-eligible instance classes; billing alarms in CloudWatch; ALB/NAT deferred to Phase 2 |
| Resume text is sensitive personal data | Minimum-necessary fields sent to the AI provider; explicit privacy treatment in Week 5 review |
| Single EC2 instance is a single point of failure | Accepted consciously for scope; Phase 2 and Multi-AZ documented as future work |
| Timeline pressure in Weeks 3–4 | Batteries-included stack (DRF) chosen specifically to reduce integration work; deployment complexity phased |

## 5. Week 2 Deliverables Checklist

- [x] Architecture diagrams — local MVP, presentation version, detailed target (`docs/ARCHITECTURE.md`, `docs/diagrams/`)
- [x] Technology comparison table (`docs/TECHNOLOGY_COMPARISON.md`)
- [x] Final technology stack decision (this document, Section 3)
- [x] Data flow diagram (`docs/DATA_FLOW.md`)
- [x] Updated README with planned system design (Week 2 section)
- [x] Architecture design review with findings resolved (`docs/ARCHITECTURE_REVIEW.md`)

## 6. Next Step — Week 3

Week 3 begins MVP development: user profile form, skills input, resume/career-goal input, working backend API endpoint, database persistence, and a basic frontend — with GitHub commits showing incremental progress and a weekly report covering what was built, what failed, what was learned, and where guidance is needed.
