from rest_framework import serializers

from .models import CareerInput, Recommendation, Skill, StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            'id',
            'full_name',
            'field_of_study',
            'year_of_study',
            'career_interest',
            'internship_goal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            'id',
            'student_profile',
            'name',
            'category',
            'confidence_level',
            'evidence',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CareerInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerInput
        fields = [
            'id',
            'student_profile',
            'input_type',
            'content',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = [
            'id',
            'student_profile',
            'recommendation_type',
            'content',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
