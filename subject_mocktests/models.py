from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

# ============================================
# SUBJECT MODEL - Main subject category
# ============================================

class Subject(models.Model):
    """Main subject for mock tests"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="subject_icons/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ============================================
# TOPIC MODEL - Topics under subjects
# ============================================

class Topic(models.Model):
    """Topics under a subject"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['subject', 'name']
    
    def __str__(self):
        return f"{self.subject.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Topic.objects.filter(subject=self.subject, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


# ============================================
# MOCK TEST MODEL
# ============================================

class MockTest(models.Model):
    """Mock test model - uses exams app's attempt models"""
    
    NEGATIVE_MARKING_TYPES = [
        ('no_negative', 'No Negative Marking'),
        ('fixed_per_question', 'Fixed per Wrong Question'),
        ('percentage_of_marks', 'Percentage of Question Marks'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="mock_tests")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="mock_tests")
    
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    
    negative_marking_type = models.CharField(max_length=25, choices=NEGATIVE_MARKING_TYPES, default='no_negative')
    negative_marking_value = models.FloatField(default=0, blank=True)
    
    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    total_questions = models.PositiveIntegerField(default=0)
    total_marks = models.FloatField(default=0)
    
    is_active = models.BooleanField(default=True)
    is_free = models.BooleanField(default=True)
    
    instructions = models.TextField(default="Read each question carefully before answering.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'is_active']),
            models.Index(fields=['topic', 'is_active']),
        ]
    
    def __str__(self):
        if self.topic:
            return f"{self.subject.name} - {self.topic.name} - {self.title}"
        return f"{self.subject.name} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def calculate_negative_marks(self, question_marks):
        """Calculate negative marks for a wrong answer"""
        if self.negative_marking_type == 'fixed_per_question':
            return self.negative_marking_value
        elif self.negative_marking_type == 'percentage_of_marks':
            return (question_marks * self.negative_marking_value) / 100
        return 0
    
    def update_totals(self):
        """Update total questions and marks"""
        self.total_questions = self.questions.count()
        self.total_marks = sum(q.marks for q in self.questions.all())
        self.save(update_fields=['total_questions', 'total_marks'])


# ============================================
# QUESTION MODEL
# ============================================

class Question(models.Model):
    """Individual question model"""
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    # Default negative marks by difficulty (for compatibility with first app)
    DIFFICULTY_NEGATIVE_MARKS = {
        'Easy': 0.25,
        'Medium': 0.33,
        'Hard': 0.50,
    }
    
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name="questions")
    
    question_en = models.TextField(verbose_name="Question (English)")
    question_hi = models.TextField(blank=True, null=True, verbose_name="Question (Hindi)")
    
    explanation_en = models.TextField(blank=True, null=True, verbose_name="Explanation (English)")
    explanation_hi = models.TextField(blank=True, null=True, verbose_name="Explanation (Hindi)")
    
    marks = models.FloatField(default=1)
    negative_marks_override = models.FloatField(null=True, blank=True)
    
    order = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    topic = models.CharField(max_length=200, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.question_en[:50]
    
    def get_effective_negative_marks(self):
        """Get effective negative marks (compatible with first app)"""
        if self.negative_marks_override is not None:
            return self.negative_marks_override
        
        # Use difficulty-based default
        return self.DIFFICULTY_NEGATIVE_MARKS.get(self.difficulty, 0.25)
    
    def get_question_text(self, language='en'):
        if language == 'hi' and self.question_hi:
            return self.question_hi
        return self.question_en
    
    def get_explanation_text(self, language='en'):
        if language == 'hi' and self.explanation_hi:
            return self.explanation_hi
        return self.explanation_en or "No explanation available"


# ============================================
# OPTION MODEL
# ============================================

class Option(models.Model):
    """Answer options for questions"""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    
    text_en = models.CharField(max_length=500, verbose_name="Option (English)")
    text_hi = models.CharField(max_length=500, blank=True, null=True, verbose_name="Option (Hindi)")
    
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text_en[:30]
    
    def get_text(self, language='en'):
        if language == 'hi' and self.text_hi:
            return self.text_hi
        return self.text_en


# ============================================
# MOCK TEST ATTEMPT - Updated to match first app's fields
# ============================================

class MockTestAttempt(models.Model):
    """
    Subject mock test attempt with fields matching first app's expectations
    """
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'हिन्दी (Hindi)'),
    ]
    
    # Link to exams app attempt (optional - created after submission)
    exams_attempt = models.OneToOneField(
        'exams.MockTestAttempt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subject_attempt'
    )
    
    # Subject-specific relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subject_mock_attempts"
    )
    
    mock_test = models.ForeignKey(
        'MockTest',
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    
    # Attempt Configuration
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en'
    )
    
    # Scoring Results - ADDED FIELDS to match first app
    raw_score = models.FloatField(default=0, help_text="Score without negative marking")
    score_with_negative = models.FloatField(default=0, help_text="Score with negative marking applied")
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)
    negative_marks_applied = models.FloatField(default=0, help_text="Total negative marks deducted")
    
    # Keep score field for backward compatibility
    score = models.FloatField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    # Data Retention
    is_archived = models.BooleanField(default=False)
    permanently_deleted = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_paid_user = models.BooleanField(default=False)
    details_deleted_at = models.DateTimeField(null=True, blank=True)
    has_detailed_data = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=['user', 'mock_test', 'is_completed']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title}"
    
    @property
    def percentage(self):
        """Calculate percentage score (for compatibility)"""
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.score / self.total_marks) * 100, 2)
    
    @property
    def percentage_with_negative(self):
        """Calculate percentage score with negative marking"""
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.score_with_negative / self.total_marks) * 100, 2)
    
    @property
    def percentage_raw(self):
        """Calculate raw percentage (without negative)"""
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.raw_score / self.total_marks) * 100, 2)
    
    @property
    def time_taken(self):
        """Calculate time taken to complete the test"""
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
    
    def calculate_scores(self):
        """Calculate all scores for this attempt (compatible with first app)"""
        answers = UserAnswer.objects.filter(attempt=self)
        
        correct = 0
        wrong = 0
        skipped = 0
        raw_total = 0
        score_with_negative = 0
        negative_total = 0
        
        for answer in answers:
            question = answer.question
            
            if not answer.selected_option:
                skipped += 1
                continue
            
            if answer.is_correct:
                correct += 1
                raw_total += question.marks
                score_with_negative += question.marks
            else:
                wrong += 1
                negative = question.get_effective_negative_marks()
                negative_total += negative
                score_with_negative -= negative
        
        self.correct_answers = correct
        self.wrong_answers = wrong
        self.skipped_answers = skipped
        self.raw_score = raw_total
        self.score_with_negative = max(0, score_with_negative)
        self.negative_marks_applied = negative_total
        self.score = self.score_with_negative  # Keep score field in sync
        self.total_marks = sum(q.marks for q in self.mock_test.questions.all())
        
        self.save()
        return self.score_with_negative
    
    def create_exams_attempt(self):
        """Create a corresponding exams app attempt"""
        from exams.models import MockTestAttempt as ExamsMockTestAttempt
        
        exams_attempt = ExamsMockTestAttempt.objects.create(
            user=self.user,
            mock_test_id=self.mock_test_id,
            language=self.language,
            raw_score=self.raw_score,
            score_with_negative=self.score_with_negative,
            total_marks=self.total_marks,
            correct_answers=self.correct_answers,
            wrong_answers=self.wrong_answers,
            skipped_answers=self.skipped_answers,
            negative_marks_applied=self.negative_marks_applied,
            started_at=self.started_at,
            submitted_at=self.submitted_at,
            is_completed=self.is_completed,
            has_detailed_data=self.has_detailed_data
        )
        
        self.exams_attempt = exams_attempt
        self.save()
        return exams_attempt


# ============================================
# USER ANSWER MODEL
# ============================================

class UserAnswer(models.Model):
    """
    Subject user answer that links to exams app answer
    """
    
    # Link to exams app answer
    exams_answer = models.OneToOneField(
        'exams.UserAnswer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subject_answer'
    )
    
    # Relationships
    attempt = models.ForeignKey(
        MockTestAttempt,
        related_name="answers",
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE,
        related_name="user_answers"
    )
    selected_option = models.ForeignKey(
        Option,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_answers"
    )
    
    # Answer Status
    is_correct = models.BooleanField(default=False)
    time_taken = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Time taken in seconds"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['attempt', 'question']),
        ]
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{self.attempt.user.username} - Q{self.question.id} {status}"
    
    def save(self, *args, **kwargs):
        """Auto-set is_correct based on selected option"""
        if self.selected_option and not self.is_correct:
            self.is_correct = self.selected_option.is_correct
        super().save(*args, **kwargs)
    
    @property
    def marks_obtained(self):
        """Calculate marks obtained for this answer (with negative marking)"""
        if not self.selected_option:
            return 0
        if self.is_correct:
            return self.question.marks
        else:
            return -self.question.get_effective_negative_marks()
    
    @property
    def negative_marks(self):
        """Get negative marks for this answer if wrong"""
        if self.selected_option and not self.is_correct:
            return self.question.get_effective_negative_marks()
        return 0
    
    def create_exams_answer(self, exams_attempt):
        """Create a corresponding exams app answer"""
        from exams.models import UserAnswer as ExamsUserAnswer
        
        exams_answer = ExamsUserAnswer.objects.create(
            attempt=exams_attempt,
            question_id=self.question_id,
            selected_option_id=self.selected_option_id if self.selected_option else None,
            is_correct=self.is_correct,
            time_taken=self.time_taken
        )
        
        self.exams_answer = exams_answer
        self.save()
        return exams_answer