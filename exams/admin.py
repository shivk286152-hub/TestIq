from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse
from django.contrib.admin import SimpleListFilter
from .models import (
    ExamCategory,
    SubCategory,
    MockTest,
    Subject,
    Question,
    Option,
    MockTestAttempt,
    UserAnswer,
    Testimonial,
    FAQ,
    Contact,
    CategoryContentSection,
    SubCategoryContentSection,
    MockTestContentSection,
    PricingConfig,
    UserContentAccess,
    Payment,
    Subscription,
    TransactionLog,
)


# ============================================
# CUSTOM FILTERS
# ============================================

class TestStatusFilter(SimpleListFilter):
    title = 'Test Status'
    parameter_name = 'test_status'
    
    def lookups(self, request, model_admin):
        return (
            ('has_questions', 'Has Questions'),
            ('no_questions', 'No Questions'),
            ('has_attempts', 'Has Attempts'),
            ('no_attempts', 'No Attempts'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'has_questions':
            return queryset.filter(questions__isnull=False).distinct()
        if self.value() == 'no_questions':
            return queryset.filter(questions__isnull=True)
        if self.value() == 'has_attempts':
            return queryset.filter(attempts__isnull=False).distinct()
        if self.value() == 'no_attempts':
            return queryset.filter(attempts__isnull=True)
        return queryset


class TestimonialStatusFilter(SimpleListFilter):
    title = 'Testimonial Status'
    parameter_name = 'testimonial_status'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('featured', 'Featured'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(status='pending')
        if self.value() == 'approved':
            return queryset.filter(status='approved')
        if self.value() == 'rejected':
            return queryset.filter(status='rejected')
        if self.value() == 'featured':
            return queryset.filter(is_featured=True)
        return queryset


# ============================================
# PAYMENT PRICING ADMIN
# ============================================

@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'content_id', 'pricing_type', 'price', 'is_active']
    list_filter = ['content_type', 'pricing_type', 'is_active']
    search_fields = ['content_id']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25


# ============================================
# USER CONTENT ACCESS ADMIN
# ============================================

@admin.register(UserContentAccess)
class UserContentAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'content_id', 'access_type', 'status', 'expiry_date']
    list_filter = ['content_type', 'access_type', 'status']
    search_fields = ['user__username', 'content_id']
    readonly_fields = ['start_date', 'created_at', 'updated_at']
    list_per_page = 25


# ============================================
# PAYMENT ADMIN
# ============================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'total_amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['payment_id', 'order_id', 'user__username']
    readonly_fields = ['payment_id', 'order_id', 'created_at', 'updated_at']
    list_per_page = 25


# ============================================
# SUBSCRIPTION ADMIN
# ============================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'expiry_date', 'is_active']
    list_filter = ['plan', 'status']
    search_fields = ['user__username']
    readonly_fields = ['start_date', 'created_at', 'updated_at']
    list_per_page = 25
    
    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True


# ============================================
# TRANSACTION LOG ADMIN
# ============================================

@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'content_type', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'action']
    readonly_fields = ['created_at']
    list_per_page = 50


# ============================================
# INLINE FOR CONTENT SECTIONS
# ============================================

class CategoryContentSectionInline(admin.TabularInline):
    model = CategoryContentSection
    extra = 1
    fields = ['order', 'section_title_en', 'section_title_hi', 'content_en', 'content_hi', 'image', 'image_alt_en', 'image_alt_hi', 'table_data', 'list_items', 'is_active']
    ordering = ['order']
    classes = ['collapse']


class SubCategoryContentSectionInline(admin.TabularInline):
    model = SubCategoryContentSection
    extra = 1
    fields = ['order', 'section_title_en', 'section_title_hi', 'content_en', 'content_hi', 'image', 'image_alt_en', 'image_alt_hi', 'table_data', 'list_items', 'is_active']
    ordering = ['order']
    classes = ['collapse']


class MockTestContentSectionInline(admin.TabularInline):
    model = MockTestContentSection
    extra = 1
    fields = ['order', 'section_title_en', 'section_title_hi', 'content_en', 'content_hi', 'image', 'image_alt_en', 'image_alt_hi', 'table_data', 'list_items', 'is_active']
    ordering = ['order']
    classes = ['collapse']


# ============================================
# OPTION INLINE
# ============================================

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    max_num = 4
    min_num = 2
    fields = ['order', 'text_en', 'text_hi', 'is_correct']
    ordering = ['order']


# ============================================
# QUESTION INLINE
# ============================================

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['order', 'question_en', 'marks', 'difficulty', 'topic']
    ordering = ['order']
    show_change_link = True


# ============================================
# SUBJECT INLINE
# ============================================

class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1
    fields = ['name', 'name_hi', 'start_question_no', 'end_question_no']
    ordering = ['start_question_no']


# ============================================
# USER ANSWER INLINE
# ============================================

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0
    fields = ['question', 'selected_option', 'is_correct', 'time_taken']
    readonly_fields = ['created_at', 'updated_at']
    show_change_link = True


# ============================================
# CATEGORY ADMIN
# ============================================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'get_subcategory_count', 'get_mocktest_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryContentSectionInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'description_hi', 'logo')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Banner', {
            'fields': ('banner_image', 'banner_title', 'banner_title_hi', 'banner_subtitle', 'banner_subtitle_hi'),
            'classes': ('collapse',)
        }),
        ('Syllabus', {
            'fields': ('syllabus_heading', 'syllabus_heading_hi', 'syllabus_description', 'syllabus_description_hi'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
    )
    
    def get_subcategory_count(self, obj):
        return obj.subcategories.count()
    get_subcategory_count.short_description = "SubCategories"
    
    def get_mocktest_count(self, obj):
        return MockTest.objects.filter(subcategory__category=obj).count()
    get_mocktest_count.short_description = "Mock Tests"


# ============================================
# SUBCATEGORY ADMIN
# ============================================

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'get_mocktest_count', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryContentSectionInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'name', 'name_hi', 'slug', 'icon', 'description', 'description_hi')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Banner', {
            'fields': ('banner_image', 'banner_title', 'banner_title_hi', 'banner_subtitle', 'banner_subtitle_hi'),
            'classes': ('collapse',)
        }),
        ('Syllabus', {
            'fields': ('syllabus_heading', 'syllabus_heading_hi', 'syllabus_description', 'syllabus_description_hi'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    def get_mocktest_count(self, obj):
        return obj.mock_tests.count()
    get_mocktest_count.short_description = "Mock Tests"


# ============================================
# MOCK TEST ADMIN
# ============================================

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subcategory', 'difficulty', 'question_count', 'duration', 'is_active']
    list_filter = ['difficulty', 'negative_marking_type', 'is_active', 'subcategory', TestStatusFilter]
    search_fields = ['title', 'description']
    inlines = [MockTestContentSectionInline, SubjectInline, QuestionInline]
    readonly_fields = ['total_questions', 'total_marks']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'title_hi', 'subcategory', 'description', 'description_hi')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Banner', {
            'fields': ('banner_image', 'banner_title', 'banner_title_hi', 'banner_subtitle', 'banner_subtitle_hi'),
            'classes': ('collapse',)
        }),
        ('Syllabus', {
            'fields': ('syllabus_heading', 'syllabus_heading_hi', 'syllabus_description', 'syllabus_description_hi'),
            'classes': ('collapse',)
        }),
        ('Test Settings', {
            'fields': ('difficulty', 'duration', 'time_limit', 'total_sections')
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value')
        }),
        ('Statistics', {
            'fields': ('total_questions', 'total_marks'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = "Questions"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.update_totals()


# ============================================
# SUBJECT ADMIN
# ============================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'start_question_no', 'end_question_no', 'question_count']
    list_filter = ['mock_test']
    search_fields = ['name', 'mock_test__title']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('mock_test', 'name', 'name_hi', 'description', 'description_hi')
        }),
        ('Question Range', {
            'fields': ('start_question_no', 'end_question_no')
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = "Questions"


# ============================================
# QUESTION ADMIN
# ============================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'mock_test', 'subject', 'question_preview', 'marks', 'difficulty', 'order']
    list_filter = ['mock_test', 'subject', 'difficulty']
    search_fields = ['question_en', 'question_hi', 'topic']
    inlines = [OptionInline]
    ordering = ['mock_test', 'order']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Relationships', {
            'fields': ('mock_test', 'subject')
        }),
        ('Question', {
            'fields': ('question_en', 'question_hi')
        }),
        ('Explanation', {
            'fields': ('explanation', 'explanation_hi'),
            'classes': ('collapse',)
        }),
        ('Scoring', {
            'fields': ('marks', 'negative_marks', 'override_test_negative')
        }),
        ('Metadata', {
            'fields': ('order', 'difficulty', 'topic')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
    question_preview.short_description = "Question"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.mock_test.update_totals()
    
    def delete_model(self, request, obj):
        mock_test = obj.mock_test
        super().delete_model(request, obj)
        mock_test.update_totals()


# ============================================
# OPTION ADMIN
# ============================================

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'text_preview', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__mock_test']
    search_fields = ['text_en', 'text_hi']
    
    def text_preview(self, obj):
        return obj.text_en[:50] + '...' if len(obj.text_en) > 50 else obj.text_en
    text_preview.short_description = "Option"


# ============================================
# MOCK TEST ATTEMPT ADMIN
# ============================================

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'mock_test', 'language', 'score_with_negative', 'percentage_display', 'correct_answers', 'wrong_answers', 'skipped_answers', 'is_completed', 'submitted_at']
    list_filter = ['is_completed', 'language', 'is_archived', 'mock_test']
    search_fields = ['user__username', 'user__email', 'mock_test__title']
    readonly_fields = ['started_at', 'submitted_at', 'raw_score', 'score_with_negative', 'total_marks', 'correct_answers', 'wrong_answers', 'skipped_answers', 'negative_marks_applied']
    inlines = [UserAnswerInline]
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'mock_test', 'language')
        }),
        ('Scores', {
            'fields': ('raw_score', 'score_with_negative', 'total_marks', 'negative_marks_applied')
        }),
        ('Statistics', {
            'fields': ('correct_answers', 'wrong_answers', 'skipped_answers')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'is_completed')
        }),
        ('Data Retention', {
            'fields': ('is_archived', 'archived_at', 'permanently_deleted', 'has_detailed_data'),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        return f"{obj.percentage_with_negative}%"
    percentage_display.short_description = "Score %"


# ============================================
# USER ANSWER ADMIN
# ============================================

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'attempt', 'question', 'selected_option_display', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['attempt__user__username', 'question__question_en']
    readonly_fields = ['created_at', 'updated_at']
    
    def selected_option_display(self, obj):
        return obj.selected_option.text_en[:30] if obj.selected_option else "Not Answered"
    selected_option_display.short_description = "Selected"


# ============================================
# TESTIMONIAL ADMIN
# ============================================

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['user', 'text_preview', 'stars', 'status', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'stars']
    search_fields = ['user__username', 'user__email', 'text']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    
    fieldsets = (
        ('Testimonial Info', {
            'fields': ('user', 'text', 'stars', 'achievement')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'is_active')
        }),
        ('Approval Info', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_testimonials', 'reject_testimonials', 'feature_testimonials']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Testimonial"
    
    def approve_testimonials(self, request, queryset):
        count = 0
        for testimonial in queryset:
            testimonial.approve(admin_user=request.user)
            count += 1
        self.message_user(request, f'{count} testimonials approved successfully.')
    approve_testimonials.short_description = "Approve selected testimonials"
    
    def reject_testimonials(self, request, queryset):
        count = queryset.update(status='rejected', is_active=False)
        self.message_user(request, f'{count} testimonials rejected.')
    reject_testimonials.short_description = "Reject selected testimonials"
    
    def feature_testimonials(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'{count} testimonials featured.')
    feature_testimonials.short_description = "Feature selected testimonials"


# ============================================
# FAQ ADMIN
# ============================================

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'order', 'is_active', 'show_on_homepage']
    list_filter = ['is_active', 'show_on_homepage', 'category']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_active', 'show_on_homepage']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('FAQ Info', {
            'fields': ('question', 'answer')
        }),
        ('Display', {
            'fields': ('order', 'category', 'is_active', 'show_on_homepage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = "Question"


# ============================================
# CONTACT ADMIN
# ============================================

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject_type', 'status', 'is_urgent', 'created_at']
    list_filter = ['status', 'subject_type', 'is_urgent']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at', 'ip_address', 'user_agent']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Contact Info', {
            'fields': ('name', 'email', 'phone', 'subject_type', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('status', 'is_urgent')
        }),
        ('Admin', {
            'fields': ('admin_notes', 'assigned_to'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('user', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_replied', 'mark_as_resolved']
    
    def mark_as_read(self, request, queryset):
        queryset.update(status='read')
        self.message_user(request, f'{queryset.count()} contacts marked as read.')
    mark_as_read.short_description = "Mark as Read"
    
    def mark_as_replied(self, request, queryset):
        queryset.update(status='replied', replied_at=timezone.now())
        self.message_user(request, f'{queryset.count()} contacts marked as replied.')
    mark_as_replied.short_description = "Mark as Replied"
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
        self.message_user(request, f'{queryset.count()} contacts marked as resolved.')
    mark_as_resolved.short_description = "Mark as Resolved"


# ============================================
# CONTENT SECTION ADMINS
# ============================================

@admin.register(CategoryContentSection)
class CategoryContentSectionAdmin(admin.ModelAdmin):
    list_display = ['get_title', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['section_title_en', 'content_en']
    
    def get_title(self, obj):
        return obj.section_title_en or f"Section {obj.order}"
    get_title.short_description = "Title"


@admin.register(SubCategoryContentSection)
class SubCategoryContentSectionAdmin(admin.ModelAdmin):
    list_display = ['get_title', 'subcategory', 'order', 'is_active']
    list_filter = ['subcategory', 'is_active']
    search_fields = ['section_title_en', 'content_en']
    
    def get_title(self, obj):
        return obj.section_title_en or f"Section {obj.order}"
    get_title.short_description = "Title"


@admin.register(MockTestContentSection)
class MockTestContentSectionAdmin(admin.ModelAdmin):
    list_display = ['get_title', 'mock_test', 'order', 'is_active']
    list_filter = ['mock_test', 'is_active']
    search_fields = ['section_title_en', 'content_en']
    
    def get_title(self, obj):
        return obj.section_title_en or f"Section {obj.order}"
    get_title.short_description = "Title"


# ============================================
# ADMIN SITE CONFIGURATION
# ============================================

admin.site.site_header = "TestIQ Admin"
admin.site.site_title = "TestIQ Admin Portal"
admin.site.index_title = "Welcome to TestIQ Admin"