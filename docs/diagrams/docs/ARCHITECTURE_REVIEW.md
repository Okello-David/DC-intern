# Architecture Design Review — Findings and Corrections

**Project:** AI-Powered Student Career and Internship Assistant
**Review type:** Internal design review of the target AWS architecture, prior to Week 3 build
**Outcome:** Architecture approved with corrections; all findings resolved in `docs/ARCHITECTURE.md` (v3)

## Purpose

Before starting the MVP build, the target AWS architecture was subjected to a structured review covering networking correctness, subnet placement, public/private access, security-group logic, secret management, IAM usage, observability, cost realism, and presentation clarity. This document records what the review found and how each finding was resolved — the same discipline used in professional architecture reviews.

## Findings and Resolutions

**Finding 1 — Missing NAT path in the simplified diagram (error, fixed).**
The presentation version of the diagram placed the backend in a private subnet but drew a direct arrow from EC2 to the external AI provider. A private-subnet instance has no route to the internet, so the flow as drawn was impossible. *Resolution:* the NAT Gateway was restored to all diagram versions as the explicit outbound path (steps 6–7 in the request flow). Lesson recorded: a simplified diagram may omit detail, but must never contradict the network model it claims.

**Finding 2 — Single Availability Zone presented as the design (inaccuracy, fixed).**
An Application Load Balancer requires subnets in at least two AZs, and an RDS DB subnet group requires two AZs even for a single-AZ database instance. The diagrams showed one subnet per tier without qualification. *Resolution:* all subnet tiers are now annotated "×2 AZs" on the diagrams and explained in `ARCHITECTURE.md` Section 3.

**Finding 3 — Secrets Manager recommended without a cost check (judgment issue, fixed).**
AWS Secrets Manager costs $0.40 per secret per month plus API charges; SSM Parameter Store's standard tier is free and fully sufficient for this project's three secrets (database credentials, AI API key, Django `SECRET_KEY`). *Resolution:* SSM Parameter Store (SecureString) is now the selected secrets store; Secrets Manager is documented as a future improvement for when automatic rotation is required.

**Finding 4 — Implied connectivity to regional services (clarity issue, fixed).**
Arrows from the private-subnet backend to SSM and CloudWatch did not state how that traffic leaves the subnet. *Resolution:* these paths are now annotated "via NAT or VPC endpoints," and VPC endpoints are listed as a future improvement that removes the NAT dependency for AWS-service traffic.

**Finding 5 — IAM control-plane arrows mixed with data-plane traffic (clarity issue, fixed).**
Multiple dotted IAM arrows could be misread as network paths. *Resolution:* IAM is now shown with a single control-plane edge to the EC2 instance labeled "instance role."

## Review Conclusions on Scope and Cost

The review confirmed the phased deployment approach as the correct call for a six-week internship:

- **Phase 1 (deploy now):** single public-subnet EC2 (SSH restricted, HTTPS via Nginx) + RDS in private subnets with security-group-restricted access + SSM Parameter Store + CloudWatch. Preserves every security principle at minimal cost.
- **Phase 2 (documented target):** ALB (~$16–20/month) + private app subnets + NAT Gateway (~$32/month + per-GB) + CloudFront/S3 frontend. Deferred deliberately — attempting full Phase 2 during Week 4 would risk spending the week on VPC routing instead of the AI feature, which is the actual Week 4 deliverable.

**Remaining future improvements (not deployed, documented):** VPC endpoints, Secrets Manager with rotation, Multi-AZ RDS, AWS WAF on the ALB.

## Verdict

Architecture sound; one networking error corrected; cost posture corrected to fit an internship budget; presentation-ready with the local-MVP, slide, and detailed-target diagram set. Approved to proceed to Week 3 MVP build.
