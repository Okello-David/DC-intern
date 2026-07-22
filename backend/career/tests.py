from io import StringIO
from pathlib import Path

from config.database import build_database_config
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings

from .management.commands.check_database import Command as CheckDatabaseCommand
from .management.commands.check_database import mask_host
from .models import CareerInput, Recommendation, Skill, StudentProfile
from .services.ai_service import AIServiceError, generate_skill_gap_analysis


class HealthCheckTests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')


class ExistingEndpointsTests(TestCase):
    """Week 3 CRUD endpoints must keep working after the Week 4 changes."""

    def test_all_list_endpoints_respond(self):
        for path in ('/api/profiles/', '/api/skills/', '/api/career-inputs/', '/api/recommendations/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_profile_can_still_be_created(self):
        response = self.client.post(
            '/api/profiles/',
            data={
                'full_name': 'Jane Doe',
                'field_of_study': 'Computer Science',
                'year_of_study': 'Year 3',
                'career_interest': 'Backend Engineering',
                'internship_goal': 'Backend internship',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(StudentProfile.objects.count(), 1)


@override_settings(AI_PROVIDER='mock', AI_API_KEY='', AI_MODEL='mock-local')
class SkillGapEndpointTests(TestCase):
    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Computer Science',
            year_of_study='Year 3',
            career_interest='Cloud Engineering',
            internship_goal='A cloud engineering internship using AWS',
        )
        Skill.objects.create(
            student_profile=self.profile,
            name='Python',
            category='Programming',
            confidence_level='Intermediate',
            evidence='Coursework and personal scripts',
        )
        CareerInput.objects.create(
            student_profile=self.profile,
            input_type='Career Goal',
            content='I want to become a cloud engineer.',
        )

    def url(self, profile_id):
        return f'/api/profiles/{profile_id}/generate-skill-gap/'

    def test_generates_and_saves_a_recommendation(self):
        response = self.client.post(self.url(self.profile.pk))

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['profile_id'], self.profile.pk)
        self.assertEqual(body['recommendation_type'], 'Skill Gap Analysis')
        self.assertTrue(body['used_fallback'])
        self.assertIn('created_at', body)

        recommendation = Recommendation.objects.get(pk=body['recommendation_id'])
        self.assertEqual(recommendation.student_profile, self.profile)
        self.assertEqual(recommendation.content, body['content'])

    def test_analysis_contains_every_required_section(self):
        content = self.client.post(self.url(self.profile.pk)).json()['content']

        for heading in (
            'CAREER READINESS SUMMARY',
            'STRENGTHS',
            'MISSING TECHNICAL SKILLS',
            'MISSING PROFESSIONAL SKILLS',
            'SUGGESTED PROJECTS',
            '4-WEEK LEARNING PLAN',
            'LIMITATIONS',
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, content)

    def test_analysis_uses_the_students_own_data(self):
        content = self.client.post(self.url(self.profile.pk)).json()['content']

        self.assertIn('Jane Doe', content)
        self.assertIn('Python', content)
        self.assertIn('Cloud / DevOps Engineer', content)

    def test_missing_profile_returns_404(self):
        response = self.client.post(self.url(9999))

        self.assertEqual(response.status_code, 404)

    def test_profile_without_skills_or_inputs_still_generates_with_notes(self):
        empty_profile = StudentProfile.objects.create(
            full_name='John Doe',
            field_of_study='Information Technology',
            year_of_study='Year 1',
            career_interest='Undecided',
            internship_goal='Any IT internship',
        )

        response = self.client.post(self.url(empty_profile.pk))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()['notes']), 2)
        self.assertIn('LIMITATIONS', response.json()['content'])

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url(self.profile.pk)).status_code, 405)


class AIServiceTests(TestCase):
    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Cybersecurity',
            year_of_study='Final Year',
            career_interest='Security Analyst',
            internship_goal='SOC internship',
        )

    @override_settings(AI_PROVIDER='mock', AI_API_KEY='', AI_MODEL='mock-local')
    def test_mock_provider_never_calls_out(self):
        result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertTrue(result['used_fallback'])
        self.assertEqual(result['provider'], 'mock')

    @override_settings(AI_PROVIDER='openai', AI_API_KEY='', AI_MODEL='gpt-x')
    def test_real_provider_without_key_falls_back_safely(self):
        result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertTrue(result['used_fallback'])
        self.assertIn('Cybersecurity Analyst', result['content'])

    @override_settings(AI_PROVIDER='openai', AI_API_KEY='not-a-real-key', AI_MODEL='gpt-x')
    def test_unimplemented_provider_raises_ai_service_error(self):
        with self.assertRaises(AIServiceError):
            generate_skill_gap_analysis(self.profile, [], [])


class DatabaseSelectionTests(TestCase):
    """`DB_HOST` is the switch between local SQLite and PostgreSQL on RDS.

    These are pure configuration tests — no database connection is opened, so
    they pass with no RDS instance and no network access.
    """

    BASE_DIR = Path('/srv/app')

    POSTGRES_ENV = {
        'db_host': 'careerdb.example.invalid',
        'db_name': 'career_assistant',
        'db_user': 'careeradmin',
        'db_password': 'not-a-real-password',
    }

    def test_sqlite_is_selected_when_db_host_is_missing(self):
        config = build_database_config(self.BASE_DIR)

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(config['NAME'], self.BASE_DIR / 'db.sqlite3')

    def test_sqlite_is_selected_for_empty_or_blank_db_host(self):
        for db_host in ('', '   ', None):
            with self.subTest(db_host=db_host):
                config = build_database_config(self.BASE_DIR, db_host=db_host)
                self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')

    def test_other_db_variables_do_not_switch_away_from_sqlite(self):
        """Only DB_HOST decides — stale DB_NAME/DB_USER must not force PostgreSQL."""
        config = build_database_config(
            self.BASE_DIR, db_name='career_assistant', db_user='careeradmin'
        )

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')

    def test_postgresql_is_selected_when_db_host_is_present(self):
        config = build_database_config(self.BASE_DIR, **self.POSTGRES_ENV)

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'career_assistant')
        self.assertEqual(config['USER'], 'careeradmin')
        self.assertEqual(config['PASSWORD'], 'not-a-real-password')
        self.assertEqual(config['HOST'], 'careerdb.example.invalid')

    def test_postgresql_defaults_are_cloud_safe(self):
        config = build_database_config(self.BASE_DIR, **self.POSTGRES_ENV)

        self.assertEqual(config['PORT'], '5432')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')
        self.assertEqual(config['OPTIONS']['connect_timeout'], 10)
        self.assertEqual(config['CONN_MAX_AGE'], 60)
        self.assertTrue(config['CONN_HEALTH_CHECKS'])

    def test_postgresql_values_can_be_overridden(self):
        config = build_database_config(
            self.BASE_DIR, **self.POSTGRES_ENV, db_port='6543', db_sslmode='verify-full'
        )

        self.assertEqual(config['PORT'], '6543')
        self.assertEqual(config['OPTIONS']['sslmode'], 'verify-full')

    def test_blank_port_and_sslmode_fall_back_to_defaults(self):
        config = build_database_config(
            self.BASE_DIR, **self.POSTGRES_ENV, db_port='', db_sslmode=''
        )

        self.assertEqual(config['PORT'], '5432')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')

    def test_missing_postgresql_credentials_fail_loudly(self):
        with self.assertRaises(ImproperlyConfigured) as raised:
            build_database_config(self.BASE_DIR, db_host='careerdb.example.invalid')

        message = str(raised.exception)
        for variable in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            self.assertIn(variable, message)

    def test_partially_configured_postgresql_names_only_what_is_missing(self):
        with self.assertRaises(ImproperlyConfigured) as raised:
            build_database_config(
                self.BASE_DIR,
                db_host='careerdb.example.invalid',
                db_name='career_assistant',
                db_user='careeradmin',
            )

        message = str(raised.exception)
        self.assertIn('DB_PASSWORD', message)
        self.assertNotIn('DB_NAME', message)
        # A configuration error must not echo the values it did receive.
        self.assertNotIn('careeradmin', message)


class CheckDatabaseCommandTests(TestCase):
    """The diagnostic command must be safe to run (and screenshot) anywhere."""

    def test_reports_sqlite_and_succeeds_locally(self):
        out = StringIO()

        call_command('check_database', stdout=out)

        output = out.getvalue()
        self.assertIn('sqlite3', output)
        self.assertIn('OK', output)

    def test_sqlite_output_mentions_no_credentials_at_all(self):
        out = StringIO()

        call_command('check_database', stdout=out)

        output = out.getvalue().lower()
        for term in ('password', 'secret', 'sslmode'):
            with self.subTest(term=term):
                self.assertNotIn(term, output)

    def test_host_is_masked_by_default(self):
        masked = mask_host('careerdb.abc123.eu-west-1.rds.amazonaws.com')

        self.assertNotIn('careerdb', masked)
        self.assertIn('rds.amazonaws.com', masked)

    def test_mask_host_handles_short_and_missing_values(self):
        self.assertEqual(mask_host(''), '(not set)')
        self.assertNotIn('db', mask_host('db.example.com'))
        self.assertEqual(mask_host('localhost'), 'lo***')

    def test_connection_errors_are_scrubbed_of_the_password(self):
        db_settings = {
            'ENGINE': 'django.db.backends.postgresql',
            'PASSWORD': 'not-a-real-password',
        }
        exception = Exception('connection failed for user=careeradmin password=not-a-real-password')

        message = CheckDatabaseCommand._clean_error(exception, db_settings)

        self.assertNotIn('not-a-real-password', message)
        self.assertIn('***', message)
        self.assertIn('security group', message)
