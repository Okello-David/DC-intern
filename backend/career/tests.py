from django.test import TestCase, override_settings

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
