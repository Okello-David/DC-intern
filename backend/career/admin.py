from django.contrib import admin

from .models import CareerInput, Recommendation, Skill, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'field_of_study', 'year_of_study', 'career_interest', 'created_at')
    list_filter = ('field_of_study', 'year_of_study')
    search_fields = ('full_name', 'career_interest')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_profile', 'category', 'confidence_level', 'created_at')
    list_filter = ('category', 'confidence_level')
    search_fields = ('name', 'student_profile__full_name')


@admin.register(CareerInput)
class CareerInputAdmin(admin.ModelAdmin):
    list_display = ('student_profile', 'input_type', 'created_at')
    list_filter = ('input_type',)
    search_fields = ('student_profile__full_name', 'content')


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('student_profile', 'recommendation_type', 'created_at')
    list_filter = ('recommendation_type',)
    search_fields = ('student_profile__full_name', 'content')
