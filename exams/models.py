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
<<<<<<< HEAD
        return self.name

# 2. Sub Category (CGL, CHSL, PO, Clerk)
=======
     return self.name
    
    class Meta:
        verbose_name_plural = "Exam Categories"


# 2. Sub Category
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
    slug = models.SlugField(unique=True, blank=True)

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
<<<<<<< HEAD
        "SubCategory",
=======
        SubCategory,
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
<<<<<<< HEAD
    
    def __str__(self):
        return self.title

# 4. Subject (Maths, Reasoning, English, GK)
=======
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']


# 4. Subject
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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

<<<<<<< HEAD
# 5. Question
=======

# 5. Question - FIXED VERSION
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
class Question(models.Model):
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

<<<<<<< HEAD
# 7. Mock Test Attempt (YOUR EXISTING MODEL - UNCHANGED)
=======

# 7. Mock Test Attempt
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
<<<<<<< HEAD
    percentage.fget.short_description = "Percentage (%)"

    # Time taken property as HH:MM:SS
=======
    
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
<<<<<<< HEAD
    time_taken.fget.short_description = "Time Taken"
    
    # Server timer
    def time_remaining(self):
        duration = self.mock_test.duration  # minutes
        end_time = self.started_at + timedelta(minutes=duration)
        remaining = (end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))

# 8. User Answer (YOUR EXISTING MODEL - UNCHANGED)
=======
    
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
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
<<<<<<< HEAD

# ========== NEW MODELS FOR RANKING FEATURE ==========

class TestRank(models.Model):
    """Stores rank information for each test attempt"""
    attempt = models.OneToOneField(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="rank_info"
    )
    rank = models.PositiveIntegerField()
    total_participants = models.PositiveIntegerField()
    percentile = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['rank']
        unique_together = ['attempt', 'rank']
    
    def __str__(self):
        return f"{self.attempt.user.username} - Rank {self.rank}/{self.total_participants}"
    
    @property
    def is_top_three(self):
        return self.rank <= 3
    
    @property
    def is_top_ten(self):
        return self.rank <= 10

class TopRanker(models.Model):
    """Cache table for top rankers to improve performance"""
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="top_rankers"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="top_ranks"
    )
    attempt = models.ForeignKey(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="top_ranker_info"
    )
    rank = models.PositiveIntegerField()
    percentage = models.FloatField()
    time_taken = models.CharField(max_length=20)  # Store as HH:MM:SS
    achieved_at = models.DateTimeField()
    
    class Meta:
        ordering = ['rank']
        unique_together = ['mock_test', 'rank']
    
    def __str__(self):
        medal = "🥇" if self.rank == 1 else "🥈" if self.rank == 2 else "🥉" if self.rank == 3 else ""
        return f"{medal} Rank {self.rank}: {self.user.username} - {self.percentage}%"

class UserRankHistory(models.Model):
    """Tracks user's rank history across different tests"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rank_history"
    )
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE,
        related_name="rank_history"
    )
    attempt = models.ForeignKey(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="rank_history"
    )
    rank = models.PositiveIntegerField()
    total_participants = models.PositiveIntegerField()
    percentile = models.FloatField()
    achieved_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-achieved_at']
        verbose_name_plural = "User Rank Histories"
    
    def __str__(self):
        return f"{self.user.username} - {self.mock_test.title} - Rank {self.rank}"

class RankStatistics(models.Model):
    """Overall ranking statistics for each mock test"""
    mock_test = models.OneToOneField(
        MockTest,
        on_delete=models.CASCADE,
        related_name="rank_stats"
    )
    total_attempts = models.PositiveIntegerField(default=0)
    highest_score = models.FloatField(default=0)
    lowest_score = models.FloatField(default=0)
    average_score = models.FloatField(default=0)
    top_rankers_count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats for {self.mock_test.title}"
    
    def update_stats(self):
        """Update statistics based on completed attempts"""
        completed_attempts = MockTestAttempt.objects.filter(
            mock_test=self.mock_test,
            is_completed=True
        )
        
        self.total_attempts = completed_attempts.count()
        
        if self.total_attempts > 0:
            # Get scores list
            scores = list(completed_attempts.values_list('percentage', flat=True))
            self.highest_score = max(scores)
            self.lowest_score = min(scores)
            self.average_score = sum(scores) / self.total_attempts
        
        self.save()

# ========== NEW MODELS FOR TEST REVIEW FEATURE ==========

class QuestionReview(models.Model):
    """Stores additional review data for questions"""
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name="review_data"
    )
    
    # Detailed explanation
    detailed_explanation = models.TextField(blank=True, null=True)
    detailed_explanation_hi = models.TextField(blank=True, null=True)
    
    # Key concepts/topics covered
    key_concepts = models.TextField(blank=True, help_text="Comma-separated key concepts")
    
    # Difficulty rating by users
    average_difficulty_rating = models.FloatField(default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    
    # Common mistakes
    common_mistakes = models.TextField(blank=True, help_text="Common mistakes students make")
    
    # Time management
    average_time_taken = models.PositiveIntegerField(default=0, help_text="Average time in seconds")
    
    # Success rate
    success_rate = models.FloatField(default=0, help_text="Percentage of users who got it correct")
    
    # Video solution link (optional)
    video_solution_url = models.URLField(blank=True, null=True)
    
    # Reference links
    reference_links = models.TextField(blank=True, help_text="JSON field for storing reference links")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Review for Q{self.question.id}"
    
    def get_key_concepts_list(self):
        if self.key_concepts:
            return [concept.strip() for concept in self.key_concepts.split(',') if concept.strip()]
        return []

class AttemptReview(models.Model):
    """Stores review data for a specific attempt"""
    attempt = models.OneToOneField(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="review"
    )
    
    # Overall feedback
    overall_feedback = models.TextField(blank=True, null=True)
    
    # Strengths and weaknesses
    strengths = models.TextField(blank=True, help_text="Topics user performed well in")
    weaknesses = models.TextField(blank=True, help_text="Topics user needs to improve")
    
    # Performance by difficulty
    easy_correct = models.PositiveIntegerField(default=0)
    easy_total = models.PositiveIntegerField(default=0)
    medium_correct = models.PositiveIntegerField(default=0)
    medium_total = models.PositiveIntegerField(default=0)
    hard_correct = models.PositiveIntegerField(default=0)
    hard_total = models.PositiveIntegerField(default=0)
    
    # Time analysis
    time_per_question = models.JSONField(default=dict, blank=True)
    average_time_correct = models.PositiveIntegerField(default=0)
    average_time_incorrect = models.PositiveIntegerField(default=0)
    
    # Recommendations
    recommendations = models.TextField(blank=True, help_text="Personalized study recommendations")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for Attempt {self.attempt.id}"
    
    @property
    def easy_accuracy(self):
        if self.easy_total > 0:
            return round((self.easy_correct / self.easy_total) * 100, 2)
        return 0
    
    @property
    def medium_accuracy(self):
        if self.medium_total > 0:
            return round((self.medium_correct / self.medium_total) * 100, 2)
        return 0
    
    @property
    def hard_accuracy(self):
        if self.hard_total > 0:
            return round((self.hard_correct / self.hard_total) * 100, 2)
        return 0

class QuestionFeedback(models.Model):
    """User feedback on specific questions during review"""
    attempt = models.ForeignKey(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="question_feedbacks"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_feedbacks"
    )
    
    # User's answer
    user_answer = models.ForeignKey(
        Option,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_feedbacks"
    )
    
    # Was it correct?
    is_correct = models.BooleanField(default=False)
    
    # User's self-assessment
    found_difficult = models.BooleanField(default=False)
    time_spent = models.PositiveIntegerField(default=0, help_text="Time spent in seconds")
    
    # User's notes
    personal_notes = models.TextField(blank=True, null=True)
    
    # Mark for review
    marked_for_review = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} Q{self.question.id} - {self.attempt.user.username}"

class ReviewSession(models.Model):
    """Tracks user's review sessions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_sessions"
    )
    attempt = models.ForeignKey(
        MockTestAttempt,
        on_delete=models.CASCADE,
        related_name="review_sessions"
    )
    
    # Session data
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Which questions were reviewed
    reviewed_questions = models.JSONField(default=list)
    
    # Notes taken during review
    session_notes = models.TextField(blank=True, null=True)
    
    # Session completed?
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Review Session {self.id} - {self.user.username}"
    
    @property
    def duration(self):
        if self.ended_at:
            delta = self.ended_at - self.started_at
            minutes = delta.total_seconds() // 60
            return f"{int(minutes)} minutes"
        return "In progress"
=======
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
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
