# payments/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from .models import (
    PricingConfig,
    SubscriptionPlan,
    UserSubscription,
    UserContentAccess,
    Payment,
    TransactionLog
)


@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    list_display = [
        'content_app', 
        'content_type', 
        'content_id', 
        'content_name', 
        'price', 
        'discount_percentage',
        'is_locked', 
        'is_active'
    ]
    list_filter = ['content_app', 'content_type', 'is_locked', 'is_active']
    search_fields = ['content_name', 'content_id']
    list_editable = ['price', 'is_locked', 'discount_percentage']
    list_per_page = 50
    
    fieldsets = (
        ('Content Information', {
            'fields': ('content_app', 'content_type', 'content_id', 'content_name')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'discount_percentage')
        }),
        ('Access Control', {
            'fields': ('is_locked', 'is_active', 'preview_text', 'show_preview')
        }),
    )
    
    actions = ['lock_content', 'unlock_content']
    
    def lock_content(self, request, queryset):
        count = queryset.update(is_locked=True)
        self.message_user(request, f'✅ {count} content(s) locked successfully.')
    lock_content.short_description = '🔒 Lock selected content'
    
    def unlock_content(self, request, queryset):
        count = queryset.update(is_locked=False)
        self.message_user(request, f'✅ {count} content(s) unlocked successfully.')
    unlock_content.short_description = '🔓 Unlock selected content'


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'price', 
        'duration', 
        'duration_days', 
        'applies_to', 
        'is_active', 
        'is_featured'
    ]
    list_filter = ['duration', 'applies_to', 'is_active', 'is_featured']
    search_fields = ['name', 'description', 'slug']
    list_editable = ['price', 'is_active', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'description_hi')
        }),
        ('Pricing & Duration', {
            'fields': ('price', 'duration', 'duration_days')
        }),
        ('Features & Access', {
            'fields': ('features', 'applies_to')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'display_order')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'plan', 
        'status', 
        'expiry_date', 
        'days_remaining', 
        'auto_renew'
    ]
    list_filter = ['status', 'plan', 'auto_renew']
    search_fields = ['user__username', 'user__email', 'plan__name']
    readonly_fields = ['start_date', 'created_at', 'updated_at']
    list_editable = ['status', 'auto_renew']
    date_hierarchy = 'start_date'
    
    def days_remaining(self, obj):
        return obj.days_remaining()
    days_remaining.short_description = 'Days Left'
    
    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'expiry_date')
        }),
        ('Renewal', {
            'fields': ('auto_renew',)
        }),
    )


@admin.register(UserContentAccess)
class UserContentAccessAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'content_type', 
        'content_id', 
        'content_app', 
        'access_type', 
        'status', 
        'access_count'
    ]
    list_filter = ['access_type', 'status', 'content_app', 'content_type']
    search_fields = ['user__username', 'content_type', 'content_id']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Content', {
            'fields': ('user', 'content_type', 'content_id', 'content_app')
        }),
        ('Access Details', {
            'fields': ('access_type', 'status', 'expiry_date')
        }),
        ('Usage', {
            'fields': ('access_count', 'last_accessed')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 
        'user', 
        'total_amount', 
        'status', 
        'payment_method', 
        'created_at'
    ]
    list_filter = ['status', 'payment_method']
    search_fields = ['payment_id', 'order_id', 'user__username', 'user__email']
    readonly_fields = ['payment_id', 'created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'created_at'
    list_per_page = 20
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('payment_id', 'order_id', 'gateway_payment_id', 'gateway_order_id')
        }),
        ('Amount', {
            'fields': ('amount', 'tax', 'discount', 'total_amount', 'currency')
        }),
        ('Status', {
            'fields': ('payment_method', 'status', 'completed_at')
        }),
        ('Items', {
            'fields': ('items', 'gateway_response')
        }),
        ('Refund', {
            'fields': ('refund_amount', 'refund_reason', 'refunded_at')
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        for payment in queryset:
            payment.complete_payment()
        self.message_user(request, f'✅ {queryset.count()} payment(s) marked as completed.')
    mark_as_completed.short_description = '✅ Mark as completed'
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
        self.message_user(request, f'❌ {queryset.count()} payment(s) marked as failed.')
    mark_as_failed.short_description = '❌ Mark as failed'


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = [
        'action', 
        'user', 
        'content_type', 
        'content_id', 
        'content_app', 
        'created_at'
    ]
    list_filter = ['action', 'content_app']
    search_fields = ['user__username', 'action', 'content_type']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================
# CUSTOM ADMIN SITE (Optional)
# ============================================

class PaymentAdminSite(admin.AdminSite):
    site_header = 'Payment Admin Dashboard'
    site_title = 'Payment Admin'
    index_title = 'Payment Management'
    
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Add custom stats
        stats = {
            'total_revenue': Payment.objects.filter(status='completed').aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'total_payments': Payment.objects.filter(status='completed').count(),
            'active_subscriptions': UserSubscription.objects.filter(
                status='active', 
                expiry_date__gt=timezone.now()
            ).count(),
            'total_locked': PricingConfig.objects.filter(is_locked=True).count(),
        }
        
        # Add stats to app_list
        for app in app_list:
            if app['app_label'] == 'payments':
                app['stats'] = stats
        
        return app_list


# Register with default admin
# Already registered via decorators