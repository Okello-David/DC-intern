"""AI service layer — the only place in the project that talks to an AI provider.

Design rules for this module:

* It runs **server-side only**. The React frontend calls the Django API; Django
  calls the AI provider. The API key therefore never leaves the server.
* It is **provider-agnostic**. `AI_PROVIDER` selects the implementation, so
  swapping OpenAI / Gemini / Anthropic later touches this file and nothing else.
* It always **degrades safely**. When `AI_PROVIDER=mock`, or when no `AI_API_KEY`
  is configured, it returns a structured local analysis instead of failing, so
  the feature can be demonstrated offline and at zero cost.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when an analysis cannot be produced.

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
    'This response was produced by the local fallback analyser, not by an external AI '
    'model, so no student data left this server and no API cost was incurred. It is '
    'rule-based, which means it reasons only about the skills it knows to look for. '
    'The structure is identical to what a real provider will return once one is '
    'configured. ' + LIMITATIONS_NOTE
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
        dict with keys ``content`` (the readable analysis text), ``provider``,
        ``model``, and ``used_fallback`` (True when no external AI was called).

    Raises:
        AIServiceError: if a configured real provider fails.
    """
    skills = list(skills or [])
    career_inputs = list(career_inputs or [])

    provider = (getattr(settings, 'AI_PROVIDER', 'mock') or 'mock').strip().lower()
    api_key = (getattr(settings, 'AI_API_KEY', '') or '').strip()
    model = getattr(settings, 'AI_MODEL', 'mock-local') or 'mock-local'

    if provider == 'mock' or not api_key:
        if provider != 'mock':
            logger.warning(
                'AI_PROVIDER=%s but no AI_API_KEY is set; falling back to the local analyser.',
                provider,
            )
        return {
            'content': build_local_analysis(student_profile, skills, career_inputs),
            'provider': 'mock',
            'model': 'mock-local' if provider == 'mock' else f'{model} (unavailable)',
            'used_fallback': True,
        }

    try:
        content = _call_provider(provider, model, api_key, student_profile, skills, career_inputs)
    except AIServiceError:
        raise
    except Exception as exc:  # network errors, bad responses, SDK errors
        logger.exception('AI provider %r failed while generating a skill-gap analysis.', provider)
        raise AIServiceError(
            f'The AI provider ({provider}) could not be reached. Please try again later.'
        ) from exc

    return {
        'content': content,
        'provider': provider,
        'model': model,
        'used_fallback': False,
    }


def build_prompt(student_profile, skills, career_inputs):
    """Build the prompt a real provider would receive.

    Kept separate so the prompt can be reviewed, tested, and reused across
    providers — and so it is obvious exactly what student data is sent out.
    """
    skill_lines = [
        f'- {skill.name} ({skill.category}, {skill.confidence_level})'
        for skill in skills
    ] or ['- (none provided)']
    input_lines = [
        f'- {entry.input_type}: {entry.content}'
        for entry in career_inputs
    ] or ['- (none provided)']

    return (
        'You are a careers advisor for university students in IT-related fields.\n'
        'Produce a skill-gap analysis with these sections, in this order:\n'
        '1. Career Readiness Summary\n2. Strengths\n3. Missing Technical Skills\n'
        '4. Missing Professional Skills\n5. Suggested Projects\n'
        '6. 4-Week Learning Plan\n7. Limitations\n\n'
        'Be specific, encouraging, and realistic. Use plain text.\n\n'
        f'Student: {student_profile.full_name}\n'
        f'Field of study: {student_profile.field_of_study}\n'
        f'Year of study: {student_profile.year_of_study}\n'
        f'Career interest: {student_profile.career_interest}\n'
        f'Internship goal: {student_profile.internship_goal}\n\n'
        'Self-reported skills:\n' + '\n'.join(skill_lines) + '\n\n'
        'Resume / career inputs:\n' + '\n'.join(input_lines) + '\n'
    )


def _call_provider(provider, model, api_key, student_profile, skills, career_inputs):
    """Dispatch to a real AI provider.

    Nothing is implemented yet by design — Week 4 Day 2 is a local milestone and
    a provider has not been approved. Adding one means writing a single function
    here that takes ``build_prompt(...)`` and returns text; no other file in the
    project changes.
    """
    prompt = build_prompt(student_profile, skills, career_inputs)  # noqa: F841 - used by real providers

    raise AIServiceError(
        f'AI provider {provider!r} is configured but no client is implemented yet. '
        'Set AI_PROVIDER=mock to use the local analyser.'
    )


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

    # --- 2. Strengths -----------------------------------------------------
    lines.append('2. STRENGTHS')
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

    # --- 5. Suggested Projects --------------------------------------------
    lines.append('5. SUGGESTED PROJECTS')
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

    # --- 6. 4-Week Learning Plan ------------------------------------------
    lines.append('6. 4-WEEK LEARNING PLAN')
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

    # --- 7. Limitations ---------------------------------------------------
    lines.append('7. LIMITATIONS')
    lines.append(f'   {MOCK_LIMITATIONS_NOTE}')

    return '\n'.join(lines)
