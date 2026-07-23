# Week 4 Day 4 — Backend Deployment Report

**Date:** 22 July 2026
**Status:** Deployed and verified, with two open items (see *Problems* and *Limitations*)
**Reviewed by:** closeout review against the running AWS environment, read-only

> **A note on identifiers.** This report is committed to a public repository, so
> AWS account number, instance ID, security group IDs, VPC/subnet IDs, the
> public IP, and the RDS endpoint are written as placeholders
> (`<account-id>`, `<instance-id>`, `<ec2-sg>`, `<rds-sg>`, `<public-ip>`).
> They are not secrets in the way a password is, but publishing them hands an
> attacker a free reconnaissance step. Substitute the real values from the AWS
> console when submitting the internship report as a private document.

---

## Day 4 Objective

Deploy the Django REST Framework backend to Amazon EC2 so it is reachable over
the public internet, connected to the private Amazon RDS PostgreSQL database,
and running as a managed service that survives crashes and reboots — without
exposing the database, the application server, or any credential.

---

## Architecture Implemented

```
                Internet
                   │  HTTP :80
                   ▼
 ┌──────────────── Custom VPC ─────────────────────────────────────────┐
 │                                                                     │
 │  Public application subnet (eu-north-1a)                            │
 │  ┌───────────────────────────────────────────────────────────────┐  │
 │  │ EC2  t3.micro, Amazon Linux 2023          SG: dc-intern-ec2-sg│  │
 │  │                                           inbound: TCP 80 only│  │
 │  │   Nginx 1.30.3   :80  public                                  │  │
 │  │     └─ proxy_pass ──► Gunicorn  127.0.0.1:8000  loopback only │  │
 │  │                          └─ Django 6.0.7 (config.wsgi)        │  │
 │  │   IAM instance profile: dc-intern-ec2-profile                 │  │
 │  │   Config + secrets: /etc/dc-intern/backend.env (0640)         │  │
 │  └───────────────────────────────────────────────────────────────┘  │
 │                            │ PostgreSQL 5432, sslmode=require       │
 │                            ▼                                        │
 │  Private DB subnets (eu-north-1a + eu-north-1b)                     │
 │  ┌───────────────────────────────────────────────────────────────┐  │
 │  │ RDS PostgreSQL 18.3  db.t4g.micro       SG: dc-intern-rds-sg  │  │
 │  │ PubliclyAccessible: false               inbound: 5432 from    │  │
 │  │ StorageEncrypted:   true (KMS)                   dc-intern-   │  │
 │  │ No route to the Internet Gateway                 ec2-sg only  │  │
 │  └───────────────────────────────────────────────────────────────┘  │
 └─────────────────────────────────────────────────────────────────────┘
```

---

## AWS Resources Used

| Resource | Identifier / value | Notes |
|---|---|---|
| Region | `eu-north-1` (Stockholm) | Single region |
| VPC | `<vpc-id>` | Custom, not the default VPC |
| Application subnet | `<subnet-id>`, eu-north-1a | Public |
| DB subnet group | `dc-intern-db-subnet-group` | Two AZs: eu-north-1a + 1b |
| EC2 instance | `<instance-id>`, `t3.micro` | Amazon Linux 2023, **running** |
| EC2 security group | `dc-intern-ec2-sg` | Inbound: TCP 80 from `0.0.0.0/0` — nothing else |
| IAM instance profile | `dc-intern-ec2-profile` → role `dc-intern-ec2-role` | `AmazonSSMManagedInstanceCore` + one scoped inline policy |
| RDS instance | `dc-intern-postgres`, `db.t4g.micro` | PostgreSQL 18.3, **available** |
| RDS security group | `dc-intern-rds-sg` | Inbound: TCP 5432 from `dc-intern-ec2-sg` only |
| Parameter Store | `/dc-intern/prod/db/{host,name,user,password}` | `password` stored as **SecureString** |
| Access | AWS Systems Manager Session Manager | No SSH, no key pair |

Cost profile: `t3.micro` + `db.t4g.micro` + 1-day backup retention — free-tier
shaped, single-AZ, no NAT Gateway.

---

## Request Path

```
Browser
  │  GET http://<public-ip>/api/health/
  ▼
Nginx  (public, port 80)
  │  • terminates the client connection
  │  • serves /static/ from /opt/dc-intern/backend/staticfiles/ directly
  │  • sets Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto
  │  • enforces client_max_body_size 5m and proxy timeouts
  ▼  proxy_pass http://127.0.0.1:8000
Gunicorn  (loopback only, 2 workers, systemd-managed)
  ▼  WSGI
Django  config.wsgi:application
  │  • validates Host against ALLOWED_HOSTS
  │  • routes through career/urls.py to a DRF viewset
  │  • reads config from the process environment (systemd EnvironmentFile)
  ▼  psycopg, sslmode=require, connect_timeout=10, CONN_MAX_AGE=60
Amazon RDS PostgreSQL  (private subnets, no internet route)
```

The response returns along the same path. Nothing in the browser ever holds a
database credential or an AI API key.

---

## Security Controls

Verified against the live environment with read-only AWS CLI calls.

| Control | Status | Evidence |
|---|---|---|
| Public SSH (22) closed | ✅ | EC2 SG has exactly one inbound rule: TCP 80 |
| Gunicorn (8000) not public | ✅ | Not in any SG rule; `curl http://<public-ip>:8000/` times out |
| PostgreSQL (5432) not public | ✅ | No SG in the VPC exposes 5432 to `0.0.0.0/0` |
| RDS not publicly accessible | ✅ | `PubliclyAccessible: false`, private subnets, no IGW route |
| RDS reachable only from the app tier | ✅ | RDS SG source is the **security group** `dc-intern-ec2-sg`, not a CIDR |
| RDS storage encrypted at rest | ✅ | `StorageEncrypted: true`, KMS key present |
| DB traffic encrypted in transit | ✅ | `DB_SSLMODE=require` |
| No long-lived keys on the instance | ✅ | IAM instance profile, no access keys |
| Least-privilege IAM | ✅ | Inline policy allows only `ssm:GetParameter(s)`/`GetParametersByPath` on `arn:aws:ssm:eu-north-1:<account-id>:parameter/dc-intern/prod/*` |
| DB password not stored in plaintext | ✅ | Parameter Store **SecureString** |
| No secret in the repository | ✅ | Only `.env.example` templates are tracked; every secret field is empty |
| Config outside the repo | ✅ | `/etc/dc-intern/backend.env`, `root:ec2-user`, mode `0640` |
| Security response headers | ✅ | Live response carries `X-Content-Type-Options: nosniff` and `Referrer-Policy: same-origin`, confirming the `DEBUG=False` block is active |
| Secrets absent from API responses and logs | ✅ | Code audit: no endpoint returns a key; the only log line naming `AI_API_KEY` reports its *absence*; `check_database` prints `Password: set (not shown)` |
| TLS on the public edge | ❌ | **Not yet** — see Limitations |

---

## Session Manager Usage

Administration uses **AWS Systems Manager Session Manager**, not SSH.

```bash
aws ssm start-session --target <instance-id> --profile dc-week4 --region eu-north-1
sudo su - ec2-user
```

Verified live: the SSM agent reports `PingStatus: Online`, agent `3.3.4624.0`,
platform Amazon Linux 2023.

Why this matters for the report:

- The security group needs **no inbound rule for port 22**, removing the most
  frequently attacked port on a public instance. This was confirmed: the only
  inbound rule is TCP 80.
- There is no key pair to distribute, lose, or accidentally commit — no `.pem`
  file exists for this project.
- Access is granted and revoked through **IAM**, per person, and every session
  is recorded in CloudTrail.
- The agent makes an *outbound* connection, so no inbound port is opened to
  provide the access.

---

## Database Migration Result

Migrations were applied to the private RDS instance from the EC2 instance,
inside the VPC — the only place the database is reachable from.

```bash
python manage.py check_database    # postgresql, SSL mode require, OK
python manage.py migrate           # applied to RDS
```

Verified from outside, without touching the database directly: all four
model-backed endpoints return `200` with valid JSON.

| Endpoint | Result |
|---|---|
| `/api/health/` | `200` `{"status": "ok", ...}` |
| `/api/profiles/` | `200` |
| `/api/skills/` | `200` |
| `/api/career-inputs/` | `200` |
| `/api/recommendations/` | `200` (0 rows) |

A missing table would raise `ProgrammingError` and return `500`, so four
successful list queries confirm the schema exists on RDS and Django is talking
to PostgreSQL rather than a stray local SQLite file.

---

## Deployment Verification Checklist

Performed during this closeout review, read-only.

| # | Check | Result |
|---|---|---|
| 1 | EC2 instance tagged `dc-intern-backend` exists | ✅ found |
| 2 | Instance state | ✅ `running` |
| 3 | IAM instance profile attached | ✅ `dc-intern-ec2-profile` |
| 4 | SSM agent online | ✅ `Online`, AL2023 |
| 5 | EC2 SG exposes public TCP 80 only | ✅ single rule |
| 6 | Public SSH 22 closed | ✅ absent |
| 7 | Gunicorn 8000 not public | ✅ connection times out from outside |
| 8 | PostgreSQL 5432 not public | ✅ no `0.0.0.0/0` rule in the VPC |
| 9 | `dc-intern-postgres` available | ✅ `available`, PostgreSQL 18.3 |
| 10 | RDS `PubliclyAccessible` | ✅ `false` |
| 11 | RDS storage encrypted | ✅ `true`, KMS |
| 12 | RDS SG source is the EC2 SG | ✅ security-group reference, no CIDR |
| 13 | Parameter Store password is SecureString | ✅ |
| 14 | IAM policy scoped to `/dc-intern/prod/*` | ✅ read-only actions only |
| 15 | Health endpoint via public IP | ✅ `200` |
| 16 | All four CRUD endpoints via public IP | ✅ `200` |
| 17 | Static files served by Nginx | ✅ `/static/admin/css/base.css` → `200` |
| 18 | Security headers present | ✅ nosniff + referrer-policy |
| 19 | Health endpoint via **public DNS name** | ❌ `400` — see Problems |
| 20 | Skill Gap Analysis exercised against RDS | ⚠️ not yet — 0 recommendation rows |
| 21 | Local test suite still passes | ✅ 26/26 |
| 22 | Local SQLite mode still works | ✅ unchanged |

---

## Problems Encountered and Solutions

### 1. `ALLOWED_HOSTS` accepts the public IP but not the public DNS name — **open**

`http://<public-ip>/api/health/` returns `200`, but the same request to the
instance's `ec2-…compute.amazonaws.com` DNS name returns **HTTP 400 Bad
Request**. That is Django's `DisallowedHost` response: the hostname in the
request is not listed in `ALLOWED_HOSTS`.

It is Django rejecting the request, not Nginx — Nginx forwarded it correctly.

**Fix** (on the instance, via Session Manager):

```bash
sudo nano /etc/dc-intern/backend.env
#   ALLOWED_HOSTS=<public-ip>,ec2-<...>.eu-north-1.compute.amazonaws.com
#   CSRF_TRUSTED_ORIGINS=http://ec2-<...>.eu-north-1.compute.amazonaws.com
sudo systemctl restart dc-intern-backend    # restart, not reload — systemd
                                            # re-reads EnvironmentFile only on start
```

### 2. The public IP is not an Elastic IP — **open, and it blocks Day 5**

`describe-addresses` returns no allocation for this instance, so the public
IPv4 address is ephemeral: **it changes every time the instance is stopped and
started.** Today that only means `ALLOWED_HOSTS` would need editing after a
restart. From Day 5 it is worse — the React frontend bakes its API base URL in
at build time, so an address change would silently break the deployed frontend
until it is rebuilt.

**Fix:** allocate and associate an Elastic IP (free while attached to a running
instance), and build the frontend against a stable address or DNS name.

### 3. Deploy script's default Python may not satisfy Django 6 — **fixed**

`deploy/scripts/deploy_backend.sh` defaults to `PYTHON_BIN=python3`. On Amazon
Linux 2023 `python3` is Python 3.9, but **Django 6.0.7 requires Python ≥ 3.12**
(confirmed from the package metadata). The deployment succeeded because
`python3.12` was installed and used, but a clean re-run of the script on a new
instance would build the virtualenv on 3.9 and fail at `pip install`.

**Fixed in this review.** `PYTHON_BIN` now defaults to `python3.12`, and a
`require_python` guard asserts the version — both for the interpreter used to
create the virtualenv and for a pre-existing virtualenv that an earlier run may
have built on 3.9. The script now stops with an actionable message naming the
version found and the `dnf install` command to run. Verified against a real
Python 3.10 interpreter, in both the "create" and "reuse" paths.

### 4. `.gitignore` does not cover `backend.env` — **fixed**

The ignore list contains `.env` and `.env.*.local`, which match a file named
exactly `.env`. It does **not** match `backend.env` — the actual production
filename referenced throughout the deployment docs. Copying
`/etc/dc-intern/backend.env` into the repository to edit it would leave it
untracked-but-offered, one `git add .` away from committing the database
password.

**Fixed in this review.** `*.env` added to `.gitignore`. Verified: `backend.env`,
`deploy/backend.env`, and `prod.env` are now ignored, while
`backend/.env.example` and `deploy/backend.env.example` remain tracked.

---

## Current Limitations

- **No TLS.** The site serves plain HTTP on port 80. Traffic between a browser
  and EC2 — including anything a student types into the forms — is unencrypted.
  `USE_HTTPS` is the single environment flag that turns on secure cookies,
  HTTPS redirect, and HSTS once a certificate exists. Until then, do not put
  real personal data through the deployment.
- **No authentication.** Every endpoint is open to the internet. Anyone who
  finds the address can create, read, and delete profiles, skills, and career
  inputs, and can trigger AI generation.
- **No rate limiting**, which becomes a cost risk the moment a paid AI provider
  is connected.
- **AI feature not yet exercised on the deployed stack** — 0 recommendation
  rows exist on RDS. The code is deployed and configured in `mock` mode, but
  the end-to-end path has not been demonstrated in the cloud.
- **Single instance, single AZ, no load balancer.** RDS is `MultiAZ: false`.
  Any instance failure is a full outage.
- **Backup retention is 1 day** and `DeletionProtection` is `false` on the RDS
  instance.
- **No CloudWatch log shipping.** Application logs live only in the instance's
  journal and are lost with the instance.
- **Ephemeral public IP** (see Problems #2).
- **Frontend is not deployed** — the React app still points at
  `http://127.0.0.1:8000/api` in `frontend/src/services/api.js`.

---

## Next Step — Day 5

1. Close the two remaining open items above, both of which need AWS changes:
   add the DNS name to `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, and allocate an
   Elastic IP. (Items 3 and 4 — the deploy script's Python version and the
   `.gitignore` gap — were fixed during this review.)
2. Exercise the Skill Gap Analysis feature against the deployed stack and
   confirm the recommendation persists to RDS.
3. Make the frontend API base URL a build-time variable instead of a hard-coded
   `127.0.0.1:8000`, and build against the deployed backend.
4. Deploy the frontend — from Nginx on the same instance, or S3 — and document
   the trade-off.
5. Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the frontend's real
   origin, restart, and verify the full user journey in the cloud.
6. Add TLS, then set `USE_HTTPS=True` and re-run `manage.py check --deploy` —
   the four expected warnings should disappear.
7. Ship logs to CloudWatch and confirm the billing alert reflects running
   resources.
8. Complete the Week 4 report.

---

## Evidence to Capture for the Internship Report

Screenshots and command output that demonstrate the work. Redact the account
ID, instance ID, and public IP in anything shared publicly.

**Cloud infrastructure**
1. VPC resource map showing public and private subnets across two AZs.
2. EC2 instance summary: `running`, AL2023, IAM role attached.
3. **EC2 security group inbound rules** — one row, TCP 80. This single
   screenshot is the strongest evidence of the "no public SSH" decision.
4. RDS instance summary: `available`, **Publicly accessible: No**, **Encryption:
   Enabled**.
5. **RDS security group inbound rule** showing the *source is a security group*,
   not a CIDR — this is the detail that distinguishes a considered design from a
   default one.
6. Parameter Store list showing `/dc-intern/prod/db/password` typed as
   **SecureString**.
7. IAM role page showing `AmazonSSMManagedInstanceCore` + the scoped inline
   policy.

**Deployment and operation**
8. A Session Manager session in the browser — proof of access without SSH.
9. `sudo systemctl status dc-intern-backend` showing `active (running)`.
10. `python manage.py check_database` output: `postgresql`, `SSL mode: require`,
    `OK`, with `Password: set (not shown)` visible — it demonstrates the
    diagnostic *and* the redaction.
11. `python manage.py migrate` output listing the applied migrations.
12. `sudo nginx -t` returning `syntax is ok` / `test is successful`.
13. `sudo journalctl -u dc-intern-backend -n 30` showing Gunicorn access lines
    and no tracebacks.

**Proof it works**
14. Browser at `http://<public-ip>/api/health/` showing the JSON response.
15. Browser at `http://<public-ip>/api/profiles/` showing the DRF browsable API.
16. Django admin login page **with CSS**, proving `collectstatic` + Nginx.
17. A Skill Gap Analysis generated against the deployed backend, and the row
    visible at `/api/recommendations/` (to be captured — see Limitations).
18. A failed connection attempt to `<public-ip>:8000` and to port 5432 —
    negative evidence that the loopback binding and the private database
    actually hold.

**Cost and governance**
19. AWS Budgets page showing the alert configured on Day 1.
20. Billing dashboard for the month.

**In the written report, explain the *why* behind three decisions** — these are
what distinguish an internship report from a deployment log:
- Why Gunicorn binds to `127.0.0.1` instead of `0.0.0.0`.
- Why the RDS rule references a security group instead of an IP range.
- Why secure cookies and HTTPS redirect are switched **off** today (enabling
  them before TLS exists breaks logins instead of hardening them).
