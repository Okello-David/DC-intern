import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import CareerInput, Recommendation, Skill, StudentProfile
from .serializers import (
    CareerInputSerializer,
    RecommendationSerializer,
    SkillSerializer,
    StudentProfileSerializer,
)
from .services.ai_service import AIServiceError, generate_skill_gap_analysis

logger = logging.getLogger(__name__)


@api_view(['GET'])
def health_check(request):
    return Response({
        'status': 'ok',
        'message': 'Backend is running',
        'project': 'AI-Powered Student Career and Internship Assistant',
    })


class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer

    @action(detail=True, methods=['post'], url_path='generate-skill-gap')
    def generate_skill_gap(self, request, pk=None):
        """POST /api/profiles/<id>/generate-skill-gap/

        Gathers the profile's skills and career inputs, asks the AI service
        layer for a skill-gap analysis, saves it as a Recommendation, and
        returns it. A missing profile yields 404 (handled by `get_object`);
        a missing profile skills/career inputs still produces a limited
        analysis, flagged in `notes`.
        """
        profile = self.get_object()

        skills = list(profile.skills.all())
        career_inputs = list(profile.career_inputs.all())

        notes = []
        if not skills:
            notes.append(
                'No skills were found for this profile, so the analysis is limited. '
                'Add skills and generate again for a personalised result.'
            )
        if not career_inputs:
            notes.append(
                'No resume text or career goal was found for this profile, so the analysis '
                'could not take your experience into account.'
            )

        try:
            result = generate_skill_gap_analysis(profile, skills, career_inputs)
        except AIServiceError as exc:
            logger.warning('Skill-gap analysis failed for profile %s: %s', profile.pk, exc)
            return Response(
                {'error': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            # Never leak a traceback to the client.
            logger.exception('Unexpected error generating skill-gap analysis for profile %s', profile.pk)
            return Response(
                {'error': 'Could not generate the skill gap analysis. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        recommendation = Recommendation.objects.create(
            student_profile=profile,
            recommendation_type=Recommendation.RecommendationType.SKILL_GAP_ANALYSIS,
            content=result['content'],
        )

        return Response(
            {
                'profile_id': profile.pk,
                'recommendation_id': recommendation.pk,
                'recommendation_type': recommendation.recommendation_type,
                'content': recommendation.content,
                'created_at': recommendation.created_at,
                'ai_provider': result['provider'],
                'ai_model': result['model'],
                'used_fallback': result['used_fallback'],
                'notes': notes,
            },
            status=status.HTTP_201_CREATED,
        )


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class CareerInputViewSet(viewsets.ModelViewSet):
    queryset = CareerInput.objects.all()
    serializer_class = CareerInputSerializer


class RecommendationViewSet(viewsets.ModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
