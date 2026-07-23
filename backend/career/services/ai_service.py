"""AI service layer — the only place in the project that talks to an AI provider.

Design rules for this module:

* It runs **server-side only**. The React frontend calls the Django API; Django
  calls the AI provider. No credential of any kind ever leaves the server.
* It is **provider-agnostic**. `AI_PROVIDER` selects the implementation:

      AI_PROVIDER=mock      no network call at all; a local rule-based analysis
      AI_PROVIDER=bedrock   Amazon Bedrock Runtime, via the Converse API

* It always **degrades honestly**. When Bedrock fails and
  `AI_FALLBACK_TO_MOCK=True`, the local analysis is returned *labelled as a
  fallback* — the caller is told which provider actually produced the text, so
  a mock response is never presented as a model response.
* It **never** handles AWS access keys. On EC2, boto3 picks up credentials from
  the instance's IAM role automatically; locally it uses whatever profile the
  developer has already configured. There is no key in this file, in settings,
  or in any environment variable this project defines.
"""

import logging

from django.conf import settings

from .prompts import SYSTEM_INSTRUCTION, build_skill_gap_prompt

logger = logging.getLogger(__name__)

# Providers this module knows how to call. Anything else is a configuration
# error, handled like any other provider failure.
SUPPORTED_PROVIDERS = ('mock', 'bedrock')


class AIServiceError(Exception):
    """Raised when an analysis cannot be produced.

    The message is written to be safe to show a student: it names what failed in
    plain language and never carries an AWS error payload, a request id, a model
    identifier the user cannot act on, or anything derived from a credential.
    Views catch this and return a clean JSON error instead of a traceback.
    """


# --------------------------------------------------------------------------
# Target-role knowledge used by the local (mock) analysis
# --------------------------------------------------------------------------
# Each entry maps keywords that may appear in a student's stated career
# interest to the skills and projects normally expected for that role. This is
# deliberately small and readable: it is a transparent stand-in for a real AI
# response, not an attempt to imitate one.

ROLE_PROFILES = [
    {
        'keywords': ('backend', 'back end', 'back-end', 'api', 'server'),
        'role': 'Backend Engineer',
        'technical_skills': [
            'Python', 'Django or Node.js', 'REST API design', 'SQL and relational databases',
            'Git and GitHub', 'Testing (unit and integration)', 'Docker basics',
        ],
        'projects': [
            'A REST API with authentication, database models, and tests',
            'A small service that integrates a third-party API and caches its responses',
        ],
    },
    {
        'keywords': ('frontend', 'front end', 'front-end', 'ui', 'ux', 'web design'),
        'role': 'Frontend Engineer',
        'technical_skills': [
            'HTML and CSS', 'JavaScript (ES6+)', 'React', 'State management',
            'Responsive design and accessibility', 'Git and GitHub', 'Consuming REST APIs',
        ],
        'projects': [
            'A responsive multi-page React app that consumes a public API',
            'An accessible dashboard with charts, filtering, and loading/error states',
        ],
    },
    {
        'keywords': ('full stack', 'fullstack', 'full-stack', 'software engineer', 'web develop'),
        'role': 'Full-Stack Engineer',
        'technical_skills': [
            'JavaScript (ES6+)', 'React', 'Python', 'Django or Node.js', 'REST API design',
            'SQL and relational databases', 'Git and GitHub', 'Deployment basics',
        ],
        'projects': [
            'A full-stack CRUD application with a React frontend and a REST API backend',
            'A deployed portfolio project with a database, hosted end to end',
        ],
    },
    {
        'keywords': ('cloud', 'devops', 'aws', 'azure', 'infrastructure', 'sre', 'platform'),
        'role': 'Cloud / DevOps Engineer',
        'technical_skills': [
            'Linux command line', 'AWS core services (EC2, S3, RDS, IAM)', 'Networking basics',
            'Infrastructure as Code (Terraform or CloudFormation)', 'Docker',
            'CI/CD pipelines', 'Monitoring and logging (CloudWatch)', 'Git and GitHub',
        ],
        'projects': [
            'Deploy a web application to AWS EC2 with a managed RDS database and IAM roles',
            'A CI/CD pipeline that tests and deploys an app automatically on every push',
        ],
    },
    {
        'keywords': (
            'data', 'analyst', 'analytics', 'machine learning', 'artificial intelligence',
        ),
        'role': 'Data / AI Practitioner',
        'technical_skills': [
            'Python', 'SQL', 'Pandas and NumPy', 'Data visualisation', 'Statistics fundamentals',
            'Machine learning basics (scikit-learn)', 'Git and GitHub',
        ],
        'projects': [
            'An end-to-end analysis of a public dataset, from cleaning to visual report',
            'A small predictive model exposed through an API endpoint',
        ],
    },
    {
        'keywords': ('security', 'cyber', 'pentest', 'soc', 'forensic'),
        'role': 'Cybersecurity Analyst',
        'technical_skills': [
            'Networking fundamentals (TCP/IP, DNS, HTTP)', 'Linux command line',
            'Web application security (OWASP Top 10)', 'Python scripting',
            'Security tooling (Wireshark, Nmap, Burp Suite)', 'Log analysis and monitoring',
            'Git and GitHub',
        ],
        'projects': [
            'A documented security review of your own web application against the OWASP Top 10',
            'A home lab with a vulnerable VM, plus written findings and remediation notes',
        ],
    },
    {
        'keywords': ('mobile', 'android', 'ios', 'flutter', 'react native'),
        'role': 'Mobile Developer',
        'technical_skills': [
            'A mobile framework (Flutter, React Native, or Kotlin)', 'UI layout and navigation',
            'Consuming REST APIs', 'Local storage and offline handling', 'Git and GitHub',
            'App store build and release basics',
        ],
        'projects': [
            'A mobile app that reads from and writes to a REST API',
            'An offline-first app that syncs data when connectivity returns',
        ],
    },
]

DEFAULT_ROLE_PROFILE = {
    'role': 'IT Graduate / Software Intern',
    'technical_skills': [
        'A primary programming language (Python, Java, or JavaScript)',
        'Git and GitHub', 'SQL and relational databases', 'REST API basics',
        'Linux command line', 'Testing fundamentals',
    ],
    'projects': [
        'A small application that stores data in a database and is published on GitHub',
        'A documented contribution to an open-source project or a team project',
    ],
}

PROFESSIONAL_SKILLS = [
    'Written and verbal communication',
    'Teamwork and collaboration',
    'Problem solving and debugging discipline',
    'Time management and meeting deadlines',
    'Technical documentation and clear README writing',
    'Interview preparation and self-presentation',
]

CONFIDENCE_ORDER = {'Advanced': 0, 'Intermediate': 1, 'Beginner': 2}

LIMITATIONS_NOTE = (
    'This analysis is generated from the profile, skills, and career inputs the '
    'student submitted. It is guidance, not a guarantee of employability, and it '
    'cannot verify claimed skills. It should be reviewed with a lecturer, mentor, '
    'or supervisor before acting on it.'
)

MOCK_LIMITATIONS_NOTE = (
    'This response was produced by the local rule-based analyser on this server, not '
    'by an AI model, so no student data left the server and no API cost was incurred. '
    'Being rule-based, it reasons only about the skills it knows to look for. It uses '
    'the same eight sections as the Amazon Bedrock response, so the two are directly '
    'comparable. ' + LIMITATIONS_NOTE
)


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def generate_skill_gap_analysis(student_profile, skills, career_inputs):
    """Produce a skill-gap analysis for one student.

    Args:
        student_profile: a ``StudentProfile`` instance.
        skills: an iterable of ``Skill`` instances (may be empty).
        career_inputs: an iterable of ``CareerInput`` instances (may be empty).

    Returns:
        dict with keys:

        ``content``           the readable analysis text
        ``provider``          who actually produced it (``mock`` or ``bedrock``)
        ``model``             the model identifier that actually produced it
        ``used_fallback``     True when the local analyser produced the text
        ``requested_provider``what ``AI_PROVIDER`` asked for
        ``fallback_reason``   plain-language reason, or None

        ``provider`` reports what *ran*, not what was configured. If Bedrock was
        requested and failed, this says ``mock``.

    Raises:
        AIServiceError: the configured provider failed and
            ``AI_FALLBACK_TO_MOCK`` is False.
    """
    skills = list(skills or [])
    career_inputs = list(career_inputs or [])

    provider = (getattr(settings, 'AI_PROVIDER', 'mock') or 'mock').strip().lower()
    model = (getattr(settings, 'AI_MODEL', '') or 'mock-local').strip()
    fallback_allowed = bool(getattr(settings, 'AI_FALLBACK_TO_MOCK', True))

    if provider == 'mock':
        return _mock_result(student_profile, skills, career_inputs)

    try:
        if provider == 'bedrock':
            content = generate_with_bedrock(
                build_skill_gap_prompt(student_profile, skills, career_inputs)
            )
        else:
            raise AIServiceError(
                f'AI_PROVIDER is set to an unsupported value. Supported values are: '
                f'{", ".join(SUPPORTED_PROVIDERS)}.'
            )
    except AIServiceError as exc:
        if not fallback_allowed:
            raise
        # The reason is deliberately the AIServiceError message, which is
        # already scrubbed of AWS detail — see the class docstring.
        logger.warning(
            'AI provider %r unavailable; returning the local fallback analysis. Reason: %s',
            provider, exc,
        )
        return _mock_result(
            student_profile, skills, career_inputs,
            requested_provider=provider,
            fallback_reason=str(exc),
        )

    return {
        'content': content,
        'provider': provider,
        'model': model,
        'used_fallback': False,
        'requested_provider': provider,
        'fallback_reason': None,
    }


def _mock_result(student_profile, skills, career_inputs,
                 requested_provider='mock', fallback_reason=None):
    """Build the local-analyser result, labelled honestly.

    When this is a *fallback* (a real provider was asked for and could not be
    used), the banner at the top of the content says so. A reader of the saved
    recommendation must never have to guess whether a model was involved.
    """
    content = build_local_analysis(student_profile, skills, career_inputs)

    if fallback_reason:
        content = (
            'NOTE — FALLBACK MODE: the configured AI provider '
            f'({requested_provider}) could not be used, so this analysis was '
            'produced by the local rule-based analyser on this server. It is NOT '
            'AI-model output.\n\n'
        ) + content

    return {
        'content': content,
        'provider': 'mock',
        'model': 'mock-local',
        'used_fallback': True,
        'requested_provider': requested_provider,
        'fallback_reason': fallback_reason,
    }


# --------------------------------------------------------------------------
# Amazon Bedrock provider
# --------------------------------------------------------------------------
# Bedrock was chosen over a key-based provider for one reason above all: on EC2
# it needs no API key. Access is granted by the instance's IAM role, so there is
# no long-lived secret to store in /etc/dc-intern/backend.env, rotate, or leak.

# Bedrock ClientError codes mapped to messages a student can act on. Anything
# unlisted gets the generic message — an unfamiliar AWS error code is exactly
# the case where the raw text must not be forwarded to a browser.
_BEDROCK_ERROR_MESSAGES = {
    'AccessDeniedException':
        'The AI service is not authorised for this application yet. This is a '
        'server configuration issue, not a problem with your profile.',
    'ResourceNotFoundException':
        'The configured AI model is not available in this region. This is a '
        'server configuration issue.',
    'ValidationException':
        'The AI service rejected the request. Please try again; if it keeps '
        'happening, report it.',
    'ThrottlingException':
        'The AI service is busy right now. Please wait a moment and try again.',
    'ServiceQuotaExceededException':
        'The AI service usage limit for this application has been reached. '
        'Please try again later.',
    'ModelTimeoutException':
        'The AI service took too long to respond. Please try again.',
    'ModelNotReadyException':
        'The AI model is warming up. Please try again in a moment.',
}

_BEDROCK_GENERIC_ERROR = (
    'The AI service could not be reached. Please try again later.'
)


def _bedrock_client():
    """Create a Bedrock Runtime client.

    boto3 resolves credentials itself, in its standard order — on EC2 that is
    the instance's IAM role (``dc-intern-ec2-role``) via the instance metadata
    service. **No access key is passed here, and none should ever be.**

    boto3 is imported inside the function so that a `mock`-mode deployment (and
    the test suite) never requires the SDK to be installed, and so that a
    missing dependency surfaces as a clean AIServiceError instead of an import
    error at startup.

    Tests patch this function, which is what keeps a real AWS call impossible in
    the automated suite.
    """
    region = (getattr(settings, 'AWS_BEDROCK_REGION', '') or '').strip()
    if not region:
        raise AIServiceError(
            'The AI service is not fully configured on the server '
            '(no Bedrock region set).'
        )

    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise AIServiceError(
            'The AI service is unavailable because a server dependency is missing.'
        ) from exc

    return boto3.client('bedrock-runtime', region_name=region)


def generate_with_bedrock(prompt, system_instruction=SYSTEM_INSTRUCTION):
    """Send one Converse request to Amazon Bedrock and return the text.

    The Converse API is used rather than `invoke_model` because it gives one
    request/response shape across every Bedrock model: swapping
    `amazon.nova-micro-v1:0` for a Claude or Llama model becomes a change to the
    `AI_MODEL` environment variable, with no code change and no per-vendor JSON
    body to maintain.

    Raises:
        AIServiceError: for every failure mode, with a message that is safe to
            show a user. AWS error details are logged, never returned.
    """
    try:
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        # Same treatment as a missing boto3: a clean provider failure, which the
        # caller can fall back from, rather than a 500 from an import error.
        raise AIServiceError(
            'The AI service is unavailable because a server dependency is missing.'
        ) from exc

    model_id = (getattr(settings, 'AI_MODEL', '') or '').strip()
    if not model_id:
        raise AIServiceError(
            'The AI service is not fully configured on the server (no model set).'
        )

    client = _bedrock_client()

    try:
        response = client.converse(
            modelId=model_id,
            system=[{'text': system_instruction}],
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={
                'maxTokens': int(getattr(settings, 'AI_MAX_TOKENS', 1200)),
                # Low by design: this is factual guidance about a real person's
                # skills, so predictable, conservative output beats creative
                # output, and it reduces the chance of invented detail.
                'temperature': float(getattr(settings, 'AI_TEMPERATURE', 0.2)),
            },
        )
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code', 'Unknown')
        # Log the error CODE only. The full response can echo request content,
        # and the prompt contains the student's own career text.
        logger.error('Bedrock converse failed for model %s with code %s.', model_id, code)
        raise AIServiceError(_BEDROCK_ERROR_MESSAGES.get(code, _BEDROCK_GENERIC_ERROR)) from exc
    except BotoCoreError as exc:
        # Credential resolution, endpoint, connection, and timeout problems.
        logger.error('Bedrock call failed: %s', type(exc).__name__)
        raise AIServiceError(_BEDROCK_GENERIC_ERROR) from exc
    except Exception as exc:  # anything unforeseen in the SDK
        logger.exception('Unexpected error calling Bedrock (model %s).', model_id)
        raise AIServiceError(_BEDROCK_GENERIC_ERROR) from exc

    return _extract_bedrock_text(response)


def _extract_bedrock_text(response):
    """Pull the assistant's text out of a Converse response, defensively.

    A Converse response looks like::

        {'output': {'message': {'role': 'assistant',
                                'content': [{'text': '...'}]}},
         'stopReason': 'end_turn', 'usage': {...}}

    but `content` can hold several blocks, and non-text blocks (tool use,
    reasoning) may appear. Everything is read with `.get()` so a shape change in
    the API surfaces as a clean error rather than a KeyError traceback.
    """
    blocks = (
        (response or {})
        .get('output', {})
        .get('message', {})
        .get('content', [])
    )

    text = '\n'.join(
        block['text'].strip()
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get('text'), str) and block['text'].strip()
    ).strip()

    if not text:
        logger.error(
            'Bedrock returned no usable text (stopReason=%s).',
            (response or {}).get('stopReason'),
        )
        raise AIServiceError(
            'The AI service returned an empty response. Please try again.'
        )

    if (response or {}).get('stopReason') == 'max_tokens':
        text += (
            '\n\n[The response reached the configured length limit and may be '
            'cut short.]'
        )

    # Usage is safe to log — token counts, no content.
    usage = (response or {}).get('usage', {})
    logger.info(
        'Bedrock analysis generated (input_tokens=%s, output_tokens=%s, chars=%s).',
        usage.get('inputTokens'), usage.get('outputTokens'), len(text),
    )

    return text


# --------------------------------------------------------------------------
# Local (mock) analyser
# --------------------------------------------------------------------------

def _best_role_match(text):
    """Return the role whose keywords match `text` most specifically, or None.

    Scoring by matched keyword length (rather than taking the first hit) keeps
    ambiguous phrases on the right role: "Security Analyst" matches both
    'analyst' and 'security', and the longer, more specific match wins.
    """
    best_profile, best_score = None, 0
    for role_profile in ROLE_PROFILES:
        score = sum(len(kw) for kw in role_profile['keywords'] if kw in text)
        if score > best_score:
            best_profile, best_score = role_profile, score
    return best_profile


def _match_role_profile(career_interest, field_of_study):
    """Pick the closest target role from the student's stated interest.

    The stated career interest is checked first because it is the student's
    actual intent; field of study is only a fallback signal.
    """
    return (
        _best_role_match((career_interest or '').lower())
        or _best_role_match((field_of_study or '').lower())
        or DEFAULT_ROLE_PROFILE
    )


def _covers(skill_names, target):
    """True if any self-reported skill plausibly covers the target skill.

    Matching is deliberately loose in both directions ("React" covers "React",
    "Git" covers "Git and GitHub") but guarded for very short skill names so
    that a skill called "C" or "R" does not appear to cover everything.
    """
    variants = [
        variant.strip().lower().replace('(', ' ').replace(')', ' ').replace(',', ' ')
        for variant in target.split(' or ')
    ]
    for name in skill_names:
        for variant in variants:
            words = variant.split()
            if not words:
                continue
            if len(name) < 3:
                if name in words:
                    return True
                continue
            if name in variant or variant in name:
                return True
            if len(words[0]) > 3 and words[0] in name:
                return True
    return False


def build_local_analysis(student_profile, skills, career_inputs):
    """Build the structured fallback analysis, derived from the student's own data."""
    role_profile = _match_role_profile(
        student_profile.career_interest, student_profile.field_of_study
    )
    target_role = role_profile['role']

    skill_names = [skill.name.strip().lower() for skill in skills if skill.name]
    professional_reported = [s for s in skills if s.category == 'Professional Skills']
    professional_names = [s.name.strip().lower() for s in professional_reported]

    missing_technical = [
        target for target in role_profile['technical_skills'] if not _covers(skill_names, target)
    ]
    missing_professional = [
        target for target in PROFESSIONAL_SKILLS if not _covers(professional_names, target)
    ]

    covered = len(role_profile['technical_skills']) - len(missing_technical)
    total_targets = len(role_profile['technical_skills'])
    coverage = round(covered / total_targets * 100) if total_targets else 0

    strengths = sorted(
        skills,
        key=lambda s: (CONFIDENCE_ORDER.get(s.confidence_level, 3), s.name.lower()),
    )

    lines = []

    # --- 1. Career Readiness Summary -------------------------------------
    lines.append('SKILL GAP ANALYSIS')
    lines.append(f'Student: {student_profile.full_name}')
    lines.append(f'Field of study: {student_profile.field_of_study} | {student_profile.year_of_study}')
    lines.append(f'Stated career interest: {student_profile.career_interest}')
    lines.append(f'Closest target role used for this analysis: {target_role}')
    lines.append('')
    lines.append('1. CAREER READINESS SUMMARY')
    if not skills and not career_inputs:
        lines.append(
            '   No skills and no resume/career input were submitted, so this is a generic '
            f'readiness outline for a {target_role} rather than a personalised analysis.'
        )
        lines.append(
            '   Add your skills and a resume or career goal, then generate the analysis '
            'again for results based on your actual profile.'
        )
    else:
        lines.append(
            f'   You reported {len(skills)} skill(s) and {len(career_inputs)} resume/career '
            f'input(s). Against a typical {target_role} skill set you currently cover about '
            f'{coverage}% ({covered} of {total_targets} core areas).'
        )
        if coverage >= 70:
            lines.append(
                '   You are in a strong position to apply for internships now. Focus the '
                'remaining time on evidence: shipped projects, a clean GitHub profile, and '
                'being able to explain your work out loud.'
            )
        elif coverage >= 40:
            lines.append(
                '   You have a workable foundation. Closing two or three of the gaps below '
                'and completing one substantial project would make you competitive for '
                'internship applications this cycle.'
            )
        else:
            lines.append(
                '   You are early in the journey for this role, which is normal and fixable. '
                'Depth in one or two core skills will move you further than shallow exposure '
                'to many.'
            )
        if not skills:
            lines.append('   Note: no skills were submitted, so strengths could not be assessed.')
        if not career_inputs:
            lines.append(
                '   Note: no resume text or career goal was submitted, so this analysis could '
                'not take your experience or specific ambitions into account.'
            )
    lines.append('')

    # --- 2. Current Strengths ---------------------------------------------
    lines.append('2. CURRENT STRENGTHS')
    if strengths:
        for skill in strengths:
            evidence = f' — evidence: {skill.evidence.strip()}' if skill.evidence.strip() else ''
            lines.append(f'   - {skill.name} ({skill.confidence_level}, {skill.category}){evidence}')
        advanced = [s.name for s in skills if s.confidence_level == 'Advanced']
        if advanced:
            lines.append(
                f'   Lead with {", ".join(advanced)} on your CV — these are your strongest '
                'talking points in an interview.'
            )
        else:
            lines.append(
                '   Nothing is rated Advanced yet. Choose one skill closest to your target role '
                'and deepen it until you can teach it to someone else.'
            )
    else:
        lines.append('   No skills submitted yet, so no strengths could be identified.')
    lines.append('')

    # --- 3. Missing Technical Skills --------------------------------------
    lines.append('3. MISSING TECHNICAL SKILLS')
    if missing_technical:
        lines.append(f'   Commonly expected for a {target_role} but not found in your profile:')
        for item in missing_technical:
            lines.append(f'   - {item}')
    else:
        lines.append(
            f'   Your profile already covers the core technical areas expected for a '
            f'{target_role}. Deepen them and demonstrate them through projects.'
        )
    lines.append('')

    # --- 4. Missing Professional Skills -----------------------------------
    lines.append('4. MISSING PROFESSIONAL SKILLS')
    if missing_professional:
        lines.append('   Not evidenced in your profile — these decide many internship outcomes:')
        for item in missing_professional:
            lines.append(f'   - {item}')
    else:
        lines.append('   You have reported the main professional skills. Keep evidencing them.')
    lines.append('')

    # --- 5. Recommended Projects ------------------------------------------
    lines.append('5. RECOMMENDED PROJECTS')
    for project in role_profile['projects']:
        lines.append(f'   - {project}')
    lines.append(
        '   - A written case study of one project: the problem, your decisions, and what '
        'you would do differently.'
    )
    if student_profile.internship_goal.strip():
        lines.append(
            f'   Tie at least one project to your stated goal: "{student_profile.internship_goal.strip()}"'
        )
    lines.append('')

    # --- 6. Four-Week Learning Plan ---------------------------------------
    lines.append('6. FOUR-WEEK LEARNING PLAN')
    focus = missing_technical or role_profile['technical_skills']
    week_one = focus[0] if focus else 'your strongest existing skill'
    week_two = focus[1] if len(focus) > 1 else week_one
    week_three = focus[2] if len(focus) > 2 else week_two
    lines.append(
        f'   Week 1 — Learn the fundamentals of {week_one}. Follow one structured tutorial end '
        'to end and take notes in your own words.'
    )
    lines.append(
        f'   Week 2 — Apply {week_one} in a small project of your own, then start {week_two}. '
        'Commit your work to GitHub daily, however small.'
    )
    lines.append(
        f'   Week 3 — Extend the project using {week_three}. Add a README, basic tests, and '
        'screenshots so the work is understandable to a reviewer.'
    )
    if missing_professional:
        lines.append(
            f'   Week 4 — Deploy or publish the project, write the case study, and practise '
            f'{missing_professional[0].lower()} by presenting it to a peer or mentor.'
        )
    else:
        lines.append(
            '   Week 4 — Deploy or publish the project, write the case study, and rehearse '
            'explaining it in under three minutes.'
        )
    lines.append('   Budget roughly 8-10 focused hours per week and protect that time.')
    lines.append('')

    # --- 7. Internship Preparation Actions --------------------------------
    lines.append('7. INTERNSHIP PREPARATION ACTIONS')
    lines.append(
        '   - Write a one-page CV that lists your strongest skills first and links to '
        'your GitHub profile.'
    )
    lines.append(
        '   - Make sure every repository you would show an employer has a README that '
        'explains what the project does and how to run it.'
    )
    lines.append(
        f'   - Prepare a two-minute spoken answer to "why {target_role.lower()}?" that '
        'uses one of your own projects as evidence.'
    )
    lines.append(
        '   - Identify three organisations that take interns in this area and note what '
        'each of them asks for.'
    )
    lines.append(
        '   - Ask a lecturer or mentor to review this analysis and your CV before you '
        'apply.'
    )
    lines.append('')

    # --- 8. Limitations ---------------------------------------------------
    lines.append('8. LIMITATIONS')
    lines.append(f'   {MOCK_LIMITATIONS_NOTE}')

    return '\n'.join(lines)
