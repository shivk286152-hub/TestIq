from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from ckeditor.fields import RichTextField
from django.utils import timezone

class Subject(models.Model):
    """Main Subject Model"""
    name = models.CharField(max_length=200, verbose_name="Subject Name")
    name_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Subject Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    description = models.TextField(verbose_name="Description", blank=True)
    description_hi = models.TextField(verbose_name="Description (Hindi)", blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., 'fa-book')")
    image = models.ImageField(upload_to='subjects/', blank=True, null=True)
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('qa:topic_list', kwargs={'subject_slug': self.slug})

    def __str__(self):
        return self.name

    def get_topics_count(self):
        return self.topics.filter(is_active=True).count()


class Topic(models.Model):
    """Topic under Subject"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=200, verbose_name="Topic Name")
    name_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Topic Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    description = models.TextField(verbose_name="Description", blank=True)
    description_hi = models.TextField(verbose_name="Description (Hindi)", blank=True)
    comprehensive_content = models.TextField(verbose_name="Comprehensive Content", blank=True)
    comprehensive_content_hi = models.TextField(verbose_name="Comprehensive Content (Hindi)", blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Topic"
        verbose_name_plural = "Topics"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('qa:part_list', kwargs={'subject_slug': self.subject.slug, 'topic_slug': self.slug})

    def __str__(self):
        return f"{self.subject.name} - {self.name}"

    def get_parts_count(self):
        return self.parts.filter(is_active=True).count()


class Part(models.Model):
    """Part/Chapter under Topic"""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='parts')
    name = models.CharField(max_length=200, verbose_name="Part Name")
    name_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Part Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    description = models.TextField(verbose_name="Description", blank=True)
    description_hi = models.TextField(verbose_name="Description (Hindi)", blank=True)
    comprehensive_content = models.TextField(verbose_name="Comprehensive Content", blank=True)
    comprehensive_content_hi = models.TextField(verbose_name="Comprehensive Content (Hindi)", blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    views = models.IntegerField(default=0, help_text="Number of views")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Part"
        verbose_name_plural = "Parts"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('qa:part_detail', kwargs={
            'subject_slug': self.topic.subject.slug,
            'topic_slug': self.topic.slug,
            'part_slug': self.slug
        })

    def __str__(self):
        return f"{self.topic.name} - {self.name}"

    def get_questions_count(self):
        return self.questions.filter(is_active=True).count()


# ============================================
# NEW: Question Category Model for Filtering
# ============================================

class QuestionCategory(models.Model):
    """Category for questions (e.g., 'Numerical', 'Theory', 'MCQ', 'Descriptive')"""
    name = models.CharField(max_length=100, verbose_name="Category Name")
    name_hi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Category Name (Hindi)")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    color = models.CharField(max_length=20, default='#6366f1', help_text='Hex color code (e.g., #6366f1)')
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., 'fa-calculator')")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Question Category"
        verbose_name_plural = "Question Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_question_count(self):
        return self.questions.filter(is_active=True).count()


class Question(models.Model):
    """Questions under Part"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]
    
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('numerical', 'Numerical'),
        ('descriptive', 'Descriptive'),
        ('true_false', 'True/False'),
        ('fill_blank', 'Fill in the Blank'),
        ('match', 'Match the Following'),
    ]
    
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField(verbose_name="Question")
    question_hi = models.TextField(verbose_name="Question (Hindi)", blank=True, null=True)
    answer = RichTextField(verbose_name="Answer", blank=True)
    answer_hi = RichTextField(verbose_name="Answer (Hindi)", blank=True)
    
    # NEW FIELDS FOR FILTERING
    categories = models.ManyToManyField(QuestionCategory, related_name='questions', blank=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='descriptive')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    published_date = models.DateTimeField(default=timezone.now, help_text="Date when this question was published")
    is_featured = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True, help_text='List of tags for advanced filtering (e.g., ["important", "repeated"])')
    
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    views = models.IntegerField(default=0, help_text="Number of views")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        indexes = [
            models.Index(fields=['published_date']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['question_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.question[:100] + "..." if len(self.question) > 100 else self.question

    def get_categories_list(self):
        """Return list of category names"""
        return list(self.categories.filter(is_active=True).values_list('name', flat=True))

    def get_tags_list(self):
        """Return tags as list"""
        return self.tags if isinstance(self.tags, list) else []


class QuestionImage(models.Model):
    """Images for Questions (optional)"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='questions/')
    caption = models.CharField(max_length=200, blank=True)
    caption_hi = models.CharField(max_length=200, blank=True, verbose_name="Caption (Hindi)")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Question Image"
        verbose_name_plural = "Question Images"

    def __str__(self):
        return f"Image for: {self.question.question[:50]}"


class QuestionTable(models.Model):
    """Tables for Questions (optional)"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='tables')
    table_data = models.TextField(verbose_name="Table Data (HTML)", help_text="Enter table HTML")
    caption = models.CharField(max_length=200, blank=True)
    caption_hi = models.CharField(max_length=200, blank=True, verbose_name="Caption (Hindi)")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Question Table"
        verbose_name_plural = "Question Tables"

    def __str__(self):
        return f"Table for: {self.question.question[:50]}"


class ComprehensiveContent(models.Model):
    """Rich content for Subjects/Topics/Parts"""
    CONTENT_TYPES = [
        ('subject', 'Subject'),
        ('topic', 'Topic'),
        ('part', 'Part'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='comprehensive_contents')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True, related_name='comprehensive_contents')
    part = models.ForeignKey(Part, on_delete=models.CASCADE, null=True, blank=True, related_name='comprehensive_contents')
    
    heading = models.CharField(max_length=200, verbose_name="Heading")
    heading_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Heading (Hindi)")
    content = RichTextField(verbose_name="Content")
    content_hi = RichTextField(verbose_name="Content (Hindi)", blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Comprehensive Content"
        verbose_name_plural = "Comprehensive Contents"

    def __str__(self):
        return f"{self.get_content_type_display()}: {self.heading}"