from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

# 1. Exam Category (SSC, Banking, Railway)
class ExamCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="category_logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Exam Categories"
        ordering = ['name']

# 2. Sub Category (CGL, CHSL, PO, Clerk)
class SubCategory(models.Model):
    category = models.ForeignKey(
        ExamCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ImageField(upload_to="sub_icons/", null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while SubCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    class Meta:
        verbose_name_plural = "Sub Categories"
        ordering = ['category__name', 'name']

# 3. Subject Master (All available subjects)
class SubjectMaster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="subject_icons/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

# 4. Mock Test - IMPROVED VERSION
class MockTest(models.Model):
    TEST_TYPE_CHOICES = [
        ('subject_wise', 'Subject Wise'),
        ('mixed', 'Mixed (All Subjects)'),
    ]
    
    title = models.CharField(max_length=255)
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mock_tests"
    )
    test_type = models.CharField(
        max_length=20, 
        choices=TEST_TYPE_CHOICES, 
        default='mixed',
        help_text="Select 'Subject Wise' for subject-based sections or 'Mixed' for random questions"
    )
    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    total_questions = models.PositiveIntegerField(default=0, editable=False)
    total_marks = models.PositiveIntegerField(default=0, editable=False)
    passing_marks = models.PositiveIntegerField(default=40, help_text="Passing percentage")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def update_totals(self):
        """Update total questions and marks"""
        questions = self.questions.all()
        self.total_questions = questions.count()
        self.total_marks = sum(q.marks for q in questions)
        self.save()
    
    def get_subject_breakdown(self):
        """Get question count and marks by subject"""
        breakdown = {}
        for question in self.questions.all():
            subject = question.subject.name if question.subject else "Uncategorized"
            if subject not in breakdown:
                breakdown[subject] = {'count': 0, 'marks': 0}
            breakdown[subject]['count'] += 1
            breakdown[subject]['marks'] += question.marks
        return breakdown
    
    class Meta:
        ordering = ['-created_at']

# 5. Subject Section (For subject-wise tests)
class SubjectSection(models.Model):
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="sections",
        limit_choices_to={'test_type': 'subject_wise'}
    )
    subject = models.ForeignKey(
        SubjectMaster,
        on_delete=models.CASCADE,
        related_name="test_sections"
    )
    name = models.CharField(max_length=100, blank=True, help_text="Leave blank to use subject name")
    question_count = models.PositiveIntegerField(default=0, editable=False)
    total_marks = models.PositiveIntegerField(default=0, editable=False)
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.subject.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.mock_test.title} - {self.name}"
    
    class Meta:
        ordering = ['order', 'id']

# 6. Question - IMPROVED VERSION
class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    subject = models.ForeignKey(
        SubjectMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Subject for this question (optional for mixed tests)"
    )
    section = models.ForeignKey(
        SubjectSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Section for subject-wise tests"
    )
    
    # Question text in multiple languages
    question_en = models.TextField()
    question_hi = models.TextField(blank=True, null=True)
    
    # Question metadata
    question_number = models.PositiveIntegerField(default=0, help_text="Question number in test")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    marks = models.PositiveIntegerField(default=1)
    negative_marks = models.FloatField(default=0, help_text="Negative marks for wrong answer (0 for no negative)")
    
    # Explanation
    explanation = models.TextField(blank=True, null=True)
    explanation_hi = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_en[:50]
    
    def clean(self):
        """Validate question based on test type"""
        if self.mock_test.test_type == 'subject_wise' and not self.section:
            raise ValidationError("Subject-wise tests require section assignment")
        if self.section and self.section.mock_test != self.mock_test:
            raise ValidationError("Section must belong to the same mock test")
    
    def save(self, *args, **kwargs):
        if not self.question_number:
            last_question = Question.objects.filter(mock_test=self.mock_test).order_by('-question_number').first()
            self.question_number = (last_question.question_number + 1) if last_question else 1
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['question_number']

# 7. Options
class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )
    option_letter = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')
    ], default='A')
    
    text_en = models.CharField(max_length=500)
    text_hi = models.CharField(max_length=500, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.option_letter}. {self.text_en[:30]}"
    
    class Meta:
        ordering = ['option_letter']

# 8. Mock Test Attempt (Tracks user's test attempts)
class MockTestAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_attempts"
    )
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    
    # Scores and stats
    score = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0)
    
    # Status
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    # Subject-wise performance (for analytics)
    subject_performance = models.JSONField(default=dict, blank=True, 
        help_text="Store performance by subject: {subject_id: {'correct': x, 'wrong': y, 'skipped': z}}")
    
    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Mock Test Attempt"
        verbose_name_plural = "Mock Test Attempts"

    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title} ({self.percentage}%)"

    def save(self, *args, **kwargs):
        if self.total_marks > 0:
            self.percentage = round((self.score / self.total_marks) * 100, 2)
        super().save(*args, **kwargs)

    @property
    def time_taken(self):
        if self.submitted_at:
            delta = self.submitted_at - self.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 0:
                total_seconds = 0
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    def time_remaining(self):
        """Calculate remaining time for in-progress attempts"""
        if self.is_completed or not self.mock_test:
            return 0
        duration = self.mock_test.duration  # minutes
        end_time = self.started_at + timedelta(minutes=duration)
        remaining = (end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))

# 9. User Answer (Tracks individual answers)
class UserAnswer(models.Model):
    attempt = models.ForeignKey(
        MockTestAttempt,
        related_name="answers",
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(
        Option,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.FloatField(default=0)
    time_spent = models.PositiveIntegerField(default=0, help_text="Time spent in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calculate if answer is correct and marks obtained
        if self.selected_option:
            self.is_correct = self.selected_option.is_correct
            if self.is_correct:
                self.marks_obtained = self.question.marks
            else:
                self.marks_obtained = -self.question.negative_marks
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ['attempt', 'question']  # One answer per question per attempt

# 10. User Dashboard Data Models

class UserPerformance(models.Model):
    """Tracks overall user performance across all tests"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="performance"
    )
    total_tests_attempted = models.PositiveIntegerField(default=0)
    total_tests_passed = models.PositiveIntegerField(default=0)
    total_questions_attempted = models.PositiveIntegerField(default=0)
    total_correct_answers = models.PositiveIntegerField(default=0)
    total_wrong_answers = models.PositiveIntegerField(default=0)
    total_skipped_answers = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0)
    highest_score = models.FloatField(default=0)
    total_time_spent = models.PositiveIntegerField(default=0, help_text="Total time in seconds")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Performance"

    def update_stats(self):
        """Update all stats from attempts"""
        attempts = MockTestAttempt.objects.filter(user=self.user, is_completed=True)
        
        self.total_tests_attempted = attempts.count()
        self.total_tests_passed = attempts.filter(percentage__gte=40).count()
        
        # Aggregate answers
        from django.db.models import Sum
        answers = UserAnswer.objects.filter(attempt__user=self.user)
        
        self.total_questions_attempted = answers.count()
        self.total_correct_answers = answers.filter(is_correct=True).count()
        self.total_wrong_answers = answers.filter(is_correct=False, selected_option__isnull=False).count()
        self.total_skipped_answers = answers.filter(selected_option__isnull=True).count()
        
        # Calculate averages
        if self.total_tests_attempted > 0:
            total_percentage = sum(a.percentage for a in attempts)
            self.average_score = round(total_percentage / self.total_tests_attempted, 2)
            self.highest_score = max((a.percentage for a in attempts), default=0)
        
        self.save()

class SubjectPerformance(models.Model):
    """Tracks user performance per subject"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subject_performances"
    )
    subject = models.ForeignKey(
        SubjectMaster,
        on_delete=models.CASCADE,
        related_name="user_performances"
    )
    total_questions_attempted = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(default=0)
    last_attempted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'subject']

    def __str__(self):
        return f"{self.user.username} - {self.subject.name}"

    def update_accuracy(self):
        if self.total_questions_attempted > 0:
            self.accuracy = round((self.correct_answers / self.total_questions_attempted) * 100, 2)
        self.save()

class UserAchievement(models.Model):
    """Tracks user achievements and badges"""
    ACHIEVEMENT_TYPES = [
        ('first_test', 'First Test Completed'),
        ('perfect_score', 'Perfect Score (100%)'),
        ('fast_finisher', 'Fast Finisher'),
        ('consistent_learner', 'Consistent Learner (10 tests)'),
        ('expert_learner', 'Expert Learner (50 tests)'),
        ('subject_master', 'Subject Master (90%+ in a subject)'),
        ('weekly_streak', 'Weekly Streak'),
        ('monthly_streak', 'Monthly Streak'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievements"
    )
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class UserActivity(models.Model):
    """Track user activities for dashboard feed"""
    ACTIVITY_TYPES = [
        ('test_started', 'Test Started'),
        ('test_completed', 'Test Completed'),
        ('achievement_unlocked', 'Achievement Unlocked'),
        ('milestone_reached', 'Milestone Reached'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "User activities"

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"

class UserTestAnalytics(models.Model):
    """Detailed analytics for each test attempt"""
    attempt = models.OneToOneField(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="analytics"
    )
    rank = models.PositiveIntegerField(null=True, blank=True)
    percentile = models.FloatField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    question_wise_time = models.JSONField(default=dict, blank=True)
    subject_wise_accuracy = models.JSONField(default=dict, blank=True)
    difficulty_wise_performance = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Analytics for {self.attempt}"
