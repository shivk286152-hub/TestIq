from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import json
import re
from decimal import Decimal


# ============================================
# PAYMENT & PRICING MODELS (COMPLETE)
# ============================================

class PricingConfig(models.Model):
    """
    Configuration for pricing of content (Category, SubCategory, MockTest)
    """
    
    CONTENT_TYPES = [
        ('subject', 'Exam Category'),
        ('topic', 'Sub Category'),
        ('mocktest', 'Mock Test'),
    ]
    
    PRICING_TYPES = [
        ('free', 'Free'),
        ('paid', 'Paid (One-time)'),
        ('subscription', 'Subscription'),
        ('trial', 'Trial'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.PositiveIntegerField()
    content_name = models.CharField(max_length=200, blank=True, help_text="Content name for reference")
    
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPES, default='free')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    subscription_duration_days = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="For subscription: duration in days (e.g., 30 for 1 month)"
    )
    
    trial_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Trial duration in days (e.g., 7 for 7-day trial)"
    )
    
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Discount percentage (0-100)"
    )
    discount_start_date = models.DateTimeField(null=True, blank=True)
    discount_end_date = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    requires_payment = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['content_type', 'content_id']
        ordering = ['content_type', 'created_at']
        indexes = [
            models.Index(fields=['content_type', 'content_id', 'is_active']),
            models.Index(fields=['pricing_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_content_type_display()} - {self.content_name or f'ID:{self.content_id}'} - {self.get_pricing_type_display()}"
    
    def get_price(self):
        if self.has_discount():
            discount_amount = (self.price * self.discount_percentage) / 100
            return self.price - discount_amount
        return self.price
    
    def has_discount(self):
        if self.discount_percentage <= 0:
            return False
        if self.discount_start_date and timezone.now() < self.discount_start_date:
            return False
        if self.discount_end_date and timezone.now() > self.discount_end_date:
            return False
        return True
    
    def is_free(self):
        return self.pricing_type == 'free' and not self.requires_payment
    
    def is_paid(self):
        return self.pricing_type == 'paid' or self.requires_payment
    
    def is_subscription(self):
        return self.pricing_type == 'subscription'
    
    def is_trial(self):
        return self.pricing_type == 'trial' and self.trial_duration_days
    
    def clean(self):
        if self.pricing_type == 'paid' and self.price <= 0 and self.requires_payment:
            raise ValidationError({
                'price': 'Price must be greater than 0 for paid content.'
            })
        if self.pricing_type == 'subscription' and not self.subscription_duration_days:
            raise ValidationError({
                'subscription_duration_days': 'Subscription duration is required for subscription pricing.'
            })
        if self.pricing_type == 'trial' and not self.trial_duration_days:
            raise ValidationError({
                'trial_duration_days': 'Trial duration is required for trial pricing.'
            })
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise ValidationError({
                'discount_percentage': 'Discount percentage must be between 0 and 100.'
            })


class UserContentAccess(models.Model):
    """
    Tracks user access to content
    """
    
    ACCESS_TYPES = [
        ('one_time', 'One-time Purchase'),
        ('subscription', 'Subscription'),
        ('free', 'Free Access'),
        ('trial', 'Trial Access'),
        ('lifetime', 'Lifetime Access'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_content_access'
    )
    
    content_type = models.CharField(max_length=20, choices=PricingConfig.CONTENT_TYPES)
    content_id = models.PositiveIntegerField()
    
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_content_accesses'
    )
    
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    access_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'content_type', 'content_id']
        indexes = [
            models.Index(fields=['user', 'content_type', 'content_id']),
            models.Index(fields=['status', 'expiry_date']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.content_type} {self.content_id}"
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        return True
    
    def can_access(self):
        return self.is_active()
    
    def get_remaining_days(self):
        if self.expiry_date and self.expiry_date > timezone.now():
            delta = self.expiry_date - timezone.now()
            return delta.days
        return 0


class Payment(models.Model):
    """
    Payment transaction model
    """
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('upi', 'UPI'),
        ('cod', 'Cash on Delivery'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_payments'
    )
    
    payment_id = models.CharField(max_length=100, unique=True, blank=True)
    order_id = models.CharField(max_length=100, unique=True)
    payment_gateway_id = models.CharField(max_length=255, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    items = models.JSONField(default=list, help_text="List of purchased items")
    
    gateway_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['order_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            import uuid
            self.payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
    
    def complete_payment(self, gateway_response=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
        
        for item in self.items:
            self.grant_access(item)
    
    def grant_access(self, item):
        content_type = item.get('content_type')
        content_id = item.get('content_id')
        
        if not content_type or not content_id:
            return
        
        access, created = UserContentAccess.objects.get_or_create(
            user=self.user,
            content_type=content_type,
            content_id=content_id,
            defaults={
                'access_type': item.get('access_type', 'one_time'),
                'payment': self,
                'status': 'active',
                'expiry_date': item.get('expiry_date'),
            }
        )
        
        if not created:
            access.payment = self
            access.status = 'active'
            
            if item.get('subscription_duration_days'):
                if access.expiry_date:
                    access.expiry_date = access.expiry_date + timezone.timedelta(
                        days=item['subscription_duration_days']
                    )
                else:
                    access.expiry_date = timezone.now() + timezone.timedelta(
                        days=item['subscription_duration_days']
                    )
            access.save()
    
    def refund(self, amount=None, reason=None):
        if amount is None:
            amount = self.total_amount
        
        self.refund_amount = amount
        self.refund_reason = reason or 'Customer refund'
        self.refunded_at = timezone.now()
        self.status = 'refunded'
        self.save()
        
        UserContentAccess.objects.filter(
            user=self.user,
            payment=self
        ).update(status='cancelled')


class Subscription(models.Model):
    """
    User subscription model
    """
    
    SUBSCRIPTION_PLANS = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_subscriptions'
    )
    
    plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLANS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_subscriptions'
    )
    
    start_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    
    is_unlimited = models.BooleanField(default=True, help_text="If True, access to all content")
    allowed_content_types = models.JSONField(default=list, blank=True, help_text="List of content types allowed")
    allowed_content_ids = models.JSONField(default=list, blank=True, help_text="List of specific content IDs")
    
    features = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.plan} - {self.status}"
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        return True
    
    def can_access_content(self, content_type, content_id):
        if not self.is_active():
            return False
        
        if self.is_unlimited:
            return True
        
        if content_type in self.allowed_content_types:
            if not self.allowed_content_ids or content_id in self.allowed_content_ids:
                return True
        
        return False
    
    def get_remaining_days(self):
        if self.expiry_date and self.expiry_date > timezone.now():
            delta = self.expiry_date - timezone.now()
            return delta.days
        return 0
    
    def renew(self, duration_days, payment=None):
        if self.expiry_date and self.expiry_date > timezone.now():
            self.expiry_date = self.expiry_date + timezone.timedelta(days=duration_days)
        else:
            self.expiry_date = timezone.now() + timezone.timedelta(days=duration_days)
        
        if payment:
            self.payment = payment
        
        self.status = 'active'
        self.save()
        return self


class TransactionLog(models.Model):
    """
    Log all payment-related transactions for audit
    """
    
    ACTION_CHOICES = [
        ('payment_init', 'Payment Initiated'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('refund', 'Refund'),
        ('access_granted', 'Access Granted'),
        ('access_revoked', 'Access Revoked'),
        ('subscription_created', 'Subscription Created'),
        ('subscription_renewed', 'Subscription Renewed'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('trial_started', 'Trial Started'),
        ('trial_expired', 'Trial Expired'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_transaction_logs'
    )
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    content_type = models.CharField(max_length=20, blank=True, null=True)
    content_id = models.PositiveIntegerField(null=True, blank=True)
    
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"


# ============================================
# BASE CONTENT SECTION MODEL (Abstract)
# ============================================

class BaseContentSection(models.Model):
    """Abstract base model for content sections with bilingual support"""
    
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
    
    list_items = models.JSONField(
        default=list,
        blank=True,
        help_text='List items as JSON array: ["Item 1", "Item 2", "Item 3"]'
    )
    
    order = models.PositiveIntegerField(default=0, help_text="Order of this section")
    is_active = models.BooleanField(default=True, help_text="Show this section")
    
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
        if not self.table_data:
            return ""
        
        html = '<div class="table-responsive overflow-x-auto">'
        html += '<table class="min-w-full border-collapse border border-gray-300">'
        
        if 'headers' in self.table_data and self.table_data['headers']:
            html += '<thead><tr>'
            for header in self.table_data['headers']:
                html += f'<th class="border border-gray-300 px-4 py-2 bg-gray-100 font-semibold">{header}</th>'
            html += '</tr></thead>'
        
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
        if not self.list_items:
            return ""
        
        html = '<ul class="list-disc pl-5 space-y-2">'
        for item in self.list_items:
            html += f'<li>{item}</li>'
        html += '</ul>'
        return html
    
    def render(self, language='en'):
        html = '<div class="content-section mb-8">'
        
        title = self.get_title(language)
        if title:
            html += f'<h2 class="text-2xl font-bold mb-4">{title}</h2>'
        
        if self.image:
            alt = self.get_image_alt(language) or 'Image'
            html += f'<figure class="my-4"><img src="{self.image.url}" alt="{alt}" class="rounded-lg shadow-md max-w-full h-auto"><figcaption class="text-sm text-gray-500 mt-2 text-center">{alt}</figcaption></figure>'
        
        content = self.get_content(language)
        if content:
            html += f'<div class="prose max-w-none mb-4">{content}</div>'
        
        if self.table_data:
            html += self.render_table()
        
        if self.list_items:
            html += self.render_list()
        
        html += '</div>'
        return html


# ============================================
# CATEGORY CONTENT SECTION
# ============================================

class CategoryContentSection(BaseContentSection):
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
# EXAM CATEGORY MODEL - WITH PAYMENT METHODS
# ============================================

class ExamCategory(models.Model):
    name = models.CharField(max_length=100)
    name_hi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Name (Hindi)")
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True, null=True, verbose_name="Description (Hindi)")
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="category_logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Show this category on the site")
    
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
    
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=300, blank=True, null=True)
    
    custom_content = models.JSONField(default=list, blank=True)

    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this category"""
        try:
            return PricingConfig.objects.get(
                content_type='subject',
                content_id=self.id,
                is_active=True
            )
        except PricingConfig.DoesNotExist:
            return None
    
    def is_locked(self):
        """Check if this category is locked (requires payment)"""
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.requires_payment and pricing.pricing_type != 'free'
        return False
    
    def is_free(self):
        """Check if this category is free"""
        try:
            pricing = PricingConfig.objects.get(
                content_type='subject',
                content_id=self.id,
                is_active=True
            )
            return not pricing.requires_payment or pricing.pricing_type == 'free'
        except PricingConfig.DoesNotExist:
            return True
    
    def get_price(self):
        """Get price for this category"""
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.get_price()
        return Decimal('0.00')
    
    def has_pricing(self):
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this category"""
        if not user.is_authenticated:
            return False
        
        # Check if free
        if not self.is_locked():
            return True
        
        # Check direct access
        try:
            access = UserContentAccess.objects.get(
                user=user,
                content_type='subject',
                content_id=self.id,
                status='active'
            )
            if access.can_access():
                return True
        except UserContentAccess.DoesNotExist:
            pass
        
        # Check subscription (subscribed users get all access)
        subscriptions = Subscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        if subscriptions.exists():
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status for this category"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if not self.is_locked():
            return {'has_access': True, 'reason': 'Free content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        pricing = self.get_pricing_config()
        return {
            'has_access': False, 
            'reason': 'This content requires payment',
            'price': pricing.get_price() if pricing else Decimal('0.00'),
            'pricing_type': pricing.pricing_type if pricing else 'free'
        }
    
    def get_locked_subcategories(self):
        """Get all locked subcategories under this category"""
        return self.subcategories.filter(is_active=True).exclude(
            id__in=SubCategory.objects.filter(
                pricingconfig__requires_payment=False,
                pricingconfig__is_active=True
            ).values_list('id', flat=True)
        )
    
    def get_free_subcategories(self):
        """Get all free subcategories under this category"""
        return self.subcategories.filter(is_active=True).filter(
            id__in=SubCategory.objects.filter(
                pricingconfig__requires_payment=False,
                pricingconfig__is_active=True
            ).values_list('id', flat=True)
        )
    
    # ========== END PAYMENT METHODS ==========

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
        sections = self.content_sections.filter(is_active=True).order_by('order')
        return [section.render(language) for section in sections]
    
    class Meta:
        verbose_name_plural = "Exam Categories"


# ============================================
# SUBCATEGORY MODEL - WITH PAYMENT METHODS
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
    is_active = models.BooleanField(default=True, help_text="Show this subcategory on the site")
    
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
    
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    
    custom_content = models.JSONField(default=list, blank=True)

    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this subcategory"""
        try:
            return PricingConfig.objects.get(
                content_type='topic',
                content_id=self.id,
                is_active=True
            )
        except PricingConfig.DoesNotExist:
            return None
    
    def is_locked(self):
        """Check if this subcategory is locked"""
        # First check parent category lock
        if self.category.is_locked():
            return True
        
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.requires_payment and pricing.pricing_type != 'free'
        return False
    
    def is_free(self):
        """Check if this subcategory is free"""
        if self.category.is_locked():
            return False
        
        try:
            pricing = PricingConfig.objects.get(
                content_type='topic',
                content_id=self.id,
                is_active=True
            )
            return not pricing.requires_payment or pricing.pricing_type == 'free'
        except PricingConfig.DoesNotExist:
            return True
    
    def get_price(self):
        """Get price for this subcategory"""
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.get_price()
        return Decimal('0.00')
    
    def has_pricing(self):
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this subcategory"""
        if not user.is_authenticated:
            return False
        
        # Check parent category access
        if not self.category.user_has_access(user):
            return False
        
        # Check if free
        if not self.is_locked():
            return True
        
        # Check direct access
        try:
            access = UserContentAccess.objects.get(
                user=user,
                content_type='topic',
                content_id=self.id,
                status='active'
            )
            if access.can_access():
                return True
        except UserContentAccess.DoesNotExist:
            pass
        
        # Check subscription
        subscriptions = Subscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        if subscriptions.exists():
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status for this subcategory"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if not self.category.user_has_access(user):
            return {'has_access': False, 'reason': 'Parent category is locked'}
        
        if not self.is_locked():
            return {'has_access': True, 'reason': 'Free content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        pricing = self.get_pricing_config()
        return {
            'has_access': False, 
            'reason': 'This content requires payment',
            'price': pricing.get_price() if pricing else Decimal('0.00'),
            'pricing_type': pricing.pricing_type if pricing else 'free'
        }
    
    def get_locked_tests(self):
        """Get all locked tests under this subcategory"""
        return self.mock_tests.filter(is_active=True).exclude(
            id__in=MockTest.objects.filter(
                pricingconfig__requires_payment=False,
                pricingconfig__is_active=True
            ).values_list('id', flat=True)
        )
    
    def get_free_tests(self):
        """Get all free tests under this subcategory"""
        return self.mock_tests.filter(is_active=True).filter(
            id__in=MockTest.objects.filter(
                pricingconfig__requires_payment=False,
                pricingconfig__is_active=True
            ).values_list('id', flat=True)
        )
    
    # ========== END PAYMENT METHODS ==========

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
        sections = self.content_sections.filter(is_active=True).order_by('order')
        return [section.render(language) for section in sections]
    
    class Meta:
        verbose_name_plural = "Sub Categories"


# ============================================
# MOCK TEST MODEL - WITH PAYMENT METHODS
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
    is_active = models.BooleanField(default=True, help_text="Show this mock test on the site")
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
    
    syllabus_heading = models.CharField(max_length=200, blank=True, null=True)
    syllabus_heading_hi = models.CharField(max_length=200, blank=True, null=True)
    syllabus_description = models.TextField(blank=True, null=True)
    syllabus_description_hi = models.TextField(blank=True, null=True)
    
    total_sections = models.PositiveIntegerField(default=1, help_text="Number of sections")
    
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    
    custom_content = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # ========== PAYMENT METHODS ==========
    
    def get_pricing_config(self):
        """Get pricing config for this mock test"""
        try:
            return PricingConfig.objects.get(
                content_type='mocktest',
                content_id=self.id,
                is_active=True
            )
        except PricingConfig.DoesNotExist:
            return None
    
    def is_locked(self):
        """Check if this mock test is locked"""
        # Check parent subcategory lock
        if self.subcategory and self.subcategory.is_locked():
            return True
        # Check parent category lock
        if self.subcategory and self.subcategory.category.is_locked():
            return True
        
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.requires_payment and pricing.pricing_type != 'free'
        return False
    
    def is_free(self):
        """Check if this mock test is free"""
        if self.subcategory and self.subcategory.is_locked():
            return False
        if self.subcategory and self.subcategory.category.is_locked():
            return False
        
        try:
            pricing = PricingConfig.objects.get(
                content_type='mocktest',
                content_id=self.id,
                is_active=True
            )
            return not pricing.requires_payment or pricing.pricing_type == 'free'
        except PricingConfig.DoesNotExist:
            return True
    
    def get_price(self):
        """Get price for this mock test"""
        pricing = self.get_pricing_config()
        if pricing:
            return pricing.get_price()
        return Decimal('0.00')
    
    def has_pricing(self):
        return self.get_pricing_config() is not None
    
    def user_has_access(self, user):
        """Check if user has access to this mock test"""
        if not user.is_authenticated:
            return False
        
        # Check parent access
        if self.subcategory:
            if not self.subcategory.user_has_access(user):
                return False
        
        # Check if free
        if not self.is_locked():
            return True
        
        # Check direct access
        try:
            access = UserContentAccess.objects.get(
                user=user,
                content_type='mocktest',
                content_id=self.id,
                status='active'
            )
            if access.can_access():
                return True
        except UserContentAccess.DoesNotExist:
            pass
        
        # Check subscription
        subscriptions = Subscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        if subscriptions.exists():
            return True
        
        return False
    
    def get_access_status(self, user):
        """Get detailed access status for this mock test"""
        if not user.is_authenticated:
            return {'has_access': False, 'reason': 'Please login to access this content'}
        
        if self.subcategory and not self.subcategory.user_has_access(user):
            return {'has_access': False, 'reason': 'Parent subcategory is locked'}
        
        if not self.is_locked():
            return {'has_access': True, 'reason': 'Free content'}
        
        if self.user_has_access(user):
            return {'has_access': True, 'reason': 'Access granted'}
        
        pricing = self.get_pricing_config()
        return {
            'has_access': False, 
            'reason': 'This content requires payment',
            'price': pricing.get_price() if pricing else Decimal('0.00'),
            'pricing_type': pricing.pricing_type if pricing else 'free'
        }
    
    # ========== END PAYMENT METHODS ==========

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
# SUBJECT MODEL (Exam-specific, not QA app)
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
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
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
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Admin approval status"
    )
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_testimonials'
    )
    
    class Meta:
        ordering = ['display_order', '-is_featured', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.stars} Stars ({self.get_status_display()})"
    
    def user_name(self):
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    @property
    def user_initials(self):
        if self.user.get_full_name():
            parts = self.user.get_full_name().split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return self.user.get_full_name()[:2].upper()
        return self.user.username[:2].upper()
    
    def clean(self):
        if self.stars < 1 or self.stars > 5:
            raise ValidationError({
                'stars': 'Stars must be between 1 and 5.'
            })
        if self.text and len(self.text.strip()) < 10:
            raise ValidationError({
                'text': 'Testimonial text must be at least 10 characters long.'
            })
    
    def approve(self, admin_user=None):
        self.status = 'approved'
        self.is_active = True
        self.approved_at = timezone.now()
        if admin_user:
            self.approved_by = admin_user
        self.save()
    
    def reject(self):
        self.status = 'rejected'
        self.is_active = False
        self.save()


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



# ============================================
# ADD THESE METHODS TO ExamCategory, SubCategory, MockTest
# ============================================

def get_pricing_config(self):
    """Get pricing config for this content"""
    try:
        from payments.models import PricingConfig
        content_type_map = {
            'ExamCategory': 'exam_category',
            'SubCategory': 'exam_subcategory',
            'MockTest': 'exam_mocktest',
        }
        return PricingConfig.objects.get(
            content_type=content_type_map.get(self.__class__.__name__),
            content_id=self.id,
            content_app='exams',
            is_active=True
        )
    except:
        return None

def is_locked(self):
    """Check if content is locked"""
    pricing = self.get_pricing_config()
    return pricing.is_locked if pricing else False

def is_free(self):
    """Check if content is free"""
    pricing = self.get_pricing_config()
    if pricing:
        return not pricing.is_locked
    return True

def get_price(self):
    """Get price"""
    pricing = self.get_pricing_config()
    return pricing.price if pricing else 0

def user_has_access(self, user):
    """Check if user has access - With parent hierarchy"""
    if not user.is_authenticated:
        return False
    
    from payments.models import UserSubscription, UserContentAccess
    
    # 1. Check if user has subscription
    if UserSubscription.objects.filter(
        user=user,
        status='active',
        expiry_date__gt=timezone.now()
    ).exists():
        return True
    
    # 2. Get content type
    content_type_map = {
        'ExamCategory': 'exam_category',
        'SubCategory': 'exam_subcategory',
        'MockTest': 'exam_mocktest',
    }
    content_type = content_type_map.get(self.__class__.__name__)
    
    # 3. Check direct purchase
    if UserContentAccess.objects.filter(
        user=user,
        content_type=content_type,
        content_id=self.id,
        content_app='exams',
        status='active'
    ).exists():
        return True
    
    # 4. If not locked, free access
    if not self.is_locked():
        return True
    
    # 5. Check parent access (for subcategory and mocktest)
    if hasattr(self, 'category') and self.category:
        return self.category.user_has_access(user)
    
    if hasattr(self, 'subcategory') and self.subcategory:
        return self.subcategory.user_has_access(user)
    
    return False            