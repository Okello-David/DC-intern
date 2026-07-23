# Week 4 Weekly Report — AI Integration and AWS Deployment

**Project:** AI-Powered Student Career and Internship Assistant
**Week:** 4 of 6
**Period covered:** Day 1 (AWS account safety) to Day 5 (frontend deployment, Bedrock integration, documentation)

---

## 1. What I researched this week

**AWS account safety before provisioning anything.** How to enable MFA on the
root account, how AWS Budgets alerts work, where to check remaining credit, and
how to configure a named AWS CLI profile so my personal credentials are not the
default on my machine.

**VPC network design.** The difference between the default VPC and a custom one;
why an RDS subnet group requires subnets in at least two Availability Zones; and
the practical difference between granting database access by **CIDR block**
versus by **security group identity**. The second is what makes the database
reachable by *the application* rather than by *an address range*.

**Running Django in production.** Why `manage.py runserver` must never be used
in production, what Gunicorn does that Nginx cannot (execute Python) and what
Nginx does that Gunicorn should not (face the internet), and how the two connect
through a loopback socket. Also how `collectstatic` and `STATIC_ROOT` work when
`DEBUG=False` stops Django serving static files.

**Instance access without SSH.** AWS Systems Manager Session Manager: how it
works through the SSM agent making an *outbound* connection, so no inbound port
22 rule is needed, no key pair exists, and access is controlled by IAM and
logged in CloudTrail.

**Serving a single-page application behind a reverse proxy.** Why
`try_files $uri $uri/ /index.html` is required (a client-side route is not a
file on disk, so a refresh 404s without it), why Vite's fingerprinted bundles
can be cached for a year while `index.html` must not be cached at all, and how
to split one origin between a static app and a proxied API by path prefix.

**Amazon Bedrock.** The difference between `invoke_model` and the **Converse
API** (one request/response shape across every model, so switching model is a
configuration change); how boto3 resolves credentials, and therefore how an EC2
instance role removes the need for an API key entirely; Bedrock's per-token
pricing and the model options; and what AWS states about prompt data retention.

**Prompt design for advice about a real person.** Reading about hallucination
and over-claiming in AI career tools convinced me the risky failure is not a bad
suggestion but a *confident* one — an invented qualification or an implied job
guarantee. That drove the explicit prohibitions in the system prompt, the low
temperature, and the standing disclaimer in the UI.

## 2. What I built this week

**Day 1 — account safety.** MFA on root, a budget alert, credit checked, a named
CLI profile. No billable resources created.

**Day 2 — environment configuration and the first AI feature.**
- Moved every setting into environment variables via `python-decouple`; with
  `DEBUG=False` and no `SECRET_KEY`, Django now refuses to start.
- `backend/career/services/ai_service.py` — the only module allowed to talk to
  an AI provider.
- `POST /api/profiles/<id>/generate-skill-gap/`, which gathers a profile's
  skills and career inputs, produces an analysis, saves it as a
  `Recommendation`, and returns it.
- A rule-based local analyser so the feature works offline at zero cost, with
  `used_fallback` in the response so the mode is never ambiguous.
- `AIRecommendationPanel.jsx` on the frontend, with loading and error states.

**Day 3 — private database.** A custom VPC with a public application tier and
private database subnets across two AZs; a private, encrypted RDS PostgreSQL
instance reachable only from the application security group;
`build_database_config()` making `DB_HOST` the single switch between SQLite and
PostgreSQL; and a `check_database` diagnostic command that never prints the
password and masks the host.

**Day 4 — backend on EC2.** Gunicorn under systemd bound to `127.0.0.1:8000`, an
Nginx site on port 80, a repeatable deploy script, and `/etc/dc-intern/backend.env`
outside the repository. **Deployed and verified:** migrations applied to the
private RDS instance, all CRUD endpoints live, static files served, health
endpoint returning `200`.

**Day 5 — frontend deployment, real AI provider, documentation.**
- `VITE_API_BASE_URL` now drives the frontend's API base URL: `/api` in
  production, `http://127.0.0.1:8000/api` locally. **No IP address or hostname
  is compiled into the bundle.** Verified by building both ways and grepping the
  output.
- Nginx now serves React and Django from one origin, with SPA fallback,
  fingerprinted-asset caching, a `no-cache` `index.html`, and proxying for
  `/api/`, `/admin/`, and `/api-auth/`.
- `deploy/scripts/deploy_frontend.sh` — install, build, publish to
  `/var/www/dc-intern` with read-only permissions, SELinux relabel, validate and
  reload Nginx, smoke test.
- **Amazon Bedrock provider** via the Converse API and the EC2 IAM role, with
  `AI_PROVIDER`, `AI_MODEL`, `AWS_BEDROCK_REGION`, `AI_MAX_TOKENS`,
  `AI_TEMPERATURE`, and `AI_FALLBACK_TO_MOCK`. No AWS key anywhere.
- A reusable prompt builder in `services/prompts.py`, with a system instruction
  carrying explicit safety rules and an eight-section output contract.
- The endpoint now returns `provider`, `model`, and `fallback_used`, so what
  produced the text is always visible.
- UI: spinner and `aria-live` status, written-for-users error messages with a
  retry, preserved line breaks, honest provider labelling, and a standing
  "AI-assisted — please review" disclaimer.
- Tests grew from 26 to **57**, covering mock mode, the Bedrock request shape,
  response extraction, every error path, both fallback modes, and a test that
  fails if any AWS client is constructed during the suite.
- Documentation: `AI_PROMPT_DOCUMENTATION.md`, `WEEK4_DEPLOYMENT_NOTES.md`, this
  report, plus updates to the three READMEs and `WEEK4_AI_AND_DEPLOYMENT.md`.

## 3. Key technical decisions

**Serve React and Django from one Nginx origin.** The alternative was S3 +
CloudFront. One origin means the frontend can be built with a *relative* `/api`,
so no address is compiled into the bundle; it removes CORS entirely; and it adds
no new AWS resource or cost. It also dissolved a Day 4 blocker: the instance's
public IP is ephemeral, which would have made an absolute API URL wrong after
every stop/start. The trade-off — both halves share one failure domain and scale
together — is acceptable for a single-instance project, and the S3 + CloudFront
migration is documented for when it is not.

**Amazon Bedrock rather than a key-based AI API.** The application already runs
on EC2 with an instance role, and Bedrock is reachable with that role. That
removes the API key entirely: nothing to store in the environment file, nothing
to rotate, nothing to leak. Credentials are temporary and unusable off the
instance. It also keeps the whole system inside one account's billing and IAM.

**The Converse API rather than `invoke_model`.** One request and response shape
for every Bedrock model, so changing model is an `AI_MODEL` change with no code
change and no per-vendor JSON body.

**Mock stays the default, everywhere.** `AI_PROVIDER` defaults to `mock`, so a
fresh checkout, CI, and the test suite cannot call AWS by accident, cannot cost
money, and send no student data anywhere. Every test runs in mock mode or against
a mocked client; one test fails if `boto3.client` is called at all.

**A fallback must never impersonate the model.** With `AI_FALLBACK_TO_MOCK=True`
a Bedrock failure returns the local analysis, but the response reports
`provider: "mock"`, `fallback_used: true`, a `notes` entry explaining why, and
the saved text itself carries a `NOTE — FALLBACK MODE` banner. A recommendation
read six weeks from now still says what produced it. `False` gives a clean `503`
for when proving the model path matters more than always answering.

**The prompt lives in its own module and excludes the student's name.** Keeping
`prompts.py` separate from the AWS code means a supervisor can review exactly
what is sent without reading networking code. The name is not needed for a skill
gap analysis, so it is not sent — the text reaching AWS is not directly
identifying. Career input is truncated to 1500 characters, which bounds what
leaves the server, what is billed, and how much untrusted text can steer the
response.

**AWS error detail stops at the server.** `ClientError` codes map to messages
written for students; the AWS payload is logged as a *code* only. Prompts and
responses are never logged — there is a test that fails if student text reaches
the log.

**Static files owned by root, not by Nginx.** `/var/www/dc-intern` is `root:root`
with `644`/`755`. Nginx only needs to read; if it could write, a web-server
compromise would become the ability to replace the application's JavaScript for
every visitor.

## 4. Challenges faced

1. **The frontend had a hard-coded backend URL, and the instance's IP is not
   stable.** `http://127.0.0.1:8000/api` was compiled into the bundle. Putting
   the public IP there instead would have produced a build that breaks the next
   time the instance stops and starts — the Day 4 review had flagged the missing
   Elastic IP as a Day 5 blocker.

2. **Deciding where the frontend should live.** S3 + CloudFront is the
   "proper" answer and is in the Week 2 plan, but it introduces a second origin,
   which reintroduces CORS and CSRF origin configuration, plus bucket policies,
   OAC, and cache invalidation — a lot of new surface for one week.

3. **Integrating a real AI provider without being able to prove it works.**
   Bedrock model access has not been granted in the account, and enabling a paid
   API behind an endpoint with no authentication and no rate limiting is a real
   cost risk. But leaving the provider unimplemented would have left the AI
   integration goal unmet.

4. **Making the test suite exercise Bedrock without ever calling AWS.** A test
   that quietly makes a real API call would cost money, fail offline, and behave
   differently depending on whose AWS profile is active.

5. **Errors that are useful without leaking.** An AWS `AccessDeniedException`
   message can contain role ARNs and account identifiers; a Django traceback
   exposes internals. Neither belongs in a browser. But "something went wrong"
   with nothing in the logs makes an outage undiagnosable.

6. **A fallback that could quietly become a lie.** If Bedrock fails and the
   local analyser answers, a student — or a marker reading a screenshot — could
   easily believe an AI model wrote it.

7. **Deep links returning 404.** A single-page app's routes are not files, so a
   naive static configuration 404s on refresh.

## 5. How I attempted to solve them

1. **Same-origin relative URL.** `API_BASE_URL` now reads
   `import.meta.env.VITE_API_BASE_URL` with the local default as a fallback, and
   Nginx serves both halves from one origin, so production builds with
   `VITE_API_BASE_URL=/api`. I verified it by building both ways and grepping
   the bundle: the production build contains `/api` and no IP or hostname; the
   default build contains `127.0.0.1:8000`. The deploy script also **fails the
   deployment** if `127.0.0.1:8000` appears in a same-origin build, which is
   what a stale `frontend/.env` would cause.

2. **Chose EC2 + Nginx for this week, and wrote down why and what changes.**
   `WEEK4_DEPLOYMENT_NOTES.md` §14 has the comparison table and a migration
   sketch, including the detail that routing `/api/*` through CloudFront to the
   EC2 origin would preserve the same-origin property and require no frontend
   change.

3. **Implemented the provider fully, left it switched off, and said so
   everywhere.** `AI_PROVIDER` stays `mock`; enabling Bedrock is one environment
   variable plus model access and a scoped IAM permission. Every document says
   plainly that no Bedrock request has been made and that model output quality
   is unassessed. I would rather report an untested integration honestly than
   claim a result I do not have.

4. **One place constructs the client, and tests patch it.** `_bedrock_client()`
   is the only place `boto3.client` is called; Bedrock tests patch that function
   and assert on the `converse` call. To prove the patching is airtight, one test
   replaces `boto3.client` itself with a function that fails the test if called,
   then runs the endpoint.

5. **Two channels: written-for-users messages out, error codes to the log.**
   Known `ClientError` codes map to messages like "The AI service is busy right
   now"; unknown codes get a generic message. The AWS payload is never returned,
   and the log records the code only. Tests assert that an ARN and an account id
   in a raw AWS message do not appear in the message a user sees, and that
   student-written text never reaches the log.

6. **Made the honest answer structural rather than a convention.** The service
   returns the provider that *ran*, not the one configured; the content gets a
   fallback banner; the API adds a `notes` entry; the UI shows "Generated by the
   local rule-based analyser — no AI model was used". Four independent places
   would all have to be wrong for the fallback to pass as model output.

7. **`try_files $uri $uri/ /index.html`**, with a smoke test in the deploy script
   that requests a deep link and fails if it does not return `200`.

## 6. What I need guidance on

1. **Approval to enable Bedrock, and on what terms.** Model access for
   `amazon.nova-micro-v1:0` in `eu-north-1` plus a `bedrock:InvokeModel`
   permission scoped to that one model ARN. My proposed precondition is rate
   limiting on the endpoint first. Is there a spend ceiling I should assume?

2. **Authentication before real student data.** The endpoints are unauthenticated,
   so anyone can create profiles and generate analyses. Should Week 5 be DRF
   token authentication, Django session auth, or Amazon Cognito? Cognito is more
   AWS learning; token auth is far less to get wrong.

3. **TLS.** With no domain name, the options are a self-signed certificate
   (browser warnings), an ALB with an ACM certificate (extra cost), or
   registering a cheap domain and using Let's Encrypt. My preference is the
   domain plus Let's Encrypt. Is a small domain cost acceptable?

4. **Whether an Elastic IP should be allocated now.** It is free while attached
   to a running instance and would give a stable link for demonstrations. The
   frontend no longer depends on it, but `ALLOWED_HOSTS` and any shared link do.

5. **How much resume text should be allowed to reach AWS.** Currently truncated
   to 1500 characters per entry with the student's name excluded. Should there be
   an explicit consent step in the UI before any text is sent to an AI provider?

6. **Whether model output should be validated before it is saved.** Nothing
   currently checks that all eight sections are present or that no employment
   guarantee slipped through. Is a structural validator expected in Week 5, or
   is the disclaimer sufficient for a student project?

## 7. Evidence of progress

**In the repository**

| Evidence | Where |
|---|---|
| Bedrock provider, dispatch, error handling | `backend/career/services/ai_service.py` |
| Prompt, safety rules, privacy exclusions | `backend/career/services/prompts.py` |
| Provider metadata in the API response | `backend/career/views.py` |
| Environment-driven frontend base URL | `frontend/src/services/api.js`, `frontend/.env.example` |
| Loading, errors, honest provider label, disclaimer | `frontend/src/components/AIRecommendationPanel.jsx` |
| One-origin routing, SPA fallback, caching | `deploy/nginx/dc-intern.conf.template` |
| Frontend build and publish | `deploy/scripts/deploy_frontend.sh` |
| 57 automated tests | `backend/career/tests.py` |
| Prompt and safety documentation | `docs/AI_PROMPT_DOCUMENTATION.md` |
| Deployment notes and checklists | `docs/WEEK4_DEPLOYMENT_NOTES.md` |
| Day 4 AWS verification evidence | `docs/WEEK4_DAY4_DEPLOYMENT_REPORT.md` |

**Verified this week (locally)**

```
$ python manage.py test
Ran 57 tests in 0.3s
OK

$ VITE_API_BASE_URL=/api npm run build
✓ built in 1.04s     dist/assets/index-*.js  205 KB (64 KB gzipped)
$ grep -c '127.0.0.1:8000' dist/assets/index-*.js
0                    # no host is compiled into the production bundle
```

**Verified on AWS (Day 4, read-only checks)**

- EC2 running, SSM agent online, IAM instance profile attached.
- EC2 security group: exactly one inbound rule — TCP 80. No SSH, no 8000, no 5432.
- RDS `available`, **not** publicly accessible, storage encrypted, reachable only
  from the EC2 security group.
- Database password stored as a Parameter Store SecureString.
- IAM policy scoped to `/dc-intern/prod/*` read actions.
- Public health endpoint returning `200`; all four CRUD endpoints live; admin
  static files served.

**Screenshots to capture for the internship report**

1. The deployed app in a browser with a completed skill gap analysis.
2. Browser devtools showing API calls to `/api/...` on the same origin — no CORS.
3. `systemctl status dc-intern-backend` showing `active (running)`.
4. `manage.py check_database` reporting `postgresql` and `OK`.
5. The RDS console showing "Publicly accessible: No".
6. The EC2 security group showing a single inbound rule.
7. `manage.py test` reporting 57 passing tests.

**Not evidence, stated plainly:** Amazon Bedrock has never been called from this
project, and the frontend deployment script has not yet been executed on the
instance. Both are implemented and locally verified; neither has a production
result to show.

---

## Week 4 status

| Deliverable | Status |
|---|---|
| AWS account safety (MFA, budget alert, CLI profile) | Complete |
| First AI feature — Skill Gap Analysis | Complete |
| Environment-driven configuration, no hard-coded secrets | Complete |
| Private Amazon RDS PostgreSQL | Complete |
| Django deployed to EC2 with Gunicorn, Nginx, systemd | Complete and verified |
| React frontend production build and deployment files | Complete; not yet run on the instance |
| Amazon Bedrock integration | Implemented and tested against a mocked client; not enabled |
| Week 4 documentation | Complete |
| TLS, authentication, rate limiting, CloudWatch logs | Week 5 |

## Next week (Week 5)

1. Run the frontend deployment on the instance and capture the evidence.
2. Authentication, then rate limiting on the AI endpoint.
3. TLS, then `USE_HTTPS=True`.
4. Enable Bedrock with a scoped IAM permission, test with an invented profile,
   and record the first real response.
5. Ship logs to CloudWatch.
