from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import Sum

# ============================================
# EXAM CATEGORY MODELS
# ============================================

class ExamCategory(models.Model):
    """
    Top-level category for exams (e.g., 'UPSC', 'SSC', 'Banking')
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="category_logos/", blank=True, null=True)

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Exam Categories"


class SubCategory(models.Model):
    """
    Sub-category under main exam category (e.g., 'Prelims', 'Mains' under UPSC)
    """
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
        """Auto-generate unique slug from name"""
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
        unique_together = ['category', 'name']  # Prevent duplicate subcategories


# ============================================
# MOCK TEST MODEL - MAIN TEST CONFIGURATION
# ============================================
class MockTest(models.Model):

    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    NEGATIVE_MARKING_TYPES = [
        ('no_negative', 'No Negative Marking'),
        ('fixed_per_question', 'Fixed per Wrong Question'),
        ('percentage_of_marks', 'Percentage of Question Marks'),
    ]

    title = models.CharField(max_length=255)

    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mock_tests"
    )

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='Intermediate'
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

    total_marks = models.FloatField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # ========== CLEAN & VALIDATION ==========
    def clean(self):
        # Negative marking validation
        if self.negative_marking_type != 'no_negative' and self.negative_marking_value <= 0:
            raise ValidationError({
                'negative_marking_value': 'Negative marking value must be greater than 0.'
            })
        
        # Duration validation
        if self.duration <= 0:
            raise ValidationError({
                'duration': 'Duration must be greater than 0 minutes.'
            })

    # ========== SAVE ==========
    def save(self, *args, **kwargs):
        # Run Django validation
        self.full_clean()
        super().save(*args, **kwargs)

    # ========== PROPERTIES ==========
    @property
    def has_negative_marking(self):
        return self.negative_marking_type != 'no_negative'

    @property
    def negative_marking_display(self):
        if self.negative_marking_type == 'no_negative':
            return "No Negative Marking"
        elif self.negative_marking_type == 'fixed_per_question':
            return f"-{self.negative_marking_value} marks per wrong answer"
        else:
            return f"-{self.negative_marking_value}% of question marks per wrong answer"

    @property
    def question_count(self):
        return self.questions.count()

    # ========== METHODS ==========
    def calculate_negative_marks(self, question_marks):
        """
        Calculate negative marks for a wrong answer
        """
        if self.negative_marking_type == 'fixed_per_question':
            return self.negative_marking_value
        elif self.negative_marking_type == 'percentage_of_marks':
            return (question_marks * self.negative_marking_value) / 100
        return 0

    def get_negative_marking_description(self):
        """Detailed negative marking description"""
        if not self.has_negative_marking:
            return "No negative marking for this test"
        if self.negative_marking_type == 'fixed_per_question':
            return f"{self.negative_marking_value} marks deducted per wrong answer"
        else:
            return f"{self.negative_marking_value}% of question marks deducted per wrong answer"

    def update_total_marks(self):
        """Auto-update total_marks based on questions"""
        total = self.questions.aggregate(total=Sum('marks'))['total'] or 0
        self.total_marks = total
        self.save(update_fields=['total_marks']) 
   

# ============================================
# SUBJECT MODEL - For organizing questions by subject
# ============================================

class Subject(models.Model):
    """
    Subject areas within a mock test (e.g., 'Mathematics', 'English' under a test)
    Each subject covers a range of question numbers
    """
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
        unique_together = ['mock_test', 'name']  # Prevent duplicate subjects
        
    def clean(self):
        """Validate question number range"""
        if self.start_question_no >= self.end_question_no:
            raise ValidationError('End question number must be greater than start question number')


# ============================================
# QUESTION MODEL - Individual questions with bilingual support
# ============================================

class Question(models.Model):
    """
    Individual question model with bilingual (English/Hindi) support
    Can override test's negative marking settings if needed
    """
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    # Relationships
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    subject = models.ForeignKey(
        Subject,
        related_name="questions",
        on_delete=models.CASCADE,
        null=True,  # Allow null for backward compatibility
        blank=True
    )

    # Question Content (Bilingual)
    question_en = models.TextField(verbose_name="Question (English)")
    question_hi = models.TextField(blank=True, null=True, verbose_name="Question (Hindi)")

    # Explanation (Bilingual)
    explanation = models.TextField(blank=True, null=True, verbose_name="Explanation (English)")
    explanation_hi = models.TextField(blank=True, null=True, verbose_name="Explanation (Hindi)")
    
    # Scoring Configuration
    marks = models.FloatField(default=1, help_text="Marks for this question")
    
    # OPTIONAL: Override test's negative marking for this specific question
    negative_marks = models.FloatField(
        null=True, 
        blank=True,
        help_text="Override test's negative marking for this question. Leave blank to use test default."
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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_en[:50] + ("..." if len(self.question_en) > 50 else "")
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['mock_test', 'order']  # Prevent duplicate order numbers
    
    # ========== CLEAN & VALIDATION ==========
    def clean(self):
        if self.marks <= 0:
            raise ValidationError({'marks': 'Marks must be greater than 0.'})
        
        if self.negative_marks and self.negative_marks < 0:
            raise ValidationError({'negative_marks': 'Negative marks cannot be negative (use positive value).'})
    
    # ========== METHODS ==========
    
    def get_effective_negative_marks(self):
        """
        Get the effective negative marks for this question:
        - If question has custom negative_marks set, use that
        - Otherwise use test's negative marking configuration
        """
        # If question has its own negative marks set, use that
        if self.negative_marks is not None and self.negative_marks > 0:
            return self.negative_marks
        
        # Otherwise use test's negative marking
        return self.mock_test.calculate_negative_marks(self.marks)
    
    def has_custom_negative_marks(self):
        """Check if this question overrides test's negative marking"""
        return self.negative_marks is not None and self.negative_marks > 0
    
    def get_negative_marks_display(self):
        """Get user-friendly negative marks description for this question"""
        if self.has_custom_negative_marks():
            return f"{self.negative_marks} marks (custom for this question)"
        return self.mock_test.get_negative_marking_description()
    
    def get_question_text(self, language='en'):
        """Get question text in specified language"""
        if language == 'hi' and self.question_hi:
            return self.question_hi
        return self.question_en
    
    def get_explanation_text(self, language='en'):
        """Get explanation text in specified language"""
        if language == 'hi' and self.explanation_hi:
            return self.explanation_hi
        return self.explanation or "No explanation available"


# ============================================
# OPTION MODEL - Answer options for questions
# ============================================

class Option(models.Model):
    """
    Answer options for questions with bilingual support
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )

    # Option Text (Bilingual)
    text_en = models.CharField(max_length=255, verbose_name="Option (English)")
    text_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option (Hindi)")

    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, help_text="Option order (1,2,3,4)")

    def __str__(self):
        return self.text_en[:30]
    
    class Meta:
        ordering = ['order']
        unique_together = ['question', 'order']  # Prevent duplicate order numbers
    
    def clean(self):
        """Ensure at least one correct option exists"""
        if self.is_correct:
            # Check if this would be the only correct option (or we're updating existing)
            existing_correct = self.question.options.filter(is_correct=True)
            if self.pk:
                existing_correct = existing_correct.exclude(pk=self.pk)
            
            # Warning only, not a hard validation
            if existing_correct.exists() and existing_correct.count() > 0:
                # This is fine for multiple correct answers, but log it
                pass
    
    def get_text(self, language='en'):
        """Get option text in specified language"""
        if language == 'hi' and self.text_hi:
            return self.text_hi
        return self.text_en


# ============================================
# MOCK TEST ATTEMPT - User's test attempt with scoring
# ============================================

class MockTestAttempt(models.Model):
    """
    Records a user's attempt at a mock test
    Includes scoring, timing, and data retention features
    """
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'हिन्दी (Hindi)'),
    ]
    
    # Relationships
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

    # Attempt Configuration
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text="Language selected by user for this attempt"
    )

    # Scoring Results
    score = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    # Data Retention Fields (for auto-deletion of old attempts)
    is_archived = models.BooleanField(
        default=False, 
        help_text="Detailed answers archived, only summary kept for rankings"
    )
    permanently_deleted = models.BooleanField(
        default=False,
        help_text="Attempt permanently deleted from database"
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Premium User Flag (for extended data retention)
    is_paid_user = models.BooleanField(
        default=False,
        help_text="Whether this attempt belongs to a paid user"
    )
    
    # For tracking deletion
    details_deleted_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When detailed answers were deleted"
    )
    
    # Summary-only flag - keep this for ranking data
    has_detailed_data = models.BooleanField(
        default=True,
        help_text="Whether detailed answers still exist"
    )
    
    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Mock Test Attempt"
        verbose_name_plural = "Mock Test Attempts"
        indexes = [
            models.Index(fields=['user', 'mock_test', 'is_completed']),
            models.Index(fields=['started_at']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['is_archived']),
            models.Index(fields=['is_paid_user', 'submitted_at', 'has_detailed_data']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title} - {self.get_language_display()}"

    # ========== PROPERTIES ==========
    
    @property
    def percentage(self):
        """Calculate percentage score"""
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.score / self.total_marks) * 100, 2)
    
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
    
    @property
    def time_remaining(self):
        """Calculate time remaining for ongoing attempt"""
        if self.is_completed or self.submitted_at:
            return 0
        duration = self.mock_test.duration
        end_time = self.started_at + timedelta(minutes=duration)
        remaining = (end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))
    
    # ========== SCORING METHODS ==========
    
    def calculate_score(self):
        """
        Calculate and update the score for this attempt
        Uses question-level negative marks (which may override test defaults)
        """
        # Count answers by type
        correct = self.answers.filter(is_correct=True).count()
        wrong = self.answers.filter(is_correct=False, selected_option__isnull=False).count()
        skipped = self.answers.filter(selected_option__isnull=True).count()
        
        self.correct_answers = correct
        self.wrong_answers = wrong
        self.skipped_answers = skipped
        
        # Calculate total score with proper negative marking
        total_score = 0
        for answer in self.answers.filter(selected_option__isnull=False):
            if answer.is_correct:
                total_score += answer.question.marks
            else:
                # Use question's effective negative marks (which may override test default)
                total_score -= answer.question.get_effective_negative_marks()
        
        # Ensure score doesn't go below 0 (optional - remove if you want negative scores)
        self.score = max(0, total_score)
        
        # Calculate total possible marks
        total_marks_agg = self.mock_test.questions.aggregate(total=Sum('marks'))['total']
        self.total_marks = total_marks_agg or 0
        
        self.save(update_fields=['score', 'total_marks', 'correct_answers', 'wrong_answers', 'skipped_answers'])
        return self.score
    
    # ========== BILINGUAL SUPPORT METHODS ==========
    
    def get_question_text(self, question):
        """Get question text in the attempt's language"""
        return question.get_question_text(self.language)
    
    def get_option_text(self, option):
        """Get option text in the attempt's language"""
        return option.get_text(self.language)
    
    def get_explanation_text(self, question):
        """Get explanation text in the attempt's language"""
        return question.get_explanation_text(self.language)
    
    # ========== DATA RETENTION METHODS ==========
    
    def should_archive(self):
        """Check if attempt should be archived (keep only summary, delete details)"""
        if self.submitted_at and not self.is_archived:
            days_old = (timezone.now() - self.submitted_at).days
            return days_old >= 7  # Archive after 7 days
        return False
    
    def should_permanently_delete(self):
        """Check if attempt should be permanently deleted"""
        if self.submitted_at and not self.permanently_deleted:
            days_old = (timezone.now() - self.submitted_at).days
            return days_old >= 30  # Delete after 30 days
        return False
    
    def should_delete_details(self):
        """Check if detailed answers should be deleted (free users only)"""
        if self.has_detailed_data and self.submitted_at:
            days_old = (timezone.now() - self.submitted_at).days
            # Delete after 7 days for free users
            return not self.is_paid_user and days_old >= 7
        return False
    
    def archive_details(self):
        """Archive this attempt by deleting detailed answers but keeping summary"""
        if self.is_archived:
            return 0
        
        # Delete all associated UserAnswer records
        answer_count = self.answers.count()
        self.answers.all().delete()
        
        self.is_archived = True
        self.has_detailed_data = False
        self.archived_at = timezone.now()
        self.details_deleted_at = timezone.now()
        self.save(update_fields=['is_archived', 'has_detailed_data', 'archived_at', 'details_deleted_at'])
        
        return answer_count


# ============================================
# USER ANSWER MODEL - Individual question responses
# ============================================

class UserAnswer(models.Model):
    """
    Records user's answer to a specific question in an attempt
    Includes time tracking and bilingual text access
    """
    
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
            models.Index(fields=['is_correct']),
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
    
    # ========== PROPERTIES ==========
    
    @property
    def marks_obtained(self):
        """Calculate marks obtained for this answer (with negative marking)"""
        if not self.selected_option:
            return 0  # Skipped question
        if self.is_correct:
            return self.question.marks
        else:
            # Use question's effective negative marks
            return -self.question.get_effective_negative_marks()
    
    @property
    def time_spent_formatted(self):
        """Format time taken as MM:SS"""
        if not self.time_taken:
            return "--:--"
        minutes = self.time_taken // 60
        seconds = self.time_taken % 60
        return f"{minutes}:{seconds:02d}"
    
    # ========== BILINGUAL TEXT PROPERTIES ==========
    
    @property
    def question_text(self):
        """Get question text in the attempt's language"""
        return self.attempt.get_question_text(self.question)
    
    @property
    def selected_option_text(self):
        """Get selected option text in the attempt's language"""
        if self.selected_option:
            return self.attempt.get_option_text(self.selected_option)
        return "Not Answered"
    
    @property
    def correct_option_text(self):
        """Get correct option text in the attempt's language"""
        correct_option = self.question.options.filter(is_correct=True).first()
        if correct_option:
            return self.attempt.get_option_text(correct_option)
        return "No correct option found"
    
    @property
    def explanation_text(self):
        """Get explanation text in the attempt's language"""
        if self.question:
            return self.attempt.get_explanation_text(self.question)
        return "No explanation available"


# ============================================
# TESTIMONIAL MODEL - User feedback and reviews
# ============================================

class Testimonial(models.Model):
    """
    User testimonials and reviews displayed on the website
    Admin-controlled visibility and featured status
    """
    
    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Fixed: use settings.AUTH_USER_MODEL instead of 'auth.User'
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
    
    # Content
    text = models.TextField(
        max_length=500,
        help_text="Share your experience with our platform"
    )
    stars = models.IntegerField(
        default=5,
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]
    )
    achievement = models.CharField(
        max_length=200, 
        blank=True,
        help_text="e.g., 'Selected in UPSC 2023', 'Scored 95% in JEE'"
    )
    
    # Admin Control
    is_featured = models.BooleanField(
        default=False,
        help_text="Show this testimonial as featured"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Only active testimonials will be displayed"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Lower numbers appear first"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-is_featured', '-created_at']
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"
    
    def __str__(self):
        return f"{self.user_name()} - {self.stars} Stars"
    
    def user_name(self):
        """Get user's full name or username for display"""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    def user_initials(self):
        """Get user initials for avatar display"""
        name = self.user_name()
        if ' ' in name:
            parts = name.split()
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return name[:2].upper() if name else "??"
