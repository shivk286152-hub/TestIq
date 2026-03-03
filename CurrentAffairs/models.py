from django.db import models

# Create your models here.
class CurrentAffairsCategory(models.Model):
    """Categories for current affairs (International, National, Sports, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

class CurrentAffairs(models.Model):
    """Main Current Affairs model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    
    title = models.CharField(max_length=500)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        CurrentAffairsCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='articles'
    )
    
    # Content - Using TextField for flexibility (can contain HTML for tables)
    content = models.TextField(help_text="News content - you can add tables using HTML")
    summary = models.TextField(max_length=500, help_text="Brief summary for card view")
    
    # Media
    featured_image = models.ImageField(upload_to='current_affairs/', blank=True, null=True)
    image_caption = models.CharField(max_length=255, blank=True)
    
    # Metadata
    source = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Dates - You control which months to include
    news_date = models.DateField(help_text="Date when the news occurred")
    published_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    views_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    # For random selection weighting
    display_weight = models.PositiveIntegerField(default=1, 
        help_text="Higher weight = more chances to appear in random selection")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while CurrentAffairs.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    @property
    def month_year(self):
        """Returns month and year for filtering"""
        return self.news_date.strftime("%B %Y")
    
    class Meta:
        verbose_name_plural = "Current Affairs"
        ordering = ['-news_date', '-id']
        indexes = [
            models.Index(fields=['-news_date', 'status']),
            models.Index(fields=['category', '-news_date']),
        ]