from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Max, Sum
from .models import (
    ExamCategory, SubCategory, MockTest, Subject, 
    Question, Option, MockTestAttempt, UserAnswer, Testimonial
)

# ============================================
# INLINE MODELS
# ============================================

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    max_num = 4
    min_num = 2
    fields = ['text_en', 'text_hi', 'is_correct', 'order']
    ordering = ['order']


# ============================================
# QUESTION ADMIN
# ============================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_preview', 'mock_test', 'subject', 'difficulty', 'topic', 'marks', 'negative_marks', 'order']
    list_filter = ['mock_test', 'subject', 'difficulty']
    search_fields = ['question_en', 'question_hi', 'topic']
    list_editable = ['marks', 'negative_marks', 'order', 'difficulty', 'topic']
    list_per_page = 20
    inlines = [OptionInline]

    fieldsets = (
        ('Question Information', {
            'fields': ('mock_test', 'subject', 'order')
        }),
        ('Question Content', {
            'fields': ('question_en', 'question_hi')
        }),
        ('Question Classification', {
            'fields': ('difficulty', 'topic'),
        }),
        ('Explanation', {
            'fields': ('explanation', 'explanation_hi'),
        }),
        ('Marking Scheme', {
            'fields': ('marks', 'negative_marks')
        }),
    )

    def question_preview(self, obj):
        return obj.question_en[:75] + '...' if len(obj.question_en) > 75 else obj.question_en
    question_preview.short_description = 'Question'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            mock_test_id = request.GET.get('mock_test') or request.POST.get('mock_test')
            if mock_test_id:
                max_order = Question.objects.filter(mock_test_id=mock_test_id).aggregate(Max('order'))['order__max']
                form.base_fields['order'].initial = (max_order or 0) + 1
        return form

    def save_model(self, request, obj, form, change):
        if not obj.order and obj.mock_test:
            max_order = Question.objects.filter(mock_test=obj.mock_test).aggregate(Max('order'))['order__max']
            obj.order = (max_order or 0) + 1
        super().save_model(request, obj, form, change)


# ============================================
# EXAM CATEGORY ADMIN
# ============================================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description_short']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20

    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else '-'
    description_short.short_description = 'Description'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'description_short']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20

    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else '-'
    description_short.short_description = 'Description'


# ============================================
# MOCK TEST ADMIN
# ============================================

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'subcategory', 'difficulty', 'duration', 'total_marks',
        'negative_marking_type', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'difficulty', 'negative_marking_type', 'subcategory__category']
    search_fields = ['title']
    list_editable = ['is_active', 'difficulty']
    list_per_page = 20

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subcategory', 'difficulty', 'is_active')
        }),
        ('Test Settings', {
            'fields': ('duration', 'time_limit', 'total_marks')
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subcategory')


# ============================================
# SUBJECT ADMIN
# ============================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'start_question_no', 'end_question_no']
    list_filter = ['mock_test']
    search_fields = ['name', 'mock_test__title']
    list_per_page = 20


# ============================================
# OPTION ADMIN
# ============================================

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'text_en', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__mock_test']
    search_fields = ['text_en', 'text_hi', 'question__question_en']
    list_editable = ['is_correct', 'order']
    list_per_page = 30


# ============================================
# MOCK TEST ATTEMPT ADMIN
# ============================================

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'score', 'percentage', 'correct_answers',
                    'wrong_answers', 'skipped_answers', 'is_completed', 'submitted_at']
    list_filter = ['is_completed', 'mock_test']
    search_fields = ['user__username', 'user__email', 'mock_test__title']
    readonly_fields = ['started_at', 'submitted_at', 'score', 'total_marks',
                       'correct_answers', 'wrong_answers', 'skipped_answers']
    list_per_page = 20

    fieldsets = (
        ('User & Test', {'fields': ('user', 'mock_test', 'language')}),
        ('Performance', {'fields': ('score', 'total_marks', 'correct_answers', 'wrong_answers', 'skipped_answers')}),
        ('Timing', {'fields': ('started_at', 'submitted_at', 'is_completed')}),
    )

    @admin.display(description='Percentage')
    def percentage(self, obj):
        return f"{obj.percentage}%"


# ============================================
# USER ANSWER ADMIN
# ============================================

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'attempt', 'question', 'selected_option', 'is_correct', 'time_taken']
    list_filter = ['is_correct', 'attempt__mock_test']
    search_fields = ['attempt__user__username', 'question__question_en']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 30

    fieldsets = (
        ('Attempt Info', {'fields': ('attempt', 'question')}),
        ('Answer Details', {'fields': ('selected_option', 'is_correct', 'time_taken')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ============================================
# TESTIMONIAL ADMIN
# ============================================

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['user', 'stars', 'is_active', 'is_featured', 'display_order', 'created_at']
    list_filter = ['is_active', 'is_featured', 'stars']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'text']
    list_editable = ['is_active', 'is_featured', 'display_order']

    fieldsets = (
        ('User Information', {'fields': ('user',)}),
        ('Testimonial Content', {'fields': ('text', 'stars', 'achievement')}),
        ('Admin Control', {'fields': ('is_active', 'is_featured', 'display_order')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ============================================
# ADMIN SITE HEADER
# ============================================

admin.site.site_header = 'Mock Test Administration'
admin.site.site_title = 'Mock Test Admin'
admin.site.index_title = 'Mock Test Management'
