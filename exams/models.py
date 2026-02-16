from django.db import models
from django.utils.text import slugify
from django.conf import settings

# 1. Exam Category (SSC, Banking, Railway)
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
    
from django.utils.text import slugify

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

# 2. Sub Category (CGL, CHSL, PO, Clerk)
class SubCategory(models.Model):
    category = models.ForeignKey(
        ExamCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to="sub_icons/", null=True, blank=True)

    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


# 3. Mock Test
class MockTest(models.Model):
    title = models.CharField(max_length=255)
    subcategory = models.ForeignKey(
        "SubCategory",  # your subcategory model
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    duration = models.PositiveIntegerField(default=30)  # in minutes
    time_limit = models.PositiveIntegerField(default=30)  # optional
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)



# 4. Subject (Maths, Reasoning, English, GK)
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


# 5. Question
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

    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.question_en[:50]


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

    def __str__(self):
        return self.text_en


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
        return f"{self.user} - {self.mock_test} ({self.score})"

    # Percentage property
    @property
    def percentage(self):
        if not self.total_marks:
            return 0
        return round((self.score / self.total_marks) * 100, 2)
    percentage.fget.short_description = "Percentage (%)"

    # FIXED: Time taken property as HH:MM:SS
    @property
    def time_taken(self):
        if self.submitted_at:
            delta = self.submitted_at - self.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 0:  # safety
                total_seconds = 0
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None
    time_taken.fget.short_description = "Time Taken"
    # ✅ ADD THIS FOR SERVER TIMER
    def time_remaining(self):
        duration = self.mock_test.duration  # minutes
        end_time = self.started_at + timedelta(minutes=duration)
        remaining = (end_time - timezone.now()).total_seconds()
        return max(0, int(remaining))


 

class UserAnswer(models.Model):
    attempt = models.ForeignKey(
        MockTestAttempt,
        related_name="answers",
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(
        "Option",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
