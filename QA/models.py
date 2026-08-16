# QA/models.py

from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from ckeditor.fields import RichTextField
from django.utils import timezone
from decimal import Decimal
import re
import logging

logger = logging.getLogger(__name__)


# ============================================
# ✅ HELPER: CHECK IF PAYMENTS ARE AVAILABLE
# ============================================

def payments_available():
    """Check if payments app is available and tables exist"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments_pricingconfig'")
        return cursor.fetchone() is not None
    except:
        return False


def get_pricing_config_safe(content_type, content_id, content_app='qa'):
    """Safely get pricing config without raising errors"""
    if not payments_available():
        return None
    
    try:
        from payments.models import PricingConfig
        return PricingConfig.objects.get(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            is_active=True
        )
    except Exception as e:
        logger.debug(f"Pricing config not found: {e}")
        return None


def user_has_subscription_safe(user):
    """Safely check if user has active subscription"""
    if not user.is_authenticated:
        return False
    
    if not payments_available():
        return False
    
    try:
        from payments.models import UserSubscription
        return UserSubscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gt=timezone.now()
        ).exists()
    except Exception as e:
        logger.debug(f"Subscription check failed: {e}")
        return False


def user_has_content_access_safe(user, content_type, content_id, content_app='qa'):
    """Safely check if user has direct content access"""
    if not user.is_authenticated:
        return False
    
    if not payments_available():
        return False
    
    try:
        from payments.models import UserContentAccess
        return UserContentAccess.objects.filter(
            user=user,
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            status='active'
        ).exists()
    except Exception as e:
        logger.debug(f"Content access check failed: {e}")
        return False


# ============================================
# SUBJECT MODEL
# ============================================

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

    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this subject"""
        return get_pricing_config_safe('qa_subject', self.id, 'qa')
    
    def is_locked(self):
        """Check if subject is locked"""
        pricing = self.get_pricing_config()
        return pricing.is_locked if pricing else False
    
    def is_free(self):
        """Check if subject is free"""
        pricing = self.get_pricing_config()
        if pricing:
            return not pricing.is_locked
        return True
    
    def get_price(self):
        """Get price for this subject"""
        pricing = self.get_pricing_config()
        return pricing.price if pricing else Decimal('0.00')
    
    def has_pricing(self):
        """Check if subject has pricing configuration"""
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this subject"""
        if not user.is_authenticated:
            return False
        
        # ✅ 1. Check if user has active subscription
        if user_has_subscription_safe(user):
            return True
        
        # ✅ 2. Check if subject is free (not locked)
        if not self.is_locked():
            return True
        
        # ✅ 3. Check direct purchase
        if user_has_content_access_safe(user, 'qa_subject', self.id, 'qa'):
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        if self.is_locked():
            return {
                'has_access': False, 
                'reason': 'This content requires payment',
                'price': self.get_price(),
                'is_locked': True
            }
        
        return {'has_access': True, 'reason': 'Free content'}
    
    def get_locked_topics(self):
        """Get all locked topics under this subject"""
        try:
            from payments.models import PricingConfig
            locked_topic_ids = PricingConfig.objects.filter(
                content_type='qa_topic',
                content_app='qa',
                is_locked=True
            ).values_list('content_id', flat=True)
            return self.topics.filter(id__in=locked_topic_ids, is_active=True)
        except:
            return self.topics.none()
    
    def get_free_topics(self):
        """Get all free topics under this subject"""
        try:
            from payments.models import PricingConfig
            locked_topic_ids = PricingConfig.objects.filter(
                content_type='qa_topic',
                content_app='qa',
                is_locked=True
            ).values_list('content_id', flat=True)
            return self.topics.filter(is_active=True).exclude(id__in=locked_topic_ids)
        except:
            return self.topics.filter(is_active=True)
    
    # ========== END PAYMENT METHODS ==========


# ============================================
# TOPIC MODEL
# ============================================

class Topic(models.Model):
    """Topic under Subject"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=200, verbose_name="Topic Name")
    name_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Topic Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    description = models.TextField(verbose_name="Description", blank=True)
    description_hi = models.TextField(verbose_name="Description (Hindi)", blank=True)
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
    
    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this topic"""
        return get_pricing_config_safe('qa_topic', self.id, 'qa')
    
    def is_locked(self):
        """Check if topic is locked"""
        # ✅ If parent subject is locked, topic is also locked
        if self.subject.is_locked():
            return True
        
        pricing = self.get_pricing_config()
        return pricing.is_locked if pricing else False
    
    def is_free(self):
        """Check if topic is free"""
        if self.subject.is_locked():
            return False
        
        pricing = self.get_pricing_config()
        if pricing:
            return not pricing.is_locked
        return True
    
    def get_price(self):
        """Get price for this topic"""
        pricing = self.get_pricing_config()
        return pricing.price if pricing else Decimal('0.00')
    
    def has_pricing(self):
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this topic"""
        if not user.is_authenticated:
            return False
        
        # ✅ 1. Check if user has active subscription
        if user_has_subscription_safe(user):
            return True
        
        # ✅ 2. Check if topic is free (not locked)
        if not self.is_locked():
            return True
        
        # ✅ 3. Check direct purchase for THIS specific topic
        if user_has_content_access_safe(user, 'qa_topic', self.id, 'qa'):
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        if self.is_locked():
            return {
                'has_access': False, 
                'reason': 'This content requires payment',
                'price': self.get_price(),
                'is_locked': True
            }
        
        return {'has_access': True, 'reason': 'Free content'}
    
    def get_locked_parts(self):
        """Get all locked parts under this topic"""
        try:
            from payments.models import PricingConfig
            locked_part_ids = PricingConfig.objects.filter(
                content_type='qa_part',
                content_app='qa',
                is_locked=True
            ).values_list('content_id', flat=True)
            return self.parts.filter(id__in=locked_part_ids, is_active=True)
        except:
            return self.parts.none()
    
    def get_free_parts(self):
        """Get all free parts under this topic"""
        try:
            from payments.models import PricingConfig
            locked_part_ids = PricingConfig.objects.filter(
                content_type='qa_part',
                content_app='qa',
                is_locked=True
            ).values_list('content_id', flat=True)
            return self.parts.filter(is_active=True).exclude(id__in=locked_part_ids)
        except:
            return self.parts.filter(is_active=True)
    
    # ========== END PAYMENT METHODS ==========


# ============================================
# PART MODEL
# ============================================

class Part(models.Model):
    """Part/Chapter under Topic with simplified content management"""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='parts')
    name = models.CharField(max_length=200, verbose_name="Part Name")
    name_hi = models.CharField(max_length=200, blank=True, null=True, verbose_name="Part Name (Hindi)")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    description = models.TextField(verbose_name="Description", blank=True)
    description_hi = models.TextField(verbose_name="Description (Hindi)", blank=True)
    
    content = models.TextField(
        verbose_name="Content",
        blank=True,
        help_text="""
        Use simple markup for rich content:
        
        For tables:
        [table]
        Name | Age | City | Occupation
        John | 25 | NYC | Engineer
        Jane | 30 | LA | Designer
        Mike | 35 | CHI | Developer
        [/table]
        
        For lists:
        [list]
        * Item 1
        * Item 2
        * Item 3
        [/list]
        
        For images:
        [image: path/to/image.jpg]Caption text[/image]
        
        For code blocks:
        [code]
        print("Hello World")
        [/code]
        
        For quotes:
        [quote]Quote text here[/quote]
        
        For highlights:
        [highlight]Important text[/highlight]
        """
    )
    content_hi = models.TextField(
        verbose_name="Content (Hindi)",
        blank=True,
        null=True,
        help_text="Hindi version of the content"
    )
    
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
        if self.slug:
            counter = 1
            original_slug = self.slug
            while Part.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
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
    
    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this part"""
        return get_pricing_config_safe('qa_part', self.id, 'qa')
    
    def is_locked(self):
        """Check if part is locked"""
        # ✅ Check parent topic and subject
        if self.topic.is_locked():
            return True
        if self.topic.subject.is_locked():
            return True
        
        pricing = self.get_pricing_config()
        return pricing.is_locked if pricing else False
    
    def is_free(self):
        """Check if part is free"""
        if self.topic.is_locked():
            return False
        if self.topic.subject.is_locked():
            return False
        
        pricing = self.get_pricing_config()
        if pricing:
            return not pricing.is_locked
        return True
    
    def get_price(self):
        """Get price for this part"""
        pricing = self.get_pricing_config()
        return pricing.price if pricing else Decimal('0.00')
    
    def has_pricing(self):
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this part"""
        if not user.is_authenticated:
            return False
        
        # ✅ 1. Check if user has active subscription
        if user_has_subscription_safe(user):
            return True
        
        # ✅ 2. Check if part is free (not locked)
        if not self.is_locked():
            return True
        
        # ✅ 3. Check direct purchase for THIS specific part
        if user_has_content_access_safe(user, 'qa_part', self.id, 'qa'):
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        if self.is_locked():
            return {
                'has_access': False, 
                'reason': 'This content requires payment',
                'price': self.get_price(),
                'is_locked': True
            }
        
        return {'has_access': True, 'reason': 'Free content'}
    
    # ========== END PAYMENT METHODS ==========
    
    def render_content(self, language='en'):
        """Render content with embedded elements as HTML"""
        content = self.content if language == 'en' else self.content_hi
        if not content:
            return ""
        
        content = self._render_tables(content)
        content = self._render_lists(content)
        content = self._render_images(content)
        content = self._render_code_blocks(content)
        content = self._render_quotes(content)
        content = self._render_highlights(content)
        content = self._render_line_breaks(content)
        
        return content
    
    def _render_tables(self, content):
        """Convert [table]...[/table] to HTML table"""
        table_pattern = r'\[table\](.*?)\[/table\]'
        
        def table_replacer(match):
            table_content = match.group(1).strip()
            rows = [row.strip() for row in table_content.split('\n') if row.strip()]
            if not rows:
                return ''
            
            html = '<div class="table-responsive"><table class="table table-striped table-bordered">'
            
            header_cells = [cell.strip() for cell in rows[0].split('|')]
            html += '<thead><tr>'
            for cell in header_cells:
                html += f'<th>{cell}</th>'
            html += '</tr></thead>'
            
            html += '<tbody>'
            for row in rows[1:]:
                cells = [cell.strip() for cell in row.split('|')]
                html += '<tr>'
                for cell in cells:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</tbody></table></div>'
            
            return html
        
        return re.sub(table_pattern, table_replacer, content, flags=re.DOTALL)
    
    def _render_lists(self, content):
        """Convert [list]...[/list] to HTML list"""
        list_pattern = r'\[list\](.*?)\[/list\]'
        
        def list_replacer(match):
            list_content = match.group(1).strip()
            items = [item.strip() for item in list_content.split('\n') if item.strip().startswith('*')]
            if not items:
                return ''
            
            html = '<ul class="list-disc pl-6">'
            for item in items:
                text = item[1:].strip()
                html += f'<li>{text}</li>'
            html += '</ul>'
            return html
        
        return re.sub(list_pattern, list_replacer, content, flags=re.DOTALL)
    
    def _render_images(self, content):
        """Convert [image: path]Caption[/image] to HTML image"""
        image_pattern = r'\[image:\s*([^\]]+)\](.*?)\[/image\]'
        
        def image_replacer(match):
            image_path = match.group(1).strip()
            caption = match.group(2).strip()
            
            html = f'''
            <figure class="my-4">
                <img src="{image_path}" alt="{caption}" class="img-fluid rounded">
                <figcaption class="text-center text-muted">{caption}</figcaption>
            </figure>
            '''
            return html
        
        return re.sub(image_pattern, image_replacer, content, flags=re.DOTALL)
    
    def _render_code_blocks(self, content):
        """Convert [code]...[/code] to preformatted code block"""
        code_pattern = r'\[code\](.*?)\[/code\]'
        
        def code_replacer(match):
            code = match.group(1).strip()
            return f'<pre class="code-block bg-gray-100 p-4 rounded"><code>{code}</code></pre>'
        
        return re.sub(code_pattern, code_replacer, content, flags=re.DOTALL)
    
    def _render_quotes(self, content):
        """Convert [quote]...[/quote] to blockquote"""
        quote_pattern = r'\[quote\](.*?)\[/quote\]'
        
        def quote_replacer(match):
            quote = match.group(1).strip()
            return f'<blockquote class="blockquote border-l-4 border-blue-500 pl-4 italic">{quote}</blockquote>'
        
        return re.sub(quote_pattern, quote_replacer, content, flags=re.DOTALL)
    
    def _render_highlights(self, content):
        """Convert [highlight]...[/highlight] to highlighted text"""
        highlight_pattern = r'\[highlight\](.*?)\[/highlight\]'
        
        def highlight_replacer(match):
            text = match.group(1).strip()
            return f'<span class="highlight bg-yellow-200 px-1">{text}</span>'
        
        return re.sub(highlight_pattern, highlight_replacer, content, flags=re.DOTALL)
    
    def _render_line_breaks(self, content):
        """Convert \n to <br> but preserve blocks"""
        paragraphs = content.split('\n\n')
        processed = []
        for para in paragraphs:
            if para.strip():
                if re.match(r'<[^>]+>', para.strip()):
                    processed.append(para)
                else:
                    lines = para.split('\n')
                    if len(lines) > 1:
                        para = '<br>'.join(lines)
                    processed.append(para)
        
        return '<p>' + '</p><p>'.join(processed) + '</p>'


# ============================================
# REMAINING MODELS (Unchanged)
# ============================================

class QuestionCategory(models.Model):
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
    
    categories = models.ManyToManyField(QuestionCategory, related_name='questions', blank=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='descriptive')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    published_date = models.DateTimeField(default=timezone.now, help_text="Date when this question was published")
    is_featured = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True, help_text='List of tags for advanced filtering')
    
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
        return list(self.categories.filter(is_active=True).values_list('name', flat=True))

    def get_tags_list(self):
        return self.tags if isinstance(self.tags, list) else []


class QuestionImage(models.Model):
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