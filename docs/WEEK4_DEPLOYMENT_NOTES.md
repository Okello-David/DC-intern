# Week 4 Deployment Notes

How the AI-Powered Student Career and Internship Assistant is deployed on AWS:
what exists, how each half gets there, and what is deliberately not done yet.

> **Scope of what has actually run.** The backend is deployed and verified on
> EC2 (Day 4 — see [`WEEK4_DAY4_DEPLOYMENT_REPORT.md`](WEEK4_DAY4_DEPLOYMENT_REPORT.md)).
> The **frontend deployment files and the Bedrock integration in this document
> are prepared and tested locally, but have not been executed on the instance.**
> Nothing below should be read as "this ran in production" unless it says so.
>
> Public identifiers (account id, instance id, IP, security group ids) are
> deliberately not written here.

---

## 1. Architecture implemented

```
                        Internet
                           │  HTTP :80   (no TLS yet)
                           ▼
 ┌───────────────── EC2 · Amazon Linux 2023 · public subnet ─────────────────┐
 │                                                                           │
 │   Nginx  (public, port 80)                                                │
 │     ├── /            → /var/www/dc-intern      React build, SPA fallback  │
 │     ├── /assets/     → /var/www/dc-intern      hashed bundles, 1y cache   │
 │     ├── /static/     → backend/staticfiles/    Django admin + DRF assets  │
 │     ├── /api/        ─┐                                                   │
 │     ├── /admin/      ─┼─ proxy_pass ──► Gunicorn                          │
 │     └── /api-auth/   ─┘                                                   │
 │                                     │                                     │
 │   Gunicorn  127.0.0.1:8000 — loopback only, never public                  │
 │     • config.wsgi:application, 2 workers, systemd-managed                 │
 │     • reads every setting from /etc/dc-intern/backend.env                 │
 │                          │                        │                       │
 └──────────────────────────┼────────────────────────┼───────────────────────┘
                            │ PostgreSQL 5432, TLS   │ HTTPS, IAM role
                            ▼                        ▼
              Amazon RDS PostgreSQL          Amazon Bedrock Runtime
              private subnets, no             (AI_PROVIDER=bedrock)
              public route                    amazon.nova-micro-v1:0
```

**The one-origin decision.** React and Django are served from the same Nginx
server block, split by path prefix. The frontend is therefore built with
`VITE_API_BASE_URL=/api` and contains **no hostname and no IP address**. Three
consequences worth stating:

1. The Day 4 finding that *"the public IP is not an Elastic IP, and that blocks
   Day 5"* no longer blocks the **build**. A relative URL keeps working when the
   address changes. (An Elastic IP is still wanted — for a stable link to share
   and a stable `ALLOWED_HOSTS` entry — but it is not a build-time dependency.)
2. There are no cross-origin requests, so no CORS preflight and no origin list
   to keep in step with the server.
3. Adding TLS later secures both halves in one step.

The cost is that frontend and backend scale together and share a failure domain.
For a single-instance student project that is the right trade; the S3 +
CloudFront alternative is in [§13](#13-future-improvement-s3--cloudfront).

## 2. AWS resources used

| Resource | Identifier | Notes |
|---|---|---|
| Region | `eu-north-1` (Stockholm) | Single region |
| VPC | Custom | Public application tier, private database tier |
| Subnets | 1 public (app), 2 private (DB, two AZs) | Two AZs required for an RDS subnet group |
| EC2 | `t3.micro`, Amazon Linux 2023 | Nginx + Gunicorn |
| EC2 security group | `dc-intern-ec2-sg` | Exactly one inbound rule: TCP 80. No SSH |
| RDS | `dc-intern-postgres`, `db.t4g.micro`, PostgreSQL 18.3 | Private, encrypted, not publicly accessible |
| RDS security group | `dc-intern-rds-sg` | TCP 5432 from the **EC2 security group** only |
| IAM role | `dc-intern-ec2-role` (profile `dc-intern-ec2-profile`) | `AmazonSSMManagedInstanceCore` + scoped Parameter Store read |
| Parameter Store | `/dc-intern/prod/*` | Database password stored as a SecureString |
| Session Manager | — | Administration; replaces SSH entirely |
| **Amazon Bedrock** | `amazon.nova-micro-v1:0` | **Prepared, not enabled.** Model access has not been requested and no IAM permission has been added |

Nothing new was created for Day 5. The frontend is published to a directory on
the existing instance; Bedrock is code plus configuration.

## 3. Frontend deployment process

```bash
# On the instance, via Session Manager, as ec2-user
cd /opt/dc-intern
git pull
./deploy/scripts/deploy_frontend.sh
```

`deploy/scripts/deploy_frontend.sh`:

1. **Preflight** — refuses to run as root, checks `frontend/package.json` exists
   and that Node is 20 or newer (Vite 8 requires it).
2. **Install** — `npm ci` from `package-lock.json`, so the deployed bundle is
   built from exactly the dependency versions that were tested.
3. **Build** — `VITE_API_BASE_URL=/api npm run build` after deleting any previous
   `dist/`, then fails the deployment if `127.0.0.1:8000` appears anywhere in the
   output (the signature of a stale `frontend/.env`).
4. **Publish** — `rsync -a --delete` of `dist/` into `/var/www/dc-intern`, owned
   `root:root`, directories `755`, files `644`. The Nginx worker can read them
   and cannot write them: if it could, a web-server compromise would become the
   ability to replace the application's JavaScript for every visitor.
   `restorecon` relabels the files for SELinux, which is enforcing on Amazon
   Linux 2023.
5. **Reload** — `nginx -t`, then `systemctl reload nginx` (reload, not restart:
   no in-flight connection is dropped).
6. **Smoke test** — `/`, a deep link (proving the SPA fallback), and
   `/api/health/` through the same origin.

Node.js is needed **only at build time**. Nothing runs Node in production; Nginx
serves static files.

**Build command, for the record:**

```bash
cd frontend
VITE_API_BASE_URL=/api npm run build     # production, same-origin
npm run build                            # local default → http://127.0.0.1:8000/api
```

## 4. Backend deployment process

Unchanged from Day 4 apart from the Nginx site and a web-root step:

```bash
cd /opt/dc-intern
git pull
SERVER_NAME=<public-dns-name> ./deploy/scripts/deploy_backend.sh
# or, to do both halves:
SERVER_NAME=<public-dns-name> DEPLOY_FRONTEND=1 ./deploy/scripts/deploy_backend.sh
```

The script creates/reuses the virtualenv on Python 3.12, installs
`requirements.txt` (now including `boto3`), runs `check`, `check --deploy`,
`check_database`, `migrate`, and `collectstatic`, installs and restarts the
systemd unit, creates `/var/www/dc-intern` with a holding page if the frontend
has not been published yet, renders and validates the Nginx site, restarts
Nginx, and smoke-tests Gunicorn directly, then through Nginx.

It never creates, fetches, edits, or prints `/etc/dc-intern/backend.env`; it
only verifies with `grep -q` that the required keys exist. `set -x` must never
be enabled in it.

## 5. Database connection

No change from Day 3/4. `DB_HOST` is the single switch: empty means local
SQLite, set means PostgreSQL on RDS.

The instance can reach the database because of **security-group membership**,
not because of an address: `dc-intern-rds-sg` admits TCP 5432 from
`dc-intern-ec2-sg`. The credentials in the environment file are only half of it.
This is why migrations run from the instance and never from a laptop, and why
the RDS endpoint being unreachable from a laptop is the design working.

`DB_SSLMODE=require` encrypts the EC2 → RDS hop. It does **not** verify the
server certificate — that needs `verify-full` plus the RDS CA bundle on the
instance, which is a configuration change, not a code change.

## 6. Bedrock integration

**Status: implemented and unit-tested against a mocked client; never executed
against the real service.**

- `backend/career/services/ai_service.py` holds the provider dispatch and the
  Bedrock client. `AI_PROVIDER` selects `mock` or `bedrock`.
- `backend/career/services/prompts.py` holds the system instruction and the
  prompt builder — separate, so the prompt can be reviewed without reading AWS
  code. Full write-up: [`AI_PROMPT_DOCUMENTATION.md`](AI_PROMPT_DOCUMENTATION.md).
- The **Converse API** is used, so changing model is an environment-variable
  change rather than a code change.
- **No AWS keys.** boto3 resolves temporary credentials from the EC2 instance
  role. `deploy/backend.env.example` contains no `AWS_ACCESS_KEY_ID`, and none
  should ever be added.
- **Failures are contained.** `ClientError` codes map to written-for-users
  messages; the AWS payload is logged as a code only and never returned to the
  browser. Prompts and responses are never logged.
- **Fallback is honest.** `AI_FALLBACK_TO_MOCK=True` returns the local analysis
  labelled as a fallback (`provider: "mock"`, `fallback_used: true`, a `notes`
  entry, and a banner in the text itself). `False` returns a clean `503`.

**Before enabling `AI_PROVIDER=bedrock` on the instance:**

1. Request model access for `amazon.nova-micro-v1:0` in `eu-north-1`.
2. Add an inline policy to `dc-intern-ec2-role` allowing `bedrock:InvokeModel`
   on **that model's ARN only** — not `bedrock:*` on `*`.
3. Confirm the budget alert covers Bedrock.
4. Add rate limiting to the skill-gap endpoint (a paid call behind an
   unauthenticated endpoint is a cost incident waiting to happen).
5. Test with an invented profile, then record the result.

## 7. Environment variables

All in `/etc/dc-intern/backend.env` (`root:ec2-user`, `0640`), outside the
repository. Template: `deploy/backend.env.example`.

| Variable | Purpose | Secret |
|---|---|---|
| `DEBUG` | Must be `False` in any deployment | No |
| `SECRET_KEY` | Django signing key | **Yes** |
| `ALLOWED_HOSTS` | Hostnames Django will serve (no scheme) | No |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API | No |
| `CSRF_TRUSTED_ORIGINS` | Origins allowed to send unsafe requests (with scheme) | No |
| `USE_HTTPS` | Gates secure cookies, HTTPS redirect, HSTS. `False` until TLS exists | No |
| `DB_NAME` / `DB_USER` / `DB_HOST` / `DB_PORT` / `DB_SSLMODE` | PostgreSQL connection | No |
| `DB_PASSWORD` | Database password, from Parameter Store | **Yes** |
| `AI_PROVIDER` | `mock` or `bedrock` | No |
| `AI_MODEL` | Bedrock model id | No |
| `AWS_BEDROCK_REGION` | Region for the Bedrock endpoint | No |
| `AI_MAX_TOKENS` | Response cap, and a cost cap | No |
| `AI_TEMPERATURE` | `0.2` — conservative, repeatable output | No |
| `AI_FALLBACK_TO_MOCK` | Behaviour when Bedrock fails | No |
| `AI_API_KEY` | Unused by mock and bedrock; reserved for a future key-based provider | **Yes if ever set** |

**Frontend:** exactly one, `VITE_API_BASE_URL`, set at build time only. Every
`VITE_*` value is compiled into the public bundle, so a secret must never be one.

**Same-origin note.** With Nginx serving both halves, `CORS_ALLOWED_ORIGINS`
becomes unnecessary in production — the browser makes no cross-origin request.
It stays configured for local development, where Vite on `:5173` calls Django on
`:8000`.

## 8. IAM role usage

`dc-intern-ec2-role`, attached through the instance profile:

| Grant | Used for | Scope |
|---|---|---|
| `AmazonSSMManagedInstanceCore` | Session Manager administration | AWS managed policy |
| Inline policy: `ssm:GetParameter(s)`, `ssm:GetParametersByPath` | Reading configuration values | `arn:aws:ssm:eu-north-1:<account-id>:parameter/dc-intern/prod/*` |
| *(to add)* `bedrock:InvokeModel` | The AI feature | Should be the single model ARN, not `*` |

The point of the role: **there are no long-lived credentials on the instance.**
boto3 obtains short-lived credentials from the instance metadata service, and
they cannot be used from anywhere else. An access key copied off a public
instance works from any machine on earth until someone revokes it; an instance
role does not leave the instance.

## 9. Nginx routing

| Path | Handled by | Notes |
|---|---|---|
| `/` | `/var/www/dc-intern` | `try_files $uri $uri/ /index.html` — SPA fallback, so a deep link or refresh returns the app, not a 404 |
| `/assets/` | `/var/www/dc-intern/assets` | Vite-fingerprinted filenames → `Cache-Control: public, immutable`, 1 year |
| `= /index.html` | `/var/www/dc-intern` | `Cache-Control: no-cache` — it is not fingerprinted, and it points at the hashed bundles. Caching it pins users to the previous release |
| `/static/` | `backend/staticfiles/` | Django admin and DRF browsable API assets |
| `/api/` | Gunicorn | `proxy_read_timeout 120s` for Bedrock calls |
| `/admin/` | Gunicorn | Django admin |
| `/api-auth/` | Gunicorn | DRF login views; currently 404s at Django, so enabling them later needs no Nginx change |

Every proxied location forwards `Host`, `X-Real-IP`, `X-Forwarded-For`,
`X-Forwarded-Proto`, and `X-Forwarded-Host`. `X-Forwarded-Proto` is always
**set**, never passed through from the client — that is what makes
`SECURE_PROXY_SSL_HEADER` in `settings.py` safe to trust. Gunicorn stays bound to
`127.0.0.1:8000`, so the application cannot be reached except through Nginx
regardless of what the security group allows.

## 10. Verification checklist

Run on the instance in this order; each step isolates one layer, so a failure
tells you *where* the problem is.

| # | Check | Expected |
|---|---|---|
| 1 | `sudo systemctl status dc-intern-backend` | `active (running)` |
| 2 | `python manage.py check_database` | `postgresql`, `SSL mode: require`, `OK` |
| 3 | `curl http://127.0.0.1:8000/api/health/` | JSON — Gunicorn works |
| 4 | `curl http://127.0.0.1/api/health/` | Same JSON — Nginx proxying works |
| 5 | `curl -I http://127.0.0.1/` | `200`, `Content-Type: text/html` — React is published |
| 6 | `curl -I http://127.0.0.1/some/deep/link` | `200` — SPA fallback works |
| 7 | `curl -sI http://127.0.0.1/assets/<hashed>.js` | `200`, `Cache-Control: public, immutable` |
| 8 | `curl -sI http://127.0.0.1/index.html \| grep -i cache` | `no-cache` |
| 9 | Open `http://<public-address>/` in a browser | The app loads, no console errors |
| 10 | Browser devtools → Network | API calls go to `/api/...` on the same origin — no IP, no CORS preflight |
| 11 | Create a profile, add a skill, add a career input | All `201`, visible in the summary |
| 12 | Click **Generate Skill Gap Analysis** | Spinner, then eight sections; `provider` and `fallback_used` shown honestly |
| 13 | `curl http://<public-address>/api/recommendations/` | The analysis is saved |
| 14 | Open `http://<public-address>/admin/` | Login page **with CSS** — `collectstatic` + `/static/` work |
| 15 | `sudo journalctl -u dc-intern-backend -n 50` | No tracebacks, **no secrets**, no prompt text |
| 16 | Stop Gunicorn, reload the page | The React app still loads (static), API calls show a readable error — no traceback |
| 17 | Reboot the instance, repeat 4 and 5 | Both still work |

With `AI_PROVIDER=bedrock`, additionally: response `provider` reads `bedrock`
and `fallback_used` is `false`; if it reads `mock`, the fallback fired and the
`notes` entry says why.

## 11. Common failure modes

| Symptom | Most likely cause | Check |
|---|---|---|
| `403 Forbidden` on `/` | `/var/www/dc-intern` empty, or SELinux labels wrong | `ls /var/www/dc-intern`; `sudo restorecon -R /var/www/dc-intern` |
| `404` on a deep link, `/` fine | `try_files` missing from `location /` | Re-render the site from the template |
| Blank page, console 404s for `/assets/...` | Stale `index.html` cached, pointing at old bundles | Hard refresh; confirm `Cache-Control: no-cache` on `/index.html` |
| App loads, every API call fails | Built with the wrong base URL | Check the bundle for `127.0.0.1:8000`; rebuild with `VITE_API_BASE_URL=/api` |
| CORS error in the browser | The frontend is not on the same origin as the API | With this Nginx site there should be no cross-origin call at all — check the built base URL first |
| `502 Bad Gateway` on `/api/` only | Gunicorn is down; static files still serve | `sudo systemctl status dc-intern-backend`, `journalctl -u dc-intern-backend -n 50` |
| `504` on the skill-gap endpoint | AI call slower than a timeout | `proxy_read_timeout` (120s) and Gunicorn's `--timeout` (60s) — the tighter one wins |
| `400 Bad Request` / `DisallowedHost` | Hostname not in `ALLOWED_HOSTS` | Add it, restart the service |
| CSRF failure in the admin | Hostname missing from `CSRF_TRUSTED_ORIGINS` (needs the scheme) | Add `http://<host>`, restart |
| Admin has no styling | `collectstatic` not run, or Nginx cannot traverse to it | `sudo chmod o+rx /opt/dc-intern /opt/dc-intern/backend` |
| `npm ci` fails on the instance | Node older than 20, or lock file out of sync | `node --version`; fix the lock file in git, do not switch to `npm install` |
| Analysis always says `fallback_used: true` with Bedrock configured | Model access not enabled, or the role lacks `bedrock:InvokeModel` | Read the `notes` entry; check the journal for the logged error code |
| `503` from the skill-gap endpoint | Provider failed with `AI_FALLBACK_TO_MOCK=False` | Intended behaviour — the message says which condition |
| Everything breaks after `USE_HTTPS=True` | TLS is not actually terminated | Set it back to `False` until a certificate exists |

## 12. Cost awareness

| Resource | Cost shape | Control in place |
|---|---|---|
| EC2 `t3.micro` | Hourly, free-tier eligible | One instance; stop it when not demonstrating |
| RDS `db.t4g.micro` | Hourly + storage, free-tier eligible | Single-AZ, 1-day backup retention |
| Data transfer out | Per GB | Low; the frontend bundle is ~205 KB (~64 KB gzipped) |
| Elastic IP | Free **while attached to a running instance**, charged when idle | Not yet allocated; release it if the instance is terminated |
| Parameter Store standard | Free | — |
| Session Manager | Free | — |
| **Amazon Bedrock** | **Per input + output token** | `AI_MAX_TOKENS=1200`; `amazon.nova-micro-v1:0` is the cheapest text model in the family; **currently disabled** |
| CloudWatch logs | Per GB ingested | No log shipping configured yet |

The real cost risk is not the instances — it is **an unauthenticated,
unthrottled endpoint that makes a paid API call**. One script clicking
"Generate" in a loop is a bill. That is why Bedrock stays off until rate
limiting exists, and why the account-level budget alert from Day 1 matters.

Serving the frontend from the existing EC2 instance adds **no new resource and
no new cost**, which is the other half of why it was chosen over S3 +
CloudFront for this week.

## 13. Current limitations

- **No TLS.** Plain HTTP on port 80. Everything a student types — including
  resume text — crosses the network unencrypted. Do not use the deployment with
  real personal data until `USE_HTTPS=True` and a certificate are in place.
- **No authentication.** Any visitor can create, read, and generate for any
  profile. The single largest gap.
- **No rate limiting.** Cost and abuse risk once Bedrock is enabled.
- **Bedrock has never been called.** Code and tests exist; model access, the IAM
  permission, and a real request do not.
- **Frontend deployment scripts have not been run on the instance.** They are
  syntax-checked, and the build they perform has been run locally.
- **No Elastic IP**, so the public address changes on stop/start. The build no
  longer depends on it, but the shareable link and `ALLOWED_HOSTS` still do.
- **Single instance, single AZ, no load balancer**; RDS is not Multi-AZ. Any
  instance failure is a full outage.
- **No CloudWatch log shipping.** Logs live in the instance journal and die with
  the instance.
- **No rollback step** in either deploy script. A failure after `migrate` is
  recovered by hand.
- **No CI/CD.** Deployment is a manual `git pull` plus a script.
- **`DB_SSLMODE=require` does not verify the server certificate.**
- **No backups tested.** RDS snapshots exist by default; a restore has never
  been performed.

## 14. Future improvement: S3 + CloudFront

The frontend is a directory of static files, so serving it from EC2 is a choice,
not a requirement.

| | EC2 + Nginx (today) | S3 + CloudFront (future) |
|---|---|---|
| New AWS resources | None | S3 bucket, CloudFront distribution, OAC |
| Cost | Included in the instance | Pennies at this traffic, but a new line item |
| TLS | Must be configured on the instance | Free certificate via ACM on CloudFront |
| Availability | Dies with the instance | Survives an instance outage (static half) |
| Latency | One region | Edge-cached globally |
| CORS | None — same origin | **Reintroduced**: the API is on a different origin, so `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` must list the CloudFront domain |
| Deployment | `npm run build` + rsync | `npm run build` + `aws s3 sync` + a CloudFront invalidation |
| Complexity | One config file | Bucket policy, OAC, distribution behaviours, cache invalidation |

**Migration sketch**, whenever it is worth doing:

1. Create a private S3 bucket (no public access) and a CloudFront distribution
   with Origin Access Control.
2. Add a CloudFront behaviour routing `/api/*` and `/admin/*` to the EC2 origin,
   keeping one public origin — which preserves the same-origin property and the
   relative `/api` build.
3. Or, if the API is given its own hostname, rebuild with
   `VITE_API_BASE_URL=https://api.<domain>` and add that origin to
   `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
4. Configure the SPA fallback at the CDN: 403/404 → `/index.html` with a `200`.
5. `aws s3 sync dist/ s3://<bucket>/ --delete`, then invalidate `/index.html`.

Option 2 is the better one: it keeps a single origin, so nothing about CORS,
CSRF, or the frontend build has to change.

---

## References

- [`AI_PROMPT_DOCUMENTATION.md`](AI_PROMPT_DOCUMENTATION.md) — prompt, safety, privacy
- [`WEEK4_DAY4_DEPLOYMENT_REPORT.md`](WEEK4_DAY4_DEPLOYMENT_REPORT.md) — Day 4 verification evidence
- [`WEEK4_AI_AND_DEPLOYMENT.md`](WEEK4_AI_AND_DEPLOYMENT.md) — the week's design write-up
- [`WEEK4_WEEKLY_REPORT.md`](WEEK4_WEEKLY_REPORT.md) — supervisor report
