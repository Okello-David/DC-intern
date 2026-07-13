from django.db import models


class StudentProfile(models.Model):
    class FieldOfStudy(models.TextChoices):
        SOFTWARE_ENGINEERING = 'Software Engineering', 'Software Engineering'
        COMPUTER_SCIENCE = 'Computer Science', 'Computer Science'
        INFORMATION_TECHNOLOGY = 'Information Technology', 'Information Technology'
        INFORMATION_SYSTEMS = 'Information Systems', 'Information Systems'
        CYBERSECURITY = 'Cybersecurity', 'Cybersecurity'
        DATA_SCIENCE = 'Data Science', 'Data Science'
        COMPUTER_ENGINEERING = 'Computer Engineering', 'Computer Engineering'
        OTHER = 'Other IT Related Field', 'Other IT Related Field'

    class YearOfStudy(models.TextChoices):
        YEAR_1 = 'Year 1', 'Year 1'
        YEAR_2 = 'Year 2', 'Year 2'
        YEAR_3 = 'Year 3', 'Year 3'
        YEAR_4 = 'Year 4', 'Year 4'
        FINAL_YEAR = 'Final Year', 'Final Year'

    full_name = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=50, choices=FieldOfStudy.choices)
    year_of_study = models.CharField(max_length=20, choices=YearOfStudy.choices)
    career_interest = models.CharField(max_length=255)
    internship_goal = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.full_name} ({self.field_of_study})'


class Skill(models.Model):
    class Category(models.TextChoices):
        PROGRAMMING = 'Programming', 'Programming'
        WEB_DEVELOPMENT = 'Web Development', 'Web Development'
        DATABASE = 'Database', 'Database'
        CLOUD_COMPUTING = 'Cloud Computing', 'Cloud Computing'
        CYBERSECURITY = 'Cybersecurity', 'Cybersecurity'
        AI_AND_DATA = 'AI and Data', 'AI and Data'
        NETWORKING = 'Networking', 'Networking'
        SOFTWARE_ENGINEERING = 'Software Engineering', 'Software Engineering'
        PROFESSIONAL_SKILLS = 'Professional Skills', 'Professional Skills'
        OTHER = 'Other', 'Other'

    class ConfidenceLevel(models.TextChoices):
        BEGINNER = 'Beginner', 'Beginner'
        INTERMEDIATE = 'Intermediate', 'Intermediate'
        ADVANCED = 'Advanced', 'Advanced'

    student_profile = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='skills'
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=Category.choices)
    confidence_level = models.CharField(max_length=20, choices=ConfidenceLevel.choices)
    evidence = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.confidence_level}) - {self.student_profile.full_name}'


class CareerInput(models.Model):
    class InputType(models.TextChoices):
        RESUME_TEXT = 'Resume Text', 'Resume Text'
        CAREER_GOAL = 'Career Goal', 'Career Goal'
        INTERNSHIP_GOAL = 'Internship Goal', 'Internship Goal'

    student_profile = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='career_inputs'
    )
    input_type = models.CharField(max_length=30, choices=InputType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.input_type} - {self.student_profile.full_name}'


class Recommendation(models.Model):
    class RecommendationType(models.TextChoices):
        SKILL_GAP_ANALYSIS = 'Skill Gap Analysis', 'Skill Gap Analysis'
        CAREER_PATH = 'Career Path', 'Career Path'
        PROJECT_RECOMMENDATION = 'Project Recommendation', 'Project Recommendation'
        LEARNING_PLAN = 'Learning Plan', 'Learning Plan'
        RESUME_FEEDBACK = 'Resume Feedback', 'Resume Feedback'
        PLACEHOLDER = 'Placeholder', 'Placeholder'

    student_profile = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='recommendations'
    )
    recommendation_type = models.CharField(max_length=30, choices=RecommendationType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.recommendation_type} - {self.student_profile.full_name}'
