from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('profiles', views.StudentProfileViewSet, basename='profile')
router.register('skills', views.SkillViewSet, basename='skill')
router.register('career-inputs', views.CareerInputViewSet, basename='career-input')
router.register('recommendations', views.RecommendationViewSet, basename='recommendation')

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('', include(router.urls)),
]
