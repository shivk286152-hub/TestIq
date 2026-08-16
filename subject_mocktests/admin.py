from django.contrib import admin
from django.db.models import Count
from .models import Subject, Topic, MockTest, Question, Option, MockTestAttempt, UserAnswer


class OptionInline(admin.TabularInline):
    """Inline options for questions"""
    model = Option
    extra = 4
    max_num = 4
    fields = ['text_en', 'text_hi', 'is_correct', 'order']
    ordering = ['order']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'test_count', 'created_at']
    list_filter = ['order']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def test_count(self, obj):
        """Count active mock tests for this subject"""
        return obj.mock_tests.filter(is_active=True).count()
    test_count.short_description = 'Active Tests'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subject', 'order', 'test_count']
    list_filter = ['subject', 'order']
    search_fields = ['name', 'subject__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def test_count(self, obj):
        """Count active mock tests for this topic"""
        return obj.mock_tests.filter(is_active=True).count()
    test_count.short_description = 'Active Tests'


@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'topic', 'difficulty', 'duration', 'total_questions', 'is_active', 'is_free']
    list_filter = ['subject', 'topic', 'difficulty', 'is_active', 'is_free']
    search_fields = ['title', 'subject__name', 'topic__name']
    list_editable = ['is_active', 'is_free']  # Both fields must be in list_display
    readonly_fields = ['total_questions', 'total_marks', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'subject', 'topic', 'description')
        }),
        ('Settings', {
            'fields': ('difficulty', 'duration', 'is_active', 'is_free')
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value'),
            'description': 'Configure negative marking rules for wrong answers.'
        }),
        ('Instructions', {
            'fields': ('instructions',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_questions', 'total_marks'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Update totals when saving from admin"""
        super().save_model(request, obj, form, change)
        obj.update_totals()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_question', 'mock_test', 'difficulty', 'marks', 'order', 'has_options']
    list_filter = ['mock_test', 'difficulty']
    search_fields = ['question_en', 'question_hi', 'topic']
    list_editable = ['marks', 'order', 'difficulty']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OptionInline]
    
    fieldsets = (
        ('Question Information', {
            'fields': ('mock_test', 'order', 'difficulty', 'topic')
        }),
        ('Content (English)', {
            'fields': ('question_en', 'explanation_en')
        }),
        ('Content (Hindi)', {
            'fields': ('question_hi', 'explanation_hi'),
            'classes': ('collapse',)
        }),
        ('Marks & Scoring', {
            'fields': ('marks', 'negative_marks_override'),
            'description': 'Leave negative_marks_override blank to use difficulty-based defaults (Easy:0.25, Medium:0.33, Hard:0.50, Expert:0.75)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def short_question(self, obj):
        """Get shortened question text"""
        if not obj.question_en:
            return f"Question {obj.id}"
        return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
    short_question.short_description = 'Question'
    short_question.admin_order_field = 'question_en'
    
    def has_options(self, obj):
        """Check if question has options"""
        return obj.options.count() > 0
    has_options.boolean = True
    has_options.short_description = 'Has Options'
    
    def save_model(self, request, obj, form, change):
        """Update mock test totals when saving question"""
        super().save_model(request, obj, form, change)
        if obj.mock_test:
            obj.mock_test.update_totals()
    
    def delete_model(self, request, obj):
        """Update mock test totals when deleting question"""
        mock_test = obj.mock_test
        super().delete_model(request, obj)
        if mock_test:
            mock_test.update_totals()


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__mock_test']
    list_editable = ['is_correct', 'order']
    search_fields = ['text_en', 'text_hi', 'question__question_en']
    # Remove readonly_fields since Option doesn't have created_at/updated_at
    
    def short_text(self, obj):
        """Get shortened option text"""
        if not obj.text_en:
            return f"Option {obj.id}"
        return obj.text_en[:30] + '...' if len(obj.text_en) > 30 else obj.text_en
    short_text.short_description = 'Option'
    short_text.admin_order_field = 'text_en'
    
    def save_model(self, request, obj, form, change):
        """When a correct option is saved, uncheck other options"""
        super().save_model(request, obj, form, change)
        # If this option is correct, ensure no other correct options for this question
        if obj.is_correct:
            Option.objects.filter(
                question=obj.question, 
                is_correct=True
            ).exclude(id=obj.id).update(is_correct=False)
        # Update mock test totals if question has a mock test
        if obj.question and obj.question.mock_test:
            obj.question.mock_test.update_totals()
    
    def delete_model(self, request, obj):
        """Update mock test totals when deleting option"""
        mock_test = obj.question.mock_test if obj.question else None
        super().delete_model(request, obj)
        if mock_test:
            mock_test.update_totals()


@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'score', 'percentage_display', 'correct_answers', 'is_completed', 'submitted_at']
    list_filter = ['is_completed', 'mock_test', 'language', 'is_paid_user']
    search_fields = ['user__username', 'user__email', 'mock_test__title']
    # Remove 'created_at' from readonly_fields if it doesn't exist
    readonly_fields = ['raw_score', 'score_with_negative', 'total_marks', 'correct_answers', 
                       'wrong_answers', 'skipped_answers', 'negative_marks_applied', 
                       'started_at', 'submitted_at']
    
    fieldsets = (
        ('User & Test Information', {
            'fields': ('user', 'mock_test', 'language')
        }),
        ('Scores', {
            'fields': ('raw_score', 'score_with_negative', 'total_marks', 'negative_marks_applied')
        }),
        ('Performance Metrics', {
            'fields': ('correct_answers', 'wrong_answers', 'skipped_answers')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'is_completed')
        }),
        ('Data Retention', {
            'fields': ('is_archived', 'permanently_deleted', 'has_detailed_data'),
            'classes': ('collapse',)
        }),
    )
    
    def percentage_display(self, obj):
        """Display percentage with proper formatting"""
        percentage = obj.percentage if hasattr(obj, 'percentage') else 0
        return f"{percentage}%"
    percentage_display.short_description = 'Percentage'
    percentage_display.admin_order_field = 'score'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list display"""
        return super().get_queryset(request).select_related('user', 'mock_test')


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_display', 'question_preview', 'selected_option_text', 'is_correct', 'marks_display']
    list_filter = ['is_correct', 'attempt__mock_test']
    search_fields = ['attempt__user__username', 'question__question_en']
    # Remove readonly_fields if Option doesn't have created_at/updated_at
    
    def user_display(self, obj):
        """Display user name"""
        return obj.attempt.user.username if obj.attempt else 'N/A'
    user_display.short_description = 'User'
    user_display.admin_order_field = 'attempt__user__username'
    
    def question_preview(self, obj):
        """Preview question text"""
        if not obj.question:
            return 'N/A'
        text = obj.question.question_en or f"Question {obj.question.id}"
        return text[:40] + '...' if len(text) > 40 else text
    question_preview.short_description = 'Question'
    
    def selected_option_text(self, obj):
        """Display selected option text"""
        if obj.selected_option:
            return obj.selected_option.text_en[:30] + '...' if len(obj.selected_option.text_en) > 30 else obj.selected_option.text_en
        return 'Not Answered'
    selected_option_text.short_description = 'Selected Option'
    
    def marks_display(self, obj):
        """Display marks obtained for this answer"""
        if not obj.selected_option:
            return "0 (Skipped)"
        if obj.is_correct:
            return f"+{obj.question.marks if obj.question else 1}"
        else:
            negative = obj.question.get_effective_negative_marks() if obj.question else 0.25
            return f"-{negative}"
    marks_display.short_description = 'Marks'


# ============================================
# ADMIN SITE CONFIGURATION
# ============================================

# Customize admin site headers
admin.site.site_header = 'Subject Mock Tests Admin'
admin.site.site_title = 'Subject Mock Tests'
admin.site.index_title = 'Subject Mock Tests Management'


# ============================================
# ADDITIONAL CUSTOMIZATIONS (Optional)
# ============================================

# Customize admin template for better UX
class MockTestAdminWithActions(MockTestAdmin):
    """Add custom actions to mock test admin"""
    actions = ['mark_active', 'mark_inactive']
    
    def mark_active(self, request, queryset):
        """Mark selected tests as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} tests marked as active.')
    mark_active.short_description = 'Mark selected tests as active'
    
    def mark_inactive(self, request, queryset):
        """Mark selected tests as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} tests marked as inactive.')
    mark_inactive.short_description = 'Mark selected tests as inactive'