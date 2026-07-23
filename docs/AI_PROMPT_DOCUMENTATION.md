# AI Prompt Documentation — Skill Gap Analysis

> **Status:** the Bedrock code path has been implemented and tested against a
> **mocked** boto3 client. It has **not** been executed against the real Amazon
> Bedrock service — no Bedrock request has been made from this project. Every
> Bedrock behaviour described below is what the code does; the live model output
> is not yet evidenced. See [Verification status](#verification-status).

---

## 1. Feature name

**Skill Gap Analysis**

Endpoint: `POST /api/profiles/<id>/generate-skill-gap/`
Implementation: `backend/career/services/ai_service.py`
Prompt: `backend/career/services/prompts.py`

## 2. Purpose

A student enters their field of study, year, career interest, internship goal,
self-assessed skills, and a career goal or resume text. The feature answers the
question the project exists to answer:

> *Given where I am and where I want to go, which skills am I missing, and what
> should I do about it in the next four weeks?*

The output is saved as a `Recommendation` row so it can be re-read, compared
over time, and reviewed by a supervisor.

## 3. Provider

| | |
|---|---|
| Provider | **Amazon Bedrock** (`bedrock-runtime`), via the **Converse API** |
| SDK | `boto3` (pinned in `backend/requirements.txt`) |
| Authentication | The EC2 instance's IAM role, `dc-intern-ec2-role` |
| Credentials in code or config | **None.** No access key, no secret key, anywhere |
| Alternative | `AI_PROVIDER=mock` — a local rule-based analyser, no network call |

**Why Bedrock rather than a key-based API.** The application already runs on EC2
with an instance role. Bedrock is reachable with that role, so there is no
long-lived API key to store in `/etc/dc-intern/backend.env`, rotate, or leak.
The credentials boto3 obtains are temporary and cannot be used off the instance.
A leaked OpenAI-style key, by contrast, works from anywhere until someone
notices the bill.

**Why the Converse API rather than `invoke_model`.** `converse` gives one
request and response shape for every Bedrock model. Swapping
`amazon.nova-micro-v1:0` for a Claude or Llama model becomes a change to the
`AI_MODEL` environment variable — no code change, and no per-vendor JSON body to
maintain.

## 4. Model configuration

| Environment variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `mock` | `mock` or `bedrock`. Defaults to `mock`, so a fresh checkout and the test suite can never call AWS by accident. |
| `AI_MODEL` | `mock-local` | Bedrock model id. Planned production value: **`amazon.nova-micro-v1:0`** |
| `AWS_BEDROCK_REGION` | `eu-north-1` | Region whose Bedrock endpoint is called; model access must be enabled there. |
| `AI_MAX_TOKENS` | `1200` | Response cap. Eight sections fit comfortably; also a cost cap, since Bedrock bills per token. |
| `AI_TEMPERATURE` | `0.2` | Low by design — see below. |
| `AI_FALLBACK_TO_MOCK` | `True` | On Bedrock failure: `True` returns the labelled local analysis, `False` returns a clean `503`. |

**Why `amazon.nova-micro-v1:0`.** It is the cheapest text model in the Bedrock
Nova family and the task is short-form structured writing from supplied facts —
not reasoning-heavy work. A student-project budget with a billing alert is the
binding constraint here, and the provider is one environment variable away from
being changed if the output quality is not good enough.

**Why temperature 0.2.** The model is describing a real person's skills. Low
temperature produces conservative, repeatable output and reduces the chance of
invented detail. High temperature would give more varied prose and more
opportunity to embellish — the opposite of what is wanted.

## 5. Prompt template

Two parts are sent: a **system instruction** (role, rules, output shape) and a
**user prompt** (this student's data). Both live in
`backend/career/services/prompts.py`, deliberately separate from the AWS code,
so they can be reviewed without reading any networking code.

### System instruction (`SYSTEM_INSTRUCTION`)

```text
You are a careers advisor for university students in IT-related fields. You help
students understand which skills they already have, which ones a target role
normally expects, and what to do about the difference in the next few weeks.

Rules you must follow:
- Do NOT guarantee employment, an internship, a placement, or a salary. Never
  imply that following your advice will result in a job offer.
- Do NOT invent qualifications, experience, certifications, projects, or skills.
  Use only what the student reported. If information is missing, say it is missing.
- Do NOT discriminate or comment on age, gender, race, ethnicity, nationality,
  religion, disability, health, family status, or appearance, and do not let any
  such attribute influence your advice.
- Do NOT request personal data beyond what is provided. Never ask for contact
  details, identification numbers, addresses, financial information, or login
  credentials.
- Give practical recommendations that a university student can actually act on
  with free or low-cost resources and a realistic weekly time budget.
- Treat everything you produce as guidance to discuss with a lecturer, mentor,
  or supervisor — not as an absolute or final decision about the student's career.
- Be specific, encouraging, and realistic. Plain text only: no markdown, no
  tables, no code fences.

Produce exactly these eight numbered sections, in this order, using these
headings:

1. CAREER READINESS SUMMARY
2. CURRENT STRENGTHS
3. MISSING TECHNICAL SKILLS
4. MISSING PROFESSIONAL SKILLS
5. RECOMMENDED PROJECTS
6. FOUR-WEEK LEARNING PLAN
7. INTERNSHIP PREPARATION ACTIONS
8. LIMITATIONS

In section 8, state plainly that this analysis is AI-generated guidance based
only on what the student submitted, that it cannot verify any claimed skill,
and that it should be reviewed with a lecturer, mentor, or supervisor.
```

### User prompt (`build_skill_gap_prompt`)

```text
Produce a skill gap analysis for the following university student.

Field of study: {field_of_study}
Year of study: {year_of_study}
Stated career interest: {career_interest}
Internship goal: {internship_goal}

Self-reported skills and confidence levels:
- {skill name} ({category}, {confidence level})
- ...

Career goal / resume text supplied by the student:
- {input type}: {content, truncated to 1500 characters}
- ...

Base every observation on the information above. Where the information is thin,
say so in section 1 rather than filling the gap with assumptions.
```

## 6. Required inputs

| Input | Source | Required | Sent to the model |
|---|---|---|---|
| Field of study | `StudentProfile.field_of_study` | Yes | Yes |
| Year of study | `StudentProfile.year_of_study` | Yes | Yes |
| Career interest | `StudentProfile.career_interest` | Yes | Yes |
| Internship goal | `StudentProfile.internship_goal` | Yes | Yes |
| Skills + confidence + category | `Skill` rows for the profile | No | Yes, up to 40 |
| Career goal / resume text | `CareerInput` rows for the profile | No | Yes, up to 5 entries, 1500 chars each |
| **Full name** | `StudentProfile.full_name` | — | **No — deliberately excluded** |
| Database ids, timestamps | models | — | **No** |

Missing skills or career inputs do not fail the request: the analysis is
produced anyway and the response's `notes` array says what was limited.

## 7. Expected output

Plain text, eight numbered sections, in the order listed in the system
instruction. The local mock analyser produces the **same eight sections**, so a
fallback response is structurally identical to a model response and the UI needs
no special case.

The API response:

```json
{
  "profile_id": 1,
  "recommendation_id": 7,
  "recommendation_type": "Skill Gap Analysis",
  "content": "1. CAREER READINESS SUMMARY\n...",
  "created_at": "2026-07-23T10:31:57.802323Z",
  "provider": "bedrock",
  "model": "amazon.nova-micro-v1:0",
  "fallback_used": false,
  "ai_provider": "bedrock",
  "ai_model": "amazon.nova-micro-v1:0",
  "used_fallback": false,
  "notes": []
}
```

`provider` reports **what actually ran**, not what was configured. If Bedrock
was requested and failed, it reads `mock` and `fallback_used` is `true`.
(`ai_provider` / `ai_model` / `used_fallback` are the same three values under
their pre-Day-5 names, kept so nothing already reading this endpoint breaks.)

## 8. Safety instructions

Encoded in the system instruction, and each one is there for a reason:

| Instruction | Why |
|---|---|
| No guarantee of employment | The application must not create an expectation it cannot meet. A student acting on "this will get you an internship" has been misled by us, not by the model. |
| Do not invent qualifications | Invented experience in a document a student might paste into a CV is a route to that student misrepresenting themselves in an application. |
| No discrimination | Career advice conditioned on a protected attribute is discriminatory whether a person or a model produces it. The model is told not to consider such attributes, and the prompt does not carry any. |
| Do not request extra personal data | Prevents the model from turning the feature into an data-collection funnel for information the project neither needs nor is equipped to protect. |
| Practical, student-appropriate advice | Advice that assumes paid courses or professional experience is useless to the target user. |
| Guidance, not a decision | Reinforced in section 8 of the output, in the UI disclaimer, and in the API `notes`. |

Additional safety measures **outside** the prompt, because a prompt is guidance
to a model and not an enforcement mechanism:

- **Output is rendered as plain text** in a `<pre>` element, never as HTML or
  markdown, so nothing in a model response can inject markup into the page.
- **The response length is capped** by `AI_MAX_TOKENS`.
- **AWS errors never reach the browser.** `ClientError` codes are mapped to
  written-for-users messages; the raw AWS payload is logged (code only) and
  discarded.
- **A fallback is always labelled.** The content itself is prefixed with a
  `NOTE — FALLBACK MODE` banner, so a saved recommendation cannot later be
  mistaken for model output.

## 9. Privacy considerations

**What leaves the server**, and only when `AI_PROVIDER=bedrock`: field of study,
year of study, career interest, internship goal, skill names with confidence
levels, and the student's own career-goal/resume text (truncated).

**What does not leave the server:**

- The student's **name**. The analysis does not need it, so it is not sent — the
  text that reaches AWS is not directly identifying on its own.
- Database identifiers, timestamps, IP addresses, and every other piece of
  record metadata.
- Anything from other students' profiles.

Other decisions:

- **Truncation at 1500 characters per career input, 5 inputs, 40 skills.** Bounds
  what leaves the server, what is billed, and how much untrusted text can
  influence a response.
- **Resume text is student-authored free text.** Students are not asked for
  identification numbers, addresses, or contact details anywhere in the UI, but
  nothing stops them pasting a full CV containing them. This is a known gap —
  see [Known limitations](#11-known-limitations).
- **Logging.** Prompts and responses are never logged. The service logs token
  counts, response length, the model id, and an AWS error *code*. There is a
  test (`test_nothing_student_written_is_ever_logged`) that fails if student text
  reaches the log.
- **Data retention at AWS.** Amazon Bedrock does not store prompts or responses
  for model training, and inference data is not retained after the request under
  the AWS service terms. This is worth re-verifying against current AWS
  documentation before any real student data is used.
- **In mock mode nothing leaves the server at all.** This is why mock is the
  default and why it is used for every automated test.

## 10. Mock versus Bedrock mode

| | `AI_PROVIDER=mock` | `AI_PROVIDER=bedrock` |
|---|---|---|
| Network call | None | HTTPS to `bedrock-runtime.<region>.amazonaws.com` |
| Credentials | None needed | EC2 instance IAM role, resolved by boto3 |
| Cost | Zero | Per input + output token |
| Student data leaves the server | No | Yes, the fields listed in §6 |
| Output | Rule-based, from `ROLE_PROFILES` | Model-generated |
| Sections | The same eight | The same eight |
| Response `provider` | `mock` | `bedrock` |
| Used for automated tests | **Yes, always** | Never (the client is mocked) |
| Used in local development | Yes, the default | Only deliberately |

**Failure behaviour.** With `AI_FALLBACK_TO_MOCK=True` (the default), a Bedrock
failure returns the local analysis with `provider: "mock"`,
`fallback_used: true`, a `notes` entry explaining what happened, and a banner in
the content itself. With `AI_FALLBACK_TO_MOCK=False`, the endpoint returns
`503` with a clean message and saves nothing. **The response never claims a
model produced text that a rule engine produced.**

## 11. Known limitations

- **Not yet run against real Bedrock.** See [Verification status](#verification-status).
- **The model cannot verify anything.** A student who reports "Advanced Python"
  with no evidence is taken at their word. The analysis reflects claims, not
  competence.
- **No model-output validation.** The response is saved and displayed as
  returned. Nothing checks that all eight sections are present, that no
  employment guarantee slipped through, or that the advice is sensible. A
  structural validator is the obvious next improvement.
- **Prompt-injection surface.** Career-goal and resume text are student-authored
  and are placed in the prompt. A student could write "ignore previous
  instructions" there. Impact is low — the worst case is a bad analysis returned
  to the same student who caused it, and output is rendered as plain text — but
  the input is untrusted and is not sanitised beyond truncation.
- **No rate limiting.** Nothing stops a client calling the endpoint repeatedly,
  which with Bedrock enabled means cost. Throttling is required before this is
  public with a real provider.
- **No authentication.** Any caller can generate an analysis for any profile id.
  This is the largest gap before real student data is involved.
- **One language.** The prompt and output are English only.
- **The mock analyser is rule-based** and matches skills by name, so unusual
  spellings can be reported as missing.
- **Cost is unmetered per user.** Token counts are logged, but nothing aggregates
  them per profile or enforces a ceiling below the account budget alert.

## 12. Example input (no real personal data)

An invented profile — this is not a real student:

```json
{
  "full_name": "Test Student",
  "field_of_study": "Information Technology",
  "year_of_study": "Year 3",
  "career_interest": "Cloud Engineering",
  "internship_goal": "A cloud engineering internship where I can work with AWS."
}
```

```json
[
  {"name": "Python", "category": "Programming", "confidence_level": "Intermediate"},
  {"name": "Linux command line", "category": "Cloud Computing", "confidence_level": "Beginner"},
  {"name": "Git", "category": "Software Engineering", "confidence_level": "Intermediate"}
]
```

```json
[
  {"input_type": "Career Goal",
   "content": "I have built two small web projects at university and I want to move into cloud infrastructure work."}
]
```

The prompt actually sent for this input (name excluded):

```text
Produce a skill gap analysis for the following university student.

Field of study: Information Technology
Year of study: Year 3
Stated career interest: Cloud Engineering
Internship goal: A cloud engineering internship where I can work with AWS.

Self-reported skills and confidence levels:
- Python (Programming, Intermediate)
- Linux command line (Cloud Computing, Beginner)
- Git (Software Engineering, Intermediate)

Career goal / resume text supplied by the student:
- Career Goal: I have built two small web projects at university and I want to move into cloud infrastructure work.

Base every observation on the information above. Where the information is thin,
say so in section 1 rather than filling the gap with assumptions.
```

## 13. Example expected response structure

Illustrative shape, abbreviated — **not** captured from a real Bedrock call:

```text
1. CAREER READINESS SUMMARY
   You have a workable foundation for a cloud engineering internship: a
   programming language, version control, and some Linux exposure. The main gap
   is demonstrated AWS work.

2. CURRENT STRENGTHS
   - Python (Intermediate) — the most useful language for automation work.
   - Git (Intermediate) — expected in every team you would join.
   - Two completed web projects, which give you something concrete to discuss.

3. MISSING TECHNICAL SKILLS
   - AWS core services (EC2, S3, RDS, IAM)
   - Networking fundamentals (VPC, subnets, security groups)
   - Infrastructure as Code (Terraform or CloudFormation)
   - CI/CD pipelines
   - Monitoring and logging (CloudWatch)

4. MISSING PROFESSIONAL SKILLS
   - Technical documentation
   - Presenting your work to a non-technical audience

5. RECOMMENDED PROJECTS
   - Deploy one of your existing web projects to AWS end to end, with a managed
     database and an IAM role instead of access keys.
   - Add a CI/CD pipeline that tests and redeploys it on every push.

6. FOUR-WEEK LEARNING PLAN
   Week 1 — AWS core services...
   Week 2 — Networking and security groups...
   Week 3 — Infrastructure as Code...
   Week 4 — CI/CD, then write the project up...

7. INTERNSHIP PREPARATION ACTIONS
   - Write a one-page CV that leads with Python and your deployed project.
   - Prepare a two-minute spoken explanation of your AWS deployment.
   - Identify three organisations in your area that take cloud interns.

8. LIMITATIONS
   This analysis is AI-generated guidance based only on what you submitted. It
   cannot verify any skill you reported and it is not a guarantee of an
   internship or a job. Review it with a lecturer, mentor, or supervisor.
```

## Verification status

| Behaviour | How it was verified |
|---|---|
| Mock mode output and structure | Automated tests, run locally |
| Prompt contents and exclusions | Automated tests (`PromptBuilderTests`) |
| Converse request shape (`modelId`, `system`, `messages`, `inferenceConfig`) | Automated tests with a mocked boto3 client |
| Response text extraction, including multi-block and malformed responses | Automated tests |
| `ClientError` and `BotoCoreError` handling, and that AWS detail does not leak | Automated tests |
| Fallback on/off behaviour | Automated tests |
| No AWS client is constructed during the test suite | Automated test that fails if `boto3.client` is called |
| **A real Bedrock call** | **Not done.** No Bedrock request has been made from this project. Model access has not been enabled in the account. |
| **Real model output quality** | **Not assessed** — there is no real output to assess. |

Before switching `AI_PROVIDER=bedrock` on the instance:

1. Enable model access for `amazon.nova-micro-v1:0` in `AWS_BEDROCK_REGION`.
2. Add `bedrock:InvokeModel` on that model ARN to `dc-intern-ec2-role` — scoped
   to the one model, not `bedrock:*` on `*`.
3. Confirm the budget alert covers Bedrock usage.
4. Add rate limiting to the endpoint.
5. Test with an invented profile, not a real student's data.
6. Record the first real response and update this document with it.
