from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import json
import re


# ============================================
# BASE CONTENT SECTION MODEL (Abstract)
# ============================================

class BaseContentSection(models.Model):
    """Abstract base model for content sections with bilingual support"""
    
    # Section Title (optional)
    section_title_en = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Section Title (English)"
    )
    section_title_hi = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Section Title (Hindi)"
    )
    
    # Main Content - can contain HTML with headings, paragraphs, lists
    content_en = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Content (English)",
        help_text="You can use HTML: <h2>, <p>, <ul>, <ol>, <table>, etc."
    )
    content_hi = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Content (Hindi)",
        help_text="You can use HTML: <h2>, <p>, <ul>, <ol>, <table>, etc."
    )
    
    # Optional Image
    image = models.ImageField(
        upload_to="section_images/", 
        blank=True, 
        null=True,
        help_text="Optional image for this section"
    )
    image_alt_en = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name="Image Alt Text (English)"
    )
    image_alt_hi = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name="Image Alt Text (Hindi)"
    )
    
    # Optional Table Data (JSON)
    table_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='''Table data in JSON format:
        {
            "headers": ["Column 1", "Column 2", "Column 3"],
            "rows": [
                ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
                ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
            ]
        }'''
    )
    
    # Optional List Items
    list_items = models.JSONField(
        default=list,
        blank=True,
        help_text='List items as JSON array: ["Item 1", "Item 2", "Item 3"]'
    )
    
    # Display order
    order = models.PositiveIntegerField(default=0, help_text="Order of this section")
    is_active = models.BooleanField(default=True, help_text="Show this section")
    
    # Styling
    background_color = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="e.g., #f3f4f6 or gray-100"
    )
    text_color = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="e.g., #1f2937 or text-gray-800"
    )
    
    class Meta:
        abstract = True
        ordering = ['order']
    
    def __str__(self):
        return self.section_title_en or self.section_title_hi or f"Section {self.order}"
    
    def get_title(self, language='en'):
        if language == 'hi' and self.section_title_hi:
            return self.section_title_hi
        return self.section_title_en
    
    def get_content(self, language='en'):
        if language == 'hi' and self.content_hi:
            return self.content_hi
        return self.content_en
    
    def get_image_alt(self, language='en'):
        if language == 'hi' and self.image_alt_hi:
            return self.image_alt_hi
        return self.image_alt_en
    
    def render_table(self):
        """Render table as HTML"""
        if not self.table_data:
            return ""
        
        html = '<div class="table-responsive overflow-x-auto">'
        html += '<table class="min-w-full border-collapse border border-gray-300">'
        
        # Headers
        if 'headers' in self.table_data and self.table_data['headers']:
            html += '<thead><tr>'
            for header in self.table_data['headers']:
                html += f'<th class="border border-gray-300 px-4 py-2 bg-gray-100 font-semibold">{header}</th>'
            html += '</tr></thead>'
        
        # Rows
        if 'rows' in self.table_data and self.table_data['rows']:
            html += '<tbody>'
            for row in self.table_data['rows']:
                html += '<tr>'
                for cell in row:
                    html += f'<td class="border border-gray-300 px-4 py-2">{cell}</td>'
                html += '</tr>'
            html += '</tbody>'
        
        html += '</table></div>'
        return html
    
    def render_list(self):
        """Render list as HTML"""
        if not self.list_items:
            return ""
        
        html = '<ul class="list-disc pl-5 space-y-2">'
        for item in self.list_items:
            html += f'<li>{item}</li>'
        html += '</ul>'
        return html
    
    def render(self, language='en'):
        """Render full section as HTML"""
        html = '<div class="content-section mb-8">'
        
        # Title
        title = self.get_title(language)
        if title:
            html += f'<h2 class="text-2xl font-bold mb-4">{title}</h2>'
        
        # Image
        if self.image:
            alt = self.get_image_alt(language) or 'Image'
            html += f'<figure class="my-4"><img src="{self.image.url}" alt="{alt}" class="rounded-lg shadow-md max-w-full h-auto"><figcaption class="text-sm text-gray-500 mt-2 text-center">{alt}</figcaption></figure>'
        
        # Content
        content = self.get_content(language)
        if content:
            html += f'<div class="prose max-w-none mb-4">{content}</div>'
        
        # Table
        if self.table_data:
            html += self.render_table()
        
        # List
        if self.list_items:
            html += self.render_list()
        
        html += '</div>'
        return html


# ============================================
# CATEGORY CONTENT SECTION
# ============================================

class CategoryContentSection(BaseContentSection):
    """Content sections for ExamCategory"""
    category = models.ForeignKey(
        'ExamCategory',
        on_delete=models.CASCADE,
        related_name='content_sections'
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "Category Content Section"
        verbose_name_plural = "Category Content Sections"


# ============================================
# SUBCATEGORY CONTENT SECTION
# ============================================

class SubCategoryContentSection(BaseContentSection):
    """Content sections for SubCategory"""
    subcategory = models.ForeignKey(
        'SubCategory',
        on_delete=models.CASCADE,
        related_name='content_sections'
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "SubCategory Content Section"
        verbose_name_plural = "SubCategory Content Sections"


# ============================================
# MOCKTEST CONTENT SECTION
# ============================================

class MockTestContentSection(BaseContentSection):
    """Content sections for MockTest"""
    mock_test = models.ForeignKey(
        'MockTest',
        on_delete=models.CASCADE,
        related_name='content_sections'
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "MockTest Content Section"
        verbose_name_plural = "MockTest Content Sections"


# ============================================
# EXAM CATEGORY MODEL
# ============================================

class ExamCategory(models.Model):
    name = models.CharField(max_length=100)
    name_hi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Name (Hindi)")
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True, null=True, verbose_name="Description (Hindi)")
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="category_logos/", blank=True, null=True)
    
    # ===== HERO/BANNER SECTION =====
    banner_image = models.ImageField(
        upload_to="categories/banners/", 
        blank=True, 
        null=True,
        help_text="Main banner image for the category page"
    )
    banner_title = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Optional custom title for banner"
    )
    banner_title_hi = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Banner title in Hindi"
    )
    banner_subtitle = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Optional subtitle for banner"
    )
    banner_subtitle_hi = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Banner subtitle in Hindi"
    )
    
    # ===== SYLLABUS/OVERVIEW =====
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    # ===== SEO =====
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=300, blank=True, null=True)
    
    # Deprecated - kept for compatibility
    custom_content = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            if ExamCategory.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{ExamCategory.objects.count() + 1}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def get_name(self, language='en'):
        if language == 'hi' and self.name_hi:
            return self.name_hi
        return self.name
    
    def get_description(self, language='en'):
        if language == 'hi' and self.description_hi:
            return self.description_hi
        return self.description
    
    def get_banner_title(self, language='en'):
        if language == 'hi' and self.banner_title_hi:
            return self.banner_title_hi
        return self.banner_title or self.name
    
    def get_banner_subtitle(self, language='en'):
        if language == 'hi' and self.banner_subtitle_hi:
            return self.banner_subtitle_hi
        return self.banner_subtitle
    
    def get_syllabus_heading(self, language='en'):
        if language == 'hi' and self.syllabus_heading_hi:
            return self.syllabus_heading_hi
        return self.syllabus_heading
    
    def get_syllabus_description(self, language='en'):
        if language == 'hi' and self.syllabus_description_hi:
            return self.syllabus_description_hi
        return self.syllabus_description
    
    def get_content_sections(self, language='en'):
        """Get all content sections rendered as HTML"""
        sections = self.content_sections.filter(is_active=True).order_by('order')
        return [section.render(language) for section in sections]
    
    class Meta:
        verbose_name_plural = "Exam Categories"


# ============================================
# SUBCATEGORY MODEL
# ============================================

class SubCategory(models.Model):
    category = models.ForeignKey(
        ExamCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    name_hi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ImageField(upload_to="sub_icons/", null=True, blank=True)
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True, null=True, verbose_name="Description (Hindi)")
    
    # ===== HERO/BANNER SECTION =====
    banner_image = models.ImageField(
        upload_to="subcategories/banners/", 
        blank=True, 
        null=True,
        help_text="Main banner image for the subcategory page"
    )
    banner_title = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Optional custom title for banner"
    )
    banner_title_hi = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Banner title in Hindi"
    )
    banner_subtitle = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Optional subtitle for banner"
    )
    banner_subtitle_hi = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Banner subtitle in Hindi"
    )
    
    # ===== SYLLABUS/OVERVIEW =====
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    # ===== SEO =====
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    
    # Deprecated - kept for compatibility
    custom_content = models.JSONField(default=list, blank=True)

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
    
    def get_name(self, language='en'):
        if language == 'hi' and self.name_hi:
            return self.name_hi
        return self.name
    
    def get_description(self, language='en'):
        if language == 'hi' and self.description_hi:
            return self.description_hi
        return self.description
    
    def get_banner_title(self, language='en'):
        if language == 'hi' and self.banner_title_hi:
            return self.banner_title_hi
        return self.banner_title or self.name
    
    def get_banner_subtitle(self, language='en'):
        if language == 'hi' and self.banner_subtitle_hi:
            return self.banner_subtitle_hi
        return self.banner_subtitle
    
    def get_syllabus_heading(self, language='en'):
        if language == 'hi' and self.syllabus_heading_hi:
            return self.syllabus_heading_hi
        return self.syllabus_heading
    
    def get_syllabus_description(self, language='en'):
        if language == 'hi' and self.syllabus_description_hi:
            return self.syllabus_description_hi
        return self.syllabus_description
    
    def get_content_sections(self, language='en'):
        """Get all content sections rendered as HTML"""
        sections = self.content_sections.filter(is_active=True).order_by('order')
        return [section.render(language) for section in sections]
    
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
        ('per_question', 'Per Question Negative Marking'),
    ]

    title = models.CharField(max_length=255)
    title_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Title (Hindi)")
    description = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True, verbose_name="Description (Hindi)")

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
    
    # ===== HERO/BANNER SECTION =====
    banner_image = models.ImageField(
        upload_to="mocktests/banners/", 
        blank=True, 
        null=True,
        help_text="Main banner image for the test page"
    )
    banner_title = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Optional custom title for banner"
    )
    banner_title_hi = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Banner title in Hindi"
    )
    banner_subtitle = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Optional subtitle for banner"
    )
    banner_subtitle_hi = models.CharField(
        max_length=300, 
        blank=True, 
        null=True,
        help_text="Banner subtitle in Hindi"
    )
    
    # ===== SYLLABUS/OVERVIEW =====
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    # ===== TEST STRUCTURE =====
    total_sections = models.PositiveIntegerField(default=1, help_text="Number of sections")
    
    # ===== SEO =====
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    
    # Deprecated - kept for compatibility
    custom_content = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if self.negative_marking_type != 'no_negative' and self.negative_marking_value <= 0:
            raise ValidationError({
                'negative_marking_value': 'Negative marking value must be greater than 0 for the selected negative marking type.'
            })
        if self.duration <= 0:
            raise ValidationError({
                'duration': 'Duration must be greater than 0 minutes.'
            })
        if self.time_limit <= 0:
            raise ValidationError({
                'time_limit': 'Time limit must be greater than 0 minutes.'
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
    
    def get_title(self, language='en'):
        if language == 'hi' and self.title_hi:
            return self.title_hi
        return self.title
    
    def get_description(self, language='en'):
        if language == 'hi' and self.description_hi:
            return self.description_hi
        return self.description
    
    def get_banner_title(self, language='en'):
        if language == 'hi' and self.banner_title_hi:
            return self.banner_title_hi
        return self.banner_title or self.title
    
    def get_banner_subtitle(self, language='en'):
        if language == 'hi' and self.banner_subtitle_hi:
            return self.banner_subtitle_hi
        return self.banner_subtitle
    
    def get_syllabus_heading(self, language='en'):
        if language == 'hi' and self.syllabus_heading_hi:
            return self.syllabus_heading_hi
        return self.syllabus_heading
    
    def get_syllabus_description(self, language='en'):
        if language == 'hi' and self.syllabus_description_hi:
            return self.syllabus_description_hi
        return self.syllabus_description
    
    def get_content_sections(self, language='en'):
        """Get all content sections rendered as HTML"""
        sections = self.content_sections.filter(is_active=True).order_by('order')
        return [section.render(language) for section in sections]

    def calculate_negative_marks(self, question_marks, question_difficulty=None):
        if self.negative_marking_type == 'fixed_per_question':
            return self.negative_marking_value
        elif self.negative_marking_type == 'percentage_of_marks':
            return (question_marks * self.negative_marking_value) / 100
        elif self.negative_marking_type == 'per_question':
            return None
        return 0

    def update_totals(self):
        self.total_questions = self.questions.count()
        self.total_marks = sum(q.marks for q in self.questions.all())
        MockTest.objects.filter(pk=self.pk).update(
            total_questions=self.total_questions,
            total_marks=self.total_marks
        )


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
    name_hi = models.CharField(max_length=100, blank=True, null=True)
    start_question_no = models.PositiveIntegerField()
    end_question_no = models.PositiveIntegerField()
    
    description = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.start_question_no}-{self.end_question_no})"
    
    def get_name(self, language='en'):
        if language == 'hi' and self.name_hi:
            return self.name_hi
        return self.name
    
    def get_description(self, language='en'):
        if language == 'hi' and self.description_hi:
            return self.description_hi
        return self.description
    
    def clean(self):
        if self.start_question_no > self.end_question_no:
            raise ValidationError({
                'end_question_no': 'End question number must be greater than or equal to start question number.'
            })
    
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
    
    DIFFICULTY_NEGATIVE_MARKS = {
        'Easy': 0.25,
        'Medium': 0.33,
        'Hard': 0.50,
    }
    
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

    question_en = models.TextField(verbose_name="Question (English)")
    question_hi = models.TextField(blank=True, null=True, verbose_name="Question (Hindi)")

    explanation = models.TextField(blank=True, null=True, verbose_name="Explanation (English)")
    explanation_hi = models.TextField(blank=True, null=True, verbose_name="Explanation (Hindi)")
    
    marks = models.FloatField(default=1, help_text="Marks for this question")
    
    negative_marks = models.FloatField(
        null=True, 
        blank=True,
        help_text="Negative marks for this question. If blank, uses difficulty-based default or test default."
    )
    
    override_test_negative = models.BooleanField(
        default=False,
        help_text="Check to use this question's negative marks instead of test defaults"
    )
    
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
        return self.question_en[:50] if self.question_en else f"Question {self.id}"
    
    class Meta:
        ordering = ['order', 'id']
    
    def get_effective_negative_marks(self):
        if self.override_test_negative and self.negative_marks is not None:
            return self.negative_marks
        
        if self.mock_test.negative_marking_type == 'per_question':
            return self.DIFFICULTY_NEGATIVE_MARKS.get(self.difficulty, 0.25)
        
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
    
    def clean(self):
        if self.marks <= 0:
            raise ValidationError({
                'marks': 'Marks must be greater than 0.'
            })
        if self.override_test_negative and self.negative_marks is not None:
            if self.negative_marks < 0:
                raise ValidationError({
                    'negative_marks': 'Negative marks cannot be negative.'
                })
        if not self.question_en or not self.question_en.strip():
            raise ValidationError({
                'question_en': 'Question text in English is required.'
            })


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
        return self.text_en[:30] if self.text_en else f"Option {self.id}"
    
    class Meta:
        ordering = ['order']
    
    def get_text(self, language='en'):
        if language == 'hi' and self.text_hi:
            return self.text_hi
        return self.text_en
    
    def clean(self):
        if not self.text_en or not self.text_en.strip():
            raise ValidationError({
                'text_en': 'Option text in English is required.'
            })


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

    raw_score = models.FloatField(default=0, help_text="Score without negative marking")
    score_with_negative = models.FloatField(default=0, help_text="Score with negative marking applied")
    total_marks = models.FloatField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    skipped_answers = models.PositiveIntegerField(default=0)
    negative_marks_applied = models.FloatField(default=0, help_text="Total negative marks deducted")

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
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
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.score_with_negative / self.total_marks) * 100, 2)
    
    @property
    def percentage_raw(self):
        if not self.total_marks or self.total_marks == 0:
            return 0
        return round((self.raw_score / self.total_marks) * 100, 2)
    
    @property
    def accuracy_with_negative(self):
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
        correct_count = 0
        wrong_count = 0
        skipped_count = 0
        raw_total = 0
        score_with_negative = 0
        total_negative_applied = 0
        
        answers = self.answers.select_related('question', 'selected_option').all()
        
        for answer in answers:
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
        self.score_with_negative = max(0, score_with_negative)
        self.negative_marks_applied = total_negative_applied
        self.total_marks = sum(q.marks for q in self.mock_test.questions.all())
        
        MockTestAttempt.objects.filter(pk=self.pk).update(
            correct_answers=correct_count,
            wrong_answers=wrong_count,
            skipped_answers=skipped_count,
            raw_score=raw_total,
            score_with_negative=max(0, score_with_negative),
            negative_marks_applied=total_negative_applied,
            total_marks=self.total_marks
        )
        
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
        if self.selected_option:
            self.is_correct = self.selected_option.is_correct
        else:
            self.is_correct = False
        super().save(*args, **kwargs)
    
    @property
    def marks_obtained(self):
        if not self.selected_option:
            return 0
        if self.is_correct:
            return self.question.marks
        else:
            return -self.question.get_effective_negative_marks()
    
    @property
    def negative_marks(self):
        if self.selected_option and not self.is_correct:
            return self.question.get_effective_negative_marks()
        return 0
    
    def clean(self):
        if self.selected_option and self.selected_option.question_id != self.question_id:
            raise ValidationError({
                'selected_option': 'Selected option does not belong to this question.'
            })


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
    
    def clean(self):
        if self.stars < 1 or self.stars > 5:
            raise ValidationError({
                'stars': 'Stars must be between 1 and 5.'
            })
        if self.text and len(self.text.strip()) < 10:
            raise ValidationError({
                'text': 'Testimonial text must be at least 10 characters long.'
            })


# ============================================
# FAQ MODEL
# ============================================

class FAQ(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Show on FAQ page")
    show_on_homepage = models.BooleanField(default=False, help_text="Show on homepage")
    category = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="e.g., General, Account, Test Related"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return self.question[:50]
    
    def clean(self):
        if not self.question or not self.question.strip():
            raise ValidationError({
                'question': 'Question text is required.'
            })
        if not self.answer or not self.answer.strip():
            raise ValidationError({
                'answer': 'Answer text is required.'
            })


# ============================================
# CONTACT MODEL
# ============================================

class Contact(models.Model):
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('resolved', 'Resolved'),
        ('spam', 'Spam'),
    ]
    
    SUBJECT_CHOICES = [
        ('mock-test', 'Mock Test Related'),
        ('technical', 'Technical Support'),
        ('billing', 'Billing & Payments'),
        ('suggestion', 'Suggestion & Feedback'),
        ('general', 'General Inquiry'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject_type = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='general')
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_urgent = models.BooleanField(default=False)
    
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes for admin")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_contacts',
        help_text="Staff member handling this query"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='contact_submissions'
    )
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_type_display()} ({self.created_at.strftime('%d/%m/%Y')})"
    
    def get_status_badge(self):
        colors = {
            'new': 'blue',
            'read': 'yellow',
            'replied': 'green',
            'resolved': 'gray',
            'spam': 'red',
        }
        return colors.get(self.status, 'gray')
    
    def time_since(self):
        from django.utils.timesince import timesince
        return timesince(self.created_at)
    
    def clean(self):
        if self.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.email):
            raise ValidationError({
                'email': 'Please enter a valid email address.'
            })
        if not self.message or not self.message.strip():
            raise ValidationError({
                'message': 'Message text is required.'
            })
        if not self.name or not self.name.strip():
            raise ValidationError({
                'name': 'Name is required.'
            })