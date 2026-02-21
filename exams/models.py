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


# 7. Mock Test Attempt
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

    score = models.FloatField(default=0)
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Mock Test Attempt"
        verbose_name_plural = "Mock Test Attempts"

    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title}"

    @property
    def percentage(self):
        if not self.total_marks:
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


# 8. User Answer
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