from django.contrib import admin
from .models import (
    ExamCategory, SubCategory, MockTest, Subject, 
    Question, Option, MockTestAttempt, UserAnswer, Testimonial
)

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    max_num = 4
    fields = ['text_en', 'text_hi', 'is_correct', 'order']

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug']
    list_filter = ['category']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subcategory', 'difficulty', 'duration', 'total_questions', 'total_marks', 'is_active']
    list_filter = ['is_active', 'difficulty', 'subcategory']
    search_fields = ['title']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subcategory', 'difficulty', 'is_active')
        }),
        ('Test Settings', {
            'fields': ('duration', 'time_limit')
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value'),
            'description': 'Choose "Per Question Negative Marking" to use per-question settings with difficulty-based defaults (Easy:0.25, Medium:0.33, Hard:0.50)'
        }),
        ('Auto-calculated Fields', {
            'fields': ('total_questions', 'total_marks'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_questions', 'total_marks']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'start_question_no', 'end_question_no']
    list_filter = ['mock_test']
    search_fields = ['name']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_question', 'mock_test', 'subject', 'difficulty', 'marks', 'negative_marks_display', 'order']
    list_filter = ['mock_test', 'subject', 'difficulty']
    search_fields = ['question_en']
    list_editable = ['marks', 'order', 'difficulty']
    inlines = [OptionInline]
    
    fieldsets = (
        ('Question', {
            'fields': ('mock_test', 'subject', 'order', 'difficulty', 'topic')
        }),
        ('Content', {
            'fields': ('question_en', 'question_hi', 'explanation', 'explanation_hi')
        }),
        ('Marks', {
            'fields': ('marks', 'negative_marks', 'override_test_negative'),
            'description': 'Check "override_test_negative" to use custom negative marks. Uncheck to use test defaults or difficulty-based (Easy:0.25, Medium:0.33, Hard:0.50)'
        }),
    )
    
    def short_question(self, obj):
        return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
    short_question.short_description = 'Question'
    
    def negative_marks_display(self, obj):
        if obj.override_test_negative and obj.negative_marks:
            return f"Custom: {obj.negative_marks}"
        elif obj.mock_test.negative_marking_type == 'per_question':
            default = obj.DIFFICULTY_NEGATIVE_MARKS.get(obj.difficulty, 0.25)
            return f"Default ({obj.difficulty}): {default}"
        else:
            return f"Test: {obj.mock_test.get_negative_marking_description()}"
    negative_marks_display.short_description = 'Negative Marks'

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'text_preview', 'question', 'is_correct', 'order']
    list_filter = ['is_correct']
    list_editable = ['is_correct', 'order']
    
    def text_preview(self, obj):
        return obj.text_en[:30] + '...' if len(obj.text_en) > 30 else obj.text_en
    text_preview.short_description = 'Option'

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'raw_score', 'score_with_negative', 'accuracy', 'correct_answers', 'is_completed']
    list_filter = ['is_completed', 'mock_test']
    search_fields = ['user__username']
    readonly_fields = ['raw_score', 'score_with_negative', 'total_marks', 'correct_answers', 
                       'wrong_answers', 'skipped_answers', 'negative_marks_applied']
    
    def accuracy(self, obj):
        return f"{obj.percentage_with_negative}%"
    accuracy.short_description = 'Accuracy'

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'question_preview', 'is_correct', 'marks']
    list_filter = ['is_correct']
    
    def user(self, obj):
        return obj.attempt.user.username
    user.short_description = 'User'
    
    def question_preview(self, obj):
        return obj.question.question_en[:30] + '...'
    question_preview.short_description = 'Question'
    
    def marks(self, obj):
        if not obj.selected_option:
            return "Skipped (0)"
        if obj.is_correct:
            return f"+{obj.question.marks}"
        else:
            return f"-{obj.question.get_effective_negative_marks()}"
    marks.short_description = 'Marks'

from django.contrib import admin
from django.utils.html import format_html
from .models import FAQ

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'order', 'status_badge', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    list_editable = ['order']
    search_fields = ['question', 'answer']
    list_per_page = 20
    save_on_top = True
    
    fieldsets = (
        ('Question Information', {
            'fields': ('question', 'answer')
        }),
        ('Categorization', {
            'fields': ('category', 'order'),
            'classes': ('wide',),
            'description': 'Organize FAQs by category and set display order'
        }),
        ('Visibility', {
            'fields': ('is_active',),
            'classes': ('wide',),
            'description': 'Toggle visibility on the website'
        }),
    )
    
    def question_preview(self, obj):
        """Show truncated question with tooltip"""
        return format_html(
            '<span title="{}">{}</span>',
            obj.question,
            obj.question[:75] + '...' if len(obj.question) > 75 else obj.question
        )
    question_preview.short_description = 'Question'
    question_preview.admin_order_field = 'question'
    
    def status_badge(self, obj):
        """Show colored status badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #ef4444; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">Inactive</span>'
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'
    
    actions = ['activate_faqs', 'deactivate_faqs']
    
    def activate_faqs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} FAQ(s) activated successfully.')
    activate_faqs.short_description = "Activate selected FAQs"
    
    def deactivate_faqs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} FAQ(s) deactivated successfully.')
    deactivate_faqs.short_description = "Deactivate selected FAQs"
    
    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',)
        }
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['user', 'stars', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'stars']
    list_editable = ['is_active', 'is_featured']
    search_fields = ['user__username']
    
    actions = ['approve_testimonials']
    
    def approve_testimonials(self, request, queryset):
        queryset.update(is_active=True)
    approve_testimonials.short_description = "Approve selected testimonials"

admin.site.site_header = 'Mock Test Admin'
admin.site.site_title = 'Mock Test Admin'
admin.site.index_title = 'Mock Test Management'