# payments/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class PricingConfig(models.Model):
    """Pricing configuration for all content - Single source of truth"""
    
    CONTENT_TYPES = [
        # EXAMS APP
        ('exam_category', 'Exam Category'),
        ('exam_subcategory', 'Exam Subcategory'),
        ('exam_mocktest', 'Exam Mock Test'),
        # QA APP
        ('qa_subject', 'QA Subject'),
        ('qa_topic', 'QA Topic'),
        ('qa_part', 'QA Part'),
    ]
    
    APP_CHOICES = [
        ('exams', 'Exams App'),
        ('qa', 'QA App'),
    ]
    
    content_type = models.CharField(max_length=30, choices=CONTENT_TYPES)
    content_id = models.IntegerField()
    content_app = models.CharField(max_length=20, choices=APP_CHOICES, default='qa')
    content_name = models.CharField(max_length=200, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Access control
    is_locked = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Preview
    preview_text = models.TextField(blank=True)
    show_preview = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['content_type', 'content_id', 'content_app']
        indexes = [
            models.Index(fields=['content_type', 'content_id', 'content_app']),
            models.Index(fields=['content_app', 'is_locked']),
        ]

    def __str__(self):
        return f"{self.content_app} - {self.content_name or self.content_type} #{self.content_id}"

    def get_final_price(self):
        if self.discount_price:
            return self.discount_price
        if self.discount_percentage > 0:
            return self.price - (self.price * self.discount_percentage / 100)
        return self.price

    def is_free(self):
        return not self.is_locked


class SubscriptionPlan(models.Model):
    """Subscription plans"""
    
    DURATION_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    APP_ACCESS_CHOICES = [
        ('all', 'All Apps'),
        ('exams', 'Exams Only'),
        ('qa', 'QA Only'),
    ]
    
    name = models.CharField(max_length=100)
    name_hi = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    duration_days = models.IntegerField(help_text="Duration in days")
    
    features = models.JSONField(default=list)
    applies_to = models.CharField(max_length=20, choices=APP_ACCESS_CHOICES, default='all')
    
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price']

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - ₹{self.price}/{self.duration}"

    def applies_to_app(self, app_name):
        if self.applies_to == 'all':
            return True
        return self.applies_to == app_name


class UserSubscription(models.Model):
    """User subscriptions"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name='user_subscriptions'
    )
    
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    auto_renew = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def is_active(self):
        if self.status != 'active':
            return False
        if timezone.now() > self.expiry_date:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        return True

    def days_remaining(self):
        if not self.is_active():
            return 0
        return (self.expiry_date - timezone.now()).days

    def can_access_app(self, app_name):
        if not self.is_active():
            return False
        return self.plan.applies_to_app(app_name)


# payments/models.py - Add payment field to UserContentAccess

class UserContentAccess(models.Model):
    """User's purchased content access"""
    
    ACCESS_TYPES = [
        ('purchase', 'One-time Purchase'),
        ('subscription', 'Subscription'),
        ('free', 'Free Access'),
        ('trial', 'Trial Access'),
        ('lifetime', 'Lifetime Access'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_accesses'
    )
    
    content_type = models.CharField(max_length=30)
    content_id = models.IntegerField()
    content_app = models.CharField(max_length=20, default='qa')
    
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES, default='purchase')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    expiry_date = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    
    # ✅ ADD THIS - Payment reference
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_accesses'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'content_type', 'content_id', 'content_app']

    def __str__(self):
        return f"{self.user.username} - {self.content_app}/{self.content_type} #{self.content_id}"

    def is_active(self):
        if self.status != 'active':
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        return True
    
class Payment(models.Model):
    """Payment transactions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
        ('demo', 'Demo'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    payment_id = models.CharField(max_length=100, unique=True, blank=True)
    order_id = models.CharField(max_length=100, unique=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_order_id = models.CharField(max_length=255, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    items = models.JSONField(default=list)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.status}"

    def complete_payment(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Grant access for all items
        for item in self.items:
            self._grant_access(item)

    def _grant_access(self, item):
        content_type = item.get('content_type')
        content_id = item.get('content_id')
        content_app = item.get('content_app', 'qa')
        
        if not content_type or not content_id:
            return
        
        UserContentAccess.objects.get_or_create(
            user=self.user,
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            defaults={
                'access_type': item.get('access_type', 'purchase'),
                'status': 'active',
                'expiry_date': item.get('expiry_date'),
            }
        )


class TransactionLog(models.Model):
    """Audit log for all transactions"""
    
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
        ('content_locked', 'Content Locked'),
        ('content_unlocked', 'Content Unlocked'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transaction_logs'
    )
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    content_type = models.CharField(max_length=30, blank=True, null=True)
    content_id = models.PositiveIntegerField(null=True, blank=True)
    content_app = models.CharField(max_length=20, default='qa')
    
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"