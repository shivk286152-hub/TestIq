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
    """Links to old app's MockTest"""
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='mocktests')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='mocktests')
    
    # This links to old app's MockTest - ONLY THIS FIELD CONNECTS TO OLD APP
    mocktest_id = models.IntegerField(
        help_text="ID of the MockTest in exams app"
    )
    
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['subject', 'topic__order', 'order']
    
    def __str__(self):
        if self.topic:
            return f"{self.subject.name} - {self.topic.name} - {self.title}"
        return f"{self.subject.name} - {self.title}"