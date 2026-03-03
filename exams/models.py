from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# 1. Exam Category
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


# 2. Sub Category
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


# 3. Mock Test
class MockTest(models.Model):
    title = models.CharField(max_length=255)
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mock_tests"
    )
    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
    total_marks = models.FloatField(default=0, help_text="Total marks for this test")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']


# 4. Subject
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


# 5. Question - FIXED VERSION
class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
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

    # English
    question_en = models.TextField()

    # Hindi
    question_hi = models.TextField(blank=True, null=True)

    # FIXED: This is 'explanation' not 'explanation_en'
    explanation = models.TextField(blank=True, null=True)
    
    marks = models.FloatField(default=1, help_text="Marks for this question")
    negative_marks = models.FloatField(default=0.25, help_text="Negative marks for wrong answer")
    
    order = models.PositiveIntegerField(default=0, help_text="Question order in test")
    
    # Add these fields for difficulty and topic
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

# 6. Options
class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )

    text_en = models.CharField(max_length=255)
    text_hi = models.CharField(max_length=255, blank=True, null=True)

    is_correct = models.BooleanField(default=False)
    
    order = models.PositiveIntegerField(default=0, help_text="Option order (1,2,3,4)")

    def __str__(self):
        return self.text_en[:30]
    
    class Meta:
        ordering = ['order']
# 7. Mock Test Attempt - UPDATED with auto-delete fields
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

    # Language preference for this attempt
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text="Language selected by user for this attempt"
    )

    score = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    # NEW FIELDS FOR AUTO-DELETION
    is_archived = models.BooleanField(
        default=False, 
        help_text="Detailed answers archived, only summary kept for rankings"
    )
    permanently_deleted = models.BooleanField(
        default=False,
        help_text="Attempt permanently deleted from database"
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Mock Test Attempt"
        verbose_name_plural = "Mock Test Attempts"
        indexes = [
            models.Index(fields=['user', 'mock_test', 'is_completed']),
            models.Index(fields=['started_at']),
            models.Index(fields=['submitted_at']),  # Add this for faster queries
            models.Index(fields=['is_archived']),   # Add this for filtering
        ]

    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title} - {self.get_language_display()}"

    @property
    def percentage(self):
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.score / self.total_marks) * 100, 2)
    
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
    
    @property
    def time_remaining(self):
        if self.is_completed or self.submitted_at:
            return 0
        duration = self.mock_test.duration
        end_time = self.started_at + timedelta(minutes=duration)
        remaining = (end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))
    
    def calculate_score(self):
        """Calculate and update the score for this attempt"""
        correct = self.answers.filter(is_correct=True).count()
        wrong = self.answers.filter(is_correct=False, selected_option__isnull=False).count()
        skipped = self.answers.filter(selected_option__isnull=True).count()
        
        self.correct_answers = correct
        self.wrong_answers = wrong
        self.skipped_answers = skipped
        
        total_score = 0
        for answer in self.answers.filter(selected_option__isnull=False):
            if answer.is_correct:
                total_score += answer.question.marks
            else:
                total_score -= answer.question.negative_marks
        
        self.score = max(0, total_score)
        self.total_marks = sum(q.marks for q in self.mock_test.questions.all())
        self.save()
        return self.score
    
    def get_question_text(self, question):
        """Get question text in the attempt's language"""
        if self.language == 'hi' and question.question_hi:
            return question.question_hi
        return question.question_en
    
    def get_option_text(self, option):
        """Get option text in the attempt's language"""
        if self.language == 'hi' and option.text_hi:
            return option.text_hi
        return option.text_en
    
    # NEW METHODS FOR AUTO-DELETION
    def should_archive(self):
        """Check if attempt should be archived (keep only summary, delete details)"""
        if self.submitted_at and not self.is_archived:
            days_old = (timezone.now() - self.submitted_at).days
            return days_old >= 7
        return False
    
    def should_permanently_delete(self):
        """Check if attempt should be permanently deleted"""
        if self.submitted_at and not self.permanently_deleted:
            days_old = (timezone.now() - self.submitted_at).days
            return days_old >= 30
        return False
    
    def archive_details(self):
        """Archive this attempt by deleting detailed answers but keeping summary"""
        if self.is_archived:
            return
        
        # Delete all associated UserAnswer records
        answer_count = self.answers.count()
        self.answers.all().delete()
        
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()
        
        return answer_count

    # NEW FIELDS FOR DATA RETENTION
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
    
    # Add index for efficient cleanup queries
    class Meta:
        # ... existing Meta options ...
        indexes = [
            # ... existing indexes ...
            models.Index(fields=['is_paid_user', 'submitted_at', 'has_detailed_data']),
        ]
    
    def should_delete_details(self):
        """Check if detailed answers should be deleted"""
        if self.has_detailed_data and self.submitted_at:
            days_old = (timezone.now() - self.submitted_at).days
            # Delete after 7 days for free users
            return not self.is_paid_user and days_old >= 7
        return False    

# 8. User Answer - with minor improvement for language handling
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
    time_taken = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Time taken in seconds"
    )
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
        if self.selected_option and not self.is_correct:
            self.is_correct = self.selected_option.is_correct
        super().save(*args, **kwargs)
    
    @property
    def time_spent_formatted(self):
        if not self.time_taken:
            return "--:--"
        minutes = self.time_taken // 60
        seconds = self.time_taken % 60
        return f"{minutes}:{seconds:02d}"
    
    # NEW: Get the question text in the attempt's language
    @property
    def question_text(self):
        return self.attempt.get_question_text(self.question)
    
    # NEW: Get the selected option text in the attempt's language
    @property
    def selected_option_text(self):
        if self.selected_option:
            return self.attempt.get_option_text(self.selected_option)
        return "Not Answered"
    
    # NEW: Get the correct option text in the attempt's language
    @property
    def correct_option_text(self):
        correct_option = self.question.options.filter(is_correct=True).first()
        if correct_option:
            return self.attempt.get_option_text(correct_option)
        return "No correct option found"
# models.py - Add this Testimonial model
# models.py - Add this model

class Testimonial(models.Model):
    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
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
    
    # Admin control fields
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
        return f"{self.user.username} - {self.stars} Stars"
    
    def user_name(self):
        """Get user's full name or username"""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    def user_initials(self):
        """Get user initials for avatar"""
        name = self.user_name()
        if ' ' in name:
            parts = name.split()
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return name[:2].upper()