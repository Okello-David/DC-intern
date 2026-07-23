from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError, EndpointConnectionError
from config.database import build_database_config
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings

from .management.commands.check_database import Command as CheckDatabaseCommand
from .management.commands.check_database import mask_host
from .models import CareerInput, Recommendation, Skill, StudentProfile
from .services import ai_service
from .services.ai_service import (
    AIServiceError,
    _extract_bedrock_text,
    generate_skill_gap_analysis,
    generate_with_bedrock,
)
from .services.prompts import build_skill_gap_prompt


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

        # Requirement: the endpoint reports which implementation produced the text.
        self.assertEqual(body['provider'], 'mock')
        self.assertEqual(body['model'], 'mock-local')
        self.assertFalse(body['fallback_used'] is None)
        self.assertTrue(body['fallback_used'])

        recommendation = Recommendation.objects.get(pk=body['recommendation_id'])
        self.assertEqual(recommendation.student_profile, self.profile)
        self.assertEqual(recommendation.content, body['content'])

    def test_analysis_contains_every_required_section(self):
        content = self.client.post(self.url(self.profile.pk)).json()['content']

        for heading in (
            'CAREER READINESS SUMMARY',
            'CURRENT STRENGTHS',
            'MISSING TECHNICAL SKILLS',
            'MISSING PROFESSIONAL SKILLS',
            'RECOMMENDED PROJECTS',
            'FOUR-WEEK LEARNING PLAN',
            'INTERNSHIP PREPARATION ACTIONS',
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


def bedrock_response(text='Generated analysis text.', stop_reason='end_turn'):
    """A minimal, realistic Bedrock Converse response."""
    return {
        'output': {'message': {'role': 'assistant', 'content': [{'text': text}]}},
        'stopReason': stop_reason,
        'usage': {'inputTokens': 420, 'outputTokens': 900, 'totalTokens': 1320},
    }


def client_error(code, message='raw AWS detail arn:aws:sts::123456789012:assumed-role/x'):
    return ClientError({'Error': {'Code': code, 'Message': message}}, 'Converse')


BEDROCK_SETTINGS = {
    'AI_PROVIDER': 'bedrock',
    'AI_MODEL': 'amazon.nova-micro-v1:0',
    'AWS_BEDROCK_REGION': 'eu-north-1',
    'AI_MAX_TOKENS': 1200,
    'AI_TEMPERATURE': 0.2,
    'AI_FALLBACK_TO_MOCK': True,
}


class AIServiceMockModeTests(TestCase):
    """`AI_PROVIDER=mock` must never touch the network, at all."""

    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Cybersecurity',
            year_of_study='Final Year',
            career_interest='Security Analyst',
            internship_goal='SOC internship',
        )

    @override_settings(AI_PROVIDER='mock', AI_MODEL='mock-local')
    def test_mock_provider_reports_itself_honestly(self):
        result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertEqual(result['provider'], 'mock')
        self.assertEqual(result['model'], 'mock-local')
        self.assertTrue(result['used_fallback'])
        self.assertIsNone(result['fallback_reason'])
        self.assertIn('Cybersecurity Analyst', result['content'])

    @override_settings(AI_PROVIDER='mock')
    def test_mock_provider_never_builds_an_aws_client(self):
        with patch.object(ai_service, '_bedrock_client') as factory:
            generate_skill_gap_analysis(self.profile, [], [])

        factory.assert_not_called()

    @override_settings(AI_PROVIDER='MOCK  ')
    def test_provider_name_is_case_and_whitespace_insensitive(self):
        self.assertEqual(generate_skill_gap_analysis(self.profile, [], [])['provider'], 'mock')

    @override_settings(AI_PROVIDER='openai', AI_MODEL='gpt-x', AI_FALLBACK_TO_MOCK=True)
    def test_unsupported_provider_falls_back_when_allowed(self):
        result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertTrue(result['used_fallback'])
        self.assertEqual(result['requested_provider'], 'openai')
        self.assertIn('unsupported', result['fallback_reason'].lower())

    @override_settings(AI_PROVIDER='openai', AI_MODEL='gpt-x', AI_FALLBACK_TO_MOCK=False)
    def test_unsupported_provider_raises_when_fallback_is_off(self):
        with self.assertRaises(AIServiceError):
            generate_skill_gap_analysis(self.profile, [], [])


class NoRealAWSCallTests(TestCase):
    """The suite must be safe to run offline, on any machine, with any AWS profile.

    Every Bedrock test patches `_bedrock_client`, which is the single place a
    boto3 client is constructed. These tests prove that: `boto3.client` itself is
    replaced with a function that fails the test if anything calls it.
    """

    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Computer Science',
            year_of_study='Year 2',
            career_interest='Backend Engineering',
            internship_goal='Backend internship',
        )

    def test_default_test_settings_use_mock(self):
        from django.conf import settings

        self.assertEqual(settings.AI_PROVIDER, 'mock')

    def test_no_boto3_client_is_ever_constructed_in_mock_mode(self):
        import boto3

        def explode(*args, **kwargs):
            raise AssertionError(f'A real AWS client was constructed: {args} {kwargs}')

        with patch.object(boto3, 'client', side_effect=explode):
            response = self.client.post(
                f'/api/profiles/{self.profile.pk}/generate-skill-gap/'
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['provider'], 'mock')

    @override_settings(**BEDROCK_SETTINGS)
    def test_patched_factory_means_the_sdk_is_never_reached(self):
        import boto3

        fake_client = MagicMock()
        fake_client.converse.return_value = bedrock_response()

        def explode(*args, **kwargs):
            raise AssertionError('boto3.client was called despite the patched factory')

        with patch.object(boto3, 'client', side_effect=explode), \
                patch.object(ai_service, '_bedrock_client', return_value=fake_client):
            result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertEqual(result['provider'], 'bedrock')


@override_settings(**BEDROCK_SETTINGS)
class BedrockProviderTests(TestCase):
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
        )
        self.fake_client = MagicMock()
        self.fake_client.converse.return_value = bedrock_response(
            '1. CAREER READINESS SUMMARY\nYou are progressing well.'
        )

    def call(self):
        with patch.object(ai_service, '_bedrock_client', return_value=self.fake_client):
            return generate_skill_gap_analysis(
                self.profile, self.profile.skills.all(), self.profile.career_inputs.all()
            )

    def test_successful_call_returns_the_model_text_and_metadata(self):
        result = self.call()

        self.assertIn('You are progressing well.', result['content'])
        self.assertEqual(result['provider'], 'bedrock')
        self.assertEqual(result['model'], 'amazon.nova-micro-v1:0')
        self.assertFalse(result['used_fallback'])
        self.assertIsNone(result['fallback_reason'])

    def test_converse_is_called_with_the_configured_model_and_inference_config(self):
        self.call()

        kwargs = self.fake_client.converse.call_args.kwargs
        self.assertEqual(kwargs['modelId'], 'amazon.nova-micro-v1:0')
        self.assertEqual(kwargs['inferenceConfig'], {'maxTokens': 1200, 'temperature': 0.2})
        self.assertEqual(kwargs['messages'][0]['role'], 'user')

    def test_a_system_instruction_with_the_safety_rules_is_sent(self):
        self.call()

        system_text = self.fake_client.converse.call_args.kwargs['system'][0]['text']
        for rule in ('Do NOT guarantee employment', 'Do NOT invent qualifications',
                     'Do NOT discriminate', 'Do NOT request personal data'):
            with self.subTest(rule=rule):
                self.assertIn(rule, system_text)

    def test_the_prompt_carries_the_students_own_inputs(self):
        self.call()

        prompt = self.fake_client.converse.call_args.kwargs['messages'][0]['content'][0]['text']
        self.assertIn('Cloud Engineering', prompt)
        self.assertIn('Python', prompt)
        self.assertIn('Year 3', prompt)

    def test_no_credential_or_key_is_passed_to_boto3(self):
        """boto3 must resolve the EC2 IAM role itself — nothing is passed in."""
        with patch('boto3.client') as boto_client:
            boto_client.return_value = self.fake_client
            ai_service._bedrock_client()

        args, kwargs = boto_client.call_args
        self.assertEqual(args, ('bedrock-runtime',))
        self.assertEqual(set(kwargs), {'region_name'})
        self.assertEqual(kwargs['region_name'], 'eu-north-1')


@override_settings(**BEDROCK_SETTINGS)
class BedrockResponseExtractionTests(TestCase):
    def test_text_is_extracted_from_a_normal_response(self):
        self.assertEqual(_extract_bedrock_text(bedrock_response('Hello.')), 'Hello.')

    def test_multiple_content_blocks_are_joined(self):
        response = {
            'output': {'message': {'content': [{'text': 'First.'}, {'text': 'Second.'}]}},
            'stopReason': 'end_turn',
        }

        self.assertEqual(_extract_bedrock_text(response), 'First.\nSecond.')

    def test_non_text_blocks_are_ignored(self):
        response = {
            'output': {'message': {'content': [
                {'reasoningContent': {'text': 'internal'}},
                {'text': 'Visible answer.'},
            ]}},
        }

        self.assertEqual(_extract_bedrock_text(response), 'Visible answer.')

    def test_a_truncated_response_is_flagged_to_the_reader(self):
        text = _extract_bedrock_text(bedrock_response('Cut off here', stop_reason='max_tokens'))

        self.assertIn('length limit', text)

    def test_empty_or_malformed_responses_raise_a_clean_error(self):
        for response in ({}, None, {'output': {}}, bedrock_response('   ')):
            with self.subTest(response=response):
                with self.assertRaises(AIServiceError) as raised:
                    _extract_bedrock_text(response)
                self.assertIn('empty response', str(raised.exception))


@override_settings(**BEDROCK_SETTINGS)
class BedrockErrorHandlingTests(TestCase):
    """Every AWS failure must become a clean, non-leaking application error."""

    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Data Science',
            year_of_study='Year 2',
            career_interest='Data Analyst',
            internship_goal='Data internship',
        )

    def failing_client(self, exception):
        client = MagicMock()
        client.converse.side_effect = exception
        return client

    def test_client_error_becomes_a_clean_ai_service_error(self):
        client = self.failing_client(client_error('AccessDeniedException'))

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            with self.assertRaises(AIServiceError) as raised:
                generate_with_bedrock('prompt')

        message = str(raised.exception)
        self.assertIn('not authorised', message)
        # The raw AWS detail must not reach the caller.
        self.assertNotIn('arn:aws', message)
        self.assertNotIn('123456789012', message)
        self.assertNotIn('AccessDeniedException', message)

    def test_every_known_error_code_maps_to_a_readable_message(self):
        for code in ('ThrottlingException', 'ValidationException',
                     'ResourceNotFoundException', 'ServiceQuotaExceededException'):
            with self.subTest(code=code):
                client = self.failing_client(client_error(code))
                with patch.object(ai_service, '_bedrock_client', return_value=client):
                    with self.assertRaises(AIServiceError) as raised:
                        generate_with_bedrock('prompt')
                self.assertNotIn(code, str(raised.exception))

    def test_an_unknown_error_code_gets_the_generic_message(self):
        client = self.failing_client(client_error('SomeBrandNewException'))

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            with self.assertRaises(AIServiceError) as raised:
                generate_with_bedrock('prompt')

        self.assertIn('could not be reached', str(raised.exception))

    def test_botocore_connection_errors_are_handled(self):
        client = self.failing_client(
            EndpointConnectionError(endpoint_url='https://bedrock-runtime.invalid')
        )

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            with self.assertRaises(AIServiceError) as raised:
                generate_with_bedrock('prompt')

        self.assertNotIn('invalid', str(raised.exception))

    def test_an_unexpected_sdk_error_is_still_contained(self):
        client = self.failing_client(RuntimeError('something odd inside botocore'))

        # assertLogs both asserts the failure is recorded and keeps the
        # traceback out of the test runner's output.
        with patch.object(ai_service, '_bedrock_client', return_value=client), \
                self.assertLogs('career.services.ai_service', level='ERROR'):
            with self.assertRaises(AIServiceError):
                generate_with_bedrock('prompt')

    def test_nothing_student_written_is_ever_logged(self):
        """Logs go to journald and later CloudWatch; resume text must not."""
        secret_text = 'MY-PRIVATE-RESUME-CONTENT'
        client = self.failing_client(client_error('ValidationException', secret_text))

        with patch.object(ai_service, '_bedrock_client', return_value=client), \
                self.assertLogs('career.services.ai_service', level='ERROR') as logs:
            with self.assertRaises(AIServiceError):
                generate_with_bedrock(f'Career goal: {secret_text}')

        logged = '\n'.join(logs.output)
        self.assertNotIn(secret_text, logged)
        self.assertIn('ValidationException', logged)  # the code alone is useful

    @override_settings(AWS_BEDROCK_REGION='')
    def test_a_missing_region_fails_before_any_call(self):
        with self.assertRaises(AIServiceError) as raised:
            ai_service._bedrock_client()

        self.assertIn('not fully configured', str(raised.exception))

    @override_settings(AI_FALLBACK_TO_MOCK=True)
    def test_failure_with_fallback_on_returns_a_labelled_mock_analysis(self):
        client = self.failing_client(client_error('ThrottlingException'))

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            result = generate_skill_gap_analysis(self.profile, [], [])

        self.assertEqual(result['provider'], 'mock')
        self.assertEqual(result['model'], 'mock-local')
        self.assertTrue(result['used_fallback'])
        self.assertEqual(result['requested_provider'], 'bedrock')
        self.assertTrue(result['fallback_reason'])
        # The saved text itself must say it is not model output.
        self.assertIn('FALLBACK MODE', result['content'])
        self.assertIn('NOT', result['content'])

    @override_settings(AI_FALLBACK_TO_MOCK=False)
    def test_failure_with_fallback_off_raises_instead_of_pretending(self):
        client = self.failing_client(client_error('ThrottlingException'))

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            with self.assertRaises(AIServiceError):
                generate_skill_gap_analysis(self.profile, [], [])


@override_settings(**BEDROCK_SETTINGS)
class SkillGapEndpointWithBedrockTests(TestCase):
    """End to end through the API, with the boto3 client mocked out."""

    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Software Engineering',
            year_of_study='Year 4',
            career_interest='Full-Stack Engineering',
            internship_goal='Full-stack internship',
        )
        self.url = f'/api/profiles/{self.profile.pk}/generate-skill-gap/'

    def test_endpoint_reports_bedrock_as_the_provider_on_success(self):
        client = MagicMock()
        client.converse.return_value = bedrock_response('8. LIMITATIONS\nGuidance only.')

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            response = self.client.post(self.url)

        body = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(body['provider'], 'bedrock')
        self.assertEqual(body['model'], 'amazon.nova-micro-v1:0')
        self.assertFalse(body['fallback_used'])
        self.assertIn('Guidance only.', body['content'])
        # The saved Recommendation holds exactly what was returned.
        self.assertEqual(
            Recommendation.objects.get(pk=body['recommendation_id']).content, body['content']
        )

    def test_endpoint_reports_the_fallback_honestly_when_bedrock_fails(self):
        client = MagicMock()
        client.converse.side_effect = client_error('AccessDeniedException')

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            response = self.client.post(self.url)

        body = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(body['provider'], 'mock')
        self.assertTrue(body['fallback_used'])
        self.assertTrue(any('local rule-based analyser' in note for note in body['notes']))

    @override_settings(AI_FALLBACK_TO_MOCK=False)
    def test_endpoint_returns_503_when_bedrock_fails_and_fallback_is_off(self):
        client = MagicMock()
        client.converse.side_effect = client_error('ThrottlingException')

        with patch.object(ai_service, '_bedrock_client', return_value=client):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertIn('busy', body['error'])
        self.assertNotIn('arn:aws', body['error'])
        self.assertNotIn('Traceback', body['error'])
        # Nothing is saved when no analysis was produced.
        self.assertEqual(Recommendation.objects.count(), 0)


class PromptBuilderTests(TestCase):
    def setUp(self):
        self.profile = StudentProfile.objects.create(
            full_name='Jane Doe',
            field_of_study='Information Technology',
            year_of_study='Year 2',
            career_interest='Cybersecurity',
            internship_goal='SOC internship',
        )
        self.skill = Skill.objects.create(
            student_profile=self.profile,
            name='Linux',
            category='Cybersecurity',
            confidence_level='Beginner',
        )
        self.career_input = CareerInput.objects.create(
            student_profile=self.profile,
            input_type='Career Goal',
            content='I want to work in a security operations centre.',
        )

    def prompt(self):
        return build_skill_gap_prompt(self.profile, [self.skill], [self.career_input])

    def test_prompt_contains_every_required_input(self):
        prompt = self.prompt()

        for expected in ('Information Technology', 'Year 2', 'Cybersecurity',
                         'SOC internship', 'Linux', 'Beginner',
                         'security operations centre'):
            with self.subTest(expected=expected):
                self.assertIn(expected, prompt)

    def test_prompt_does_not_send_the_students_name(self):
        """Privacy: the analysis does not need it, so it is not sent to AWS."""
        self.assertNotIn('Jane Doe', self.prompt())

    def test_long_career_input_is_truncated(self):
        self.career_input.content = 'x' * 5000

        prompt = build_skill_gap_prompt(self.profile, [], [self.career_input])

        self.assertIn('truncated', prompt)
        self.assertLess(len(prompt), 2500)

    def test_empty_inputs_are_labelled_rather_than_omitted(self):
        prompt = build_skill_gap_prompt(self.profile, [], [])

        self.assertIn('(none reported)', prompt)
        self.assertIn('(none provided)', prompt)


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
