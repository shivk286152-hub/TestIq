from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

# ============================================
# EXAM CATEGORY MODELS
# ============================================

class ExamCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="category_logos/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Exam Categories"


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


# ============================================
# MOCK TEST MODEL
# ============================================

class MockTest(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]

    NEGATIVE_MARKING_TYPES = [
        ('no_negative', 'No Negative Marking'),
        ('fixed_per_question', 'Fixed per Wrong Question'),
        ('percentage_of_marks', 'Percentage of Question Marks'),
        ('per_question', 'Per Question Negative Marking'),  # NEW: Per question control
    ]

    title = models.CharField(max_length=255)

    subcategory = models.ForeignKey(
        'SubCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mock_tests"
    )

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='medium',
        help_text="Overall difficulty level of the mock test"
    )

    negative_marking_type = models.CharField(
        max_length=25,
        choices=NEGATIVE_MARKING_TYPES,
        default='no_negative'
    )

    negative_marking_value = models.FloatField(
        default=0,
        blank=True,
        help_text="Negative marks or percentage depending on type"
    )

    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit per attempt in minutes")

    total_questions = models.PositiveIntegerField(default=0, help_text="Total number of questions")
    total_marks = models.FloatField(default=0, help_text="Total marks for the test")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if self.negative_marking_type != 'no_negative' and self.negative_marking_value <= 0:
            raise ValidationError({
                'negative_marking_value': 'Negative marking value must be greater than 0.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def has_negative_marking(self):
        return self.negative_marking_type != 'no_negative'

    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def difficulty_display(self):
        return self.get_difficulty_display()

    def calculate_negative_marks(self, question_marks, question_difficulty=None):
        """
        Calculate negative marks for a wrong answer
        Now supports per-question negative marking with difficulty-based defaults
        """
        if self.negative_marking_type == 'fixed_per_question':
            return self.negative_marking_value
        elif self.negative_marking_type == 'percentage_of_marks':
            return (question_marks * self.negative_marking_value) / 100
        elif self.negative_marking_type == 'per_question':
            # If per-question negative marking is enabled, use question's own negative_marks
            # This will be handled in Question.get_effective_negative_marks()
            return None
        return 0

    def update_totals(self):
        """Auto-update total_questions and total_marks based on questions"""
        self.total_questions = self.questions.count()
        self.total_marks = sum(q.marks for q in self.questions.all())
        super().save(update_fields=['total_questions', 'total_marks'])


# ============================================
# SUBJECT MODEL
# ============================================

class Subject(models.Model):
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=100)
    start_question_no = models.PositiveIntegerField()
    end_question_no = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} ({self.start_question_no}-{self.end_question_no})"
    
    class Meta:
        ordering = ['start_question_no']


# ============================================
# QUESTION MODEL
# ============================================

class Question(models.Model):
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    # Default negative marks by difficulty
    DIFFICULTY_NEGATIVE_MARKS = {
        'Easy': 0.25,
        'Medium': 0.33,
        'Hard': 0.50,
    }
    
    # Relationships
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    subject = models.ForeignKey(
        Subject,
        related_name="questions",
        on_delete=models.CASCADE
    )

    # Question Content (Bilingual)
    question_en = models.TextField(verbose_name="Question (English)")
    question_hi = models.TextField(blank=True, null=True, verbose_name="Question (Hindi)")

    # Explanation (Bilingual)
    explanation = models.TextField(blank=True, null=True, verbose_name="Explanation (English)")
    explanation_hi = models.TextField(blank=True, null=True, verbose_name="Explanation (Hindi)")
    
    # Scoring Configuration
    marks = models.FloatField(default=1, help_text="Marks for this question")
    
    # Negative marking per question
    # If null/blank, uses test's negative marking settings
    # If test has per_question marking, this value will be used
    negative_marks = models.FloatField(
        null=True, 
        blank=True,
        help_text="Negative marks for this question. If blank, uses difficulty-based default or test default."
    )
    
    # Override test's negative marking for this specific question
    override_test_negative = models.BooleanField(
        default=False,
        help_text="Check to use this question's negative marks instead of test defaults"
    )
    
    # Question Metadata
    order = models.PositiveIntegerField(default=0, help_text="Question order in test")
    difficulty = models.CharField(
        max_length=10, 
        choices=DIFFICULTY_CHOICES, 
        default='Medium',
        help_text="Difficulty level of the question"
    )
    topic = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="e.g., Algebra, Grammar, Modern History"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_en[:50]
    
    class Meta:
        ordering = ['order', 'id']
    
    def get_effective_negative_marks(self):
        """
        Get the effective negative marks for this question based on priority:
        1. If override_test_negative is True and negative_marks is set, use that
        2. If test has per_question marking, use difficulty-based default
        3. Otherwise use test's negative marking configuration
        """
        # Check if question overrides test negative marking
        if self.override_test_negative and self.negative_marks is not None:
            return self.negative_marks
        
        # Check if test uses per-question marking
        if self.mock_test.negative_marking_type == 'per_question':
            # Use difficulty-based default
            return self.DIFFICULTY_NEGATIVE_MARKS.get(self.difficulty, 0.25)
        
        # Otherwise use test's negative marking
        test_negative = self.mock_test.calculate_negative_marks(self.marks, self.difficulty)
        return test_negative if test_negative is not None else 0
    
    def get_question_text(self, language='en'):
        if language == 'hi' and self.question_hi:
            return self.question_hi
        return self.question_en
    
    def get_explanation_text(self, language='en'):
        if language == 'hi' and self.explanation_hi:
            return self.explanation_hi
        return self.explanation or "No explanation available"


# ============================================
# OPTION MODEL
# ============================================

class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )

    text_en = models.CharField(max_length=255, verbose_name="Option (English)")
    text_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option (Hindi)")

    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, help_text="Option order (1,2,3,4)")

    def __str__(self):
        return self.text_en[:30]
    
    class Meta:
        ordering = ['order']
    
    def get_text(self, language='en'):
        if language == 'hi' and self.text_hi:
            return self.text_hi
        return self.text_en


# ============================================
# MOCK TEST ATTEMPT
# ============================================

class MockTestAttempt(models.Model):
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'हिन्दी (Hindi)'),
    ]
    
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

    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text="Language selected by user for this attempt"
    )

    # Scoring Results
    raw_score = models.FloatField(default=0, help_text="Score without negative marking")
    score_with_negative = models.FloatField(default=0, help_text="Score with negative marking applied")
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)
    
    # Additional stats
    negative_marks_applied = models.FloatField(default=0, help_text="Total negative marks deducted")

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
            models.Index(fields=['submitted_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title}"

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
    def accuracy_with_negative(self):
        """
        Calculate accuracy considering negative marking
        Accuracy = (Score with negative / Total possible marks) * 100
        """
        if not self.total_marks or self.total_marks == 0:
            return 0
        return self.percentage_with_negative
    
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
    
    def calculate_scores(self):
        """
        Calculate all scores for this attempt
        Formula: Score = sum(correct * marks) - sum(wrong * negative_marks)
        """
        correct_count = 0
        wrong_count = 0
        skipped_count = 0
        raw_total = 0
        score_with_negative = 0
        total_negative_applied = 0
        
        for answer in self.answers.all():
            question = answer.question
            
            if not answer.selected_option:
                skipped_count += 1
                continue
            
            if answer.selected_option.is_correct:
                correct_count += 1
                raw_total += question.marks
                score_with_negative += question.marks
            else:
                wrong_count += 1
                negative = question.get_effective_negative_marks()
                total_negative_applied += negative
                score_with_negative -= negative
        
        self.correct_answers = correct_count
        self.wrong_answers = wrong_count
        self.skipped_answers = skipped_count
        self.raw_score = raw_total
        self.score_with_negative = max(0, score_with_negative)  # Ensure non-negative
        self.negative_marks_applied = total_negative_applied
        self.total_marks = sum(q.marks for q in self.mock_test.questions.all())
        
        self.save()
        return self.score_with_negative


# ============================================
# USER ANSWER MODEL
# ============================================

class UserAnswer(models.Model):
    
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
    
    is_correct = models.BooleanField(default=False)
    time_taken = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        unique_together = ['attempt', 'question']

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{self.attempt.user.username} - Q{self.question.id} {status}"
    
    def save(self, *args, **kwargs):
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


# ============================================
# TESTIMONIAL MODEL
# ============================================

class Testimonial(models.Model):
    
    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
    
    text = models.TextField(max_length=500)
    stars = models.IntegerField(
        default=5,
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]
    )
    achievement = models.CharField(max_length=200, blank=True)
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-is_featured', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.stars} Stars"
    
    def user_name(self):
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username


# Add this to your exams/models.py

class FAQ(models.Model):
    """Frequently Asked Questions model"""
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=100, blank=True, null=True, 
                                help_text="e.g., General, Account, Test Related")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return self.question[:50]        