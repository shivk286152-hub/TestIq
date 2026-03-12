from django.db import models
from django.utils.text import slugify

class Subject(models.Model):
    """Main subject category"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Topic(models.Model):
    """Topics under subject (optional)"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['subject', 'slug']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class SubjectMockTest(models.Model):
    # Existing fields
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='mocktests')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='mocktests')
    
    # REMOVE THIS LINE - we don't want to link to old app
    # mocktest_id = models.IntegerField(help_text="ID of the MockTest in exams app")
    
    # ADD ALL MOCKTEST FIELDS HERE (copy from exams app MockTest model)
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('Beginner', 'Beginner'),
            ('Intermediate', 'Intermediate'),
            ('Advanced', 'Advanced')
        ],
        default='Intermediate',
    )
    
    negative_marking_type = models.CharField(
        max_length=25,
        choices=[
            ('no_negative', 'No Negative Marking'),
            ('fixed_per_question', 'Fixed per Wrong Question'),
            ('percentage_of_marks', 'Percentage of Question Marks')
        ],
        default='no_negative',
    )
    
    negative_marking_value = models.FloatField(
        default=0,
        blank=True,
        help_text="Negative marks or percentage depending on type",
    )
    
    time_limit = models.PositiveIntegerField(
        default=30,
        help_text="Time limit per attempt in minutes",
    )
    
    total_marks = models.FloatField(default=0)
    
    duration = models.IntegerField(default=30)  # Add this if needed
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['subject', 'topic__order', 'order']
    
    def __str__(self):
        if self.topic:
            return f"{self.subject.name} - {self.topic.name} - {self.title}"
        return f"{self.subject.name} - {self.title}"
    

class Question(models.Model):
    mocktest = models.ForeignKey(SubjectMockTest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)  # or IntegerField for option number
    marks = models.FloatField(default=1)
    
    def __str__(self):
        return self.question_text[:50]   