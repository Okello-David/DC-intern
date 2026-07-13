from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import CareerInput, Recommendation, Skill, StudentProfile
from .serializers import (
    CareerInputSerializer,
    RecommendationSerializer,
    SkillSerializer,
    StudentProfileSerializer,
)


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


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class CareerInputViewSet(viewsets.ModelViewSet):
    queryset = CareerInput.objects.all()
    serializer_class = CareerInputSerializer


class RecommendationViewSet(viewsets.ModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
