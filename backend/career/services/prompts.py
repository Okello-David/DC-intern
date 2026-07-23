"""Prompt construction for the Skill Gap Analysis feature.

Kept in its own module, separate from the provider code in ``ai_service.py``,
for three reasons:

* **Reviewability.** A supervisor can read exactly what is sent to an external
  model without reading any AWS or networking code.
* **Privacy.** This is the single place that decides *which* student data leaves
  the server. If a field is not assembled here, it is not sent — see
  ``build_skill_gap_prompt`` for the deliberate exclusions.
* **Reuse.** The same prompt is used by every provider, so switching providers
  cannot silently change what students are asked about or what the model is told
  not to do.
"""

# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------
# Free-text career input is student-authored and unbounded. Truncating it here
# bounds three things at once: what leaves the server, what the model is billed
# for, and how much untrusted text can influence the response.

MAX_CAREER_INPUT_CHARS = 1500
MAX_CAREER_INPUTS = 5
MAX_SKILLS = 40


# --------------------------------------------------------------------------
# System instruction
# --------------------------------------------------------------------------
# Sent as the model's system prompt: role, hard rules, and output shape. These
# rules are stated as prohibitions because that is what a model follows most
# reliably, and they are documented in docs/AI_PROMPT_DOCUMENTATION.md.

SYSTEM_INSTRUCTION = """\
You are a careers advisor for university students in IT-related fields. You help \
students understand which skills they already have, which ones a target role \
normally expects, and what to do about the difference in the next few weeks.

Rules you must follow:
- Do NOT guarantee employment, an internship, a placement, or a salary. Never \
imply that following your advice will result in a job offer.
- Do NOT invent qualifications, experience, certifications, projects, or skills. \
Use only what the student reported. If information is missing, say it is missing.
- Do NOT discriminate or comment on age, gender, race, ethnicity, nationality, \
religion, disability, health, family status, or appearance, and do not let any \
such attribute influence your advice.
- Do NOT request personal data beyond what is provided. Never ask for contact \
details, identification numbers, addresses, financial information, or login \
credentials.
- Give practical recommendations that a university student can actually act on \
with free or low-cost resources and a realistic weekly time budget.
- Treat everything you produce as guidance to discuss with a lecturer, mentor, \
or supervisor — not as an absolute or final decision about the student's career.
- Be specific, encouraging, and realistic. Plain text only: no markdown, no \
tables, no code fences.

Produce exactly these eight numbered sections, in this order, using these \
headings:

1. CAREER READINESS SUMMARY
2. CURRENT STRENGTHS
3. MISSING TECHNICAL SKILLS
4. MISSING PROFESSIONAL SKILLS
5. RECOMMENDED PROJECTS
6. FOUR-WEEK LEARNING PLAN
7. INTERNSHIP PREPARATION ACTIONS
8. LIMITATIONS

In section 8, state plainly that this analysis is AI-generated guidance based \
only on what the student submitted, that it cannot verify any claimed skill, \
and that it should be reviewed with a lecturer, mentor, or supervisor.
"""


def _truncate(text, limit):
    """Trim free text to `limit` characters, marking that it was shortened."""
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + ' […truncated]'


def summarise_skills(skills):
    """Render self-reported skills as `- name (category, confidence)` lines."""
    lines = [
        f'- {skill.name.strip()} ({skill.category}, {skill.confidence_level})'
        for skill in list(skills)[:MAX_SKILLS]
        if (skill.name or '').strip()
    ]
    return '\n'.join(lines) if lines else '- (none reported)'


def summarise_career_inputs(career_inputs):
    """Render career/resume text, truncated, as labelled blocks."""
    lines = [
        f'- {entry.input_type}: {_truncate(entry.content, MAX_CAREER_INPUT_CHARS)}'
        for entry in list(career_inputs)[:MAX_CAREER_INPUTS]
        if (entry.content or '').strip()
    ]
    return '\n'.join(lines) if lines else '- (none provided)'


def build_skill_gap_prompt(student_profile, skills, career_inputs):
    """Build the user-turn prompt for a Skill Gap Analysis.

    Only the fields needed to reason about a skill gap are included:
    field of study, year of study, career interest, internship goal, the
    self-reported skills with their confidence levels, and the student's own
    career-goal / resume text.

    Deliberately excluded, because the analysis does not need them:

    * the student's **name** — the model has no use for it, and leaving it out
      means the text sent to AWS is not directly identifying;
    * database identifiers, timestamps, and any other record metadata;
    * anything not typed by the student for this purpose.
    """
    return (
        'Produce a skill gap analysis for the following university student.\n\n'
        f'Field of study: {student_profile.field_of_study}\n'
        f'Year of study: {student_profile.year_of_study}\n'
        f'Stated career interest: {student_profile.career_interest}\n'
        f'Internship goal: {(student_profile.internship_goal or "").strip() or "(not stated)"}\n\n'
        'Self-reported skills and confidence levels:\n'
        f'{summarise_skills(skills)}\n\n'
        'Career goal / resume text supplied by the student:\n'
        f'{summarise_career_inputs(career_inputs)}\n\n'
        'Base every observation on the information above. Where the information '
        'is thin, say so in section 1 rather than filling the gap with '
        'assumptions.'
    )
