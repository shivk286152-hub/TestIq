from django.contrib import admin
<<<<<<< HEAD
from .models import *

# =========================
# OPTION INLINE (Inside Question)
# =========================
=======
from django.utils.html import format_html
from django.db.models import Max
from .models import (
    ExamCategory, SubCategory, MockTest, Subject, 
    Question, Option, MockTestAttempt, UserAnswer
)

# Register your models here.

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
class OptionInline(admin.TabularInline):
    """Inline admin for options within question"""
    model = Option
<<<<<<< HEAD
    extra = 4   # Show 4 empty options by default
    min_num = 2
    max_num = 6

=======
    extra = 4  # Show 4 empty option forms by default
    max_num = 4  # Maximum 4 options
    min_num = 2  # Minimum 2 options
    fields = ['text_en', 'text_hi', 'is_correct', 'order']
    ordering = ['order']
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)

# =========================
# QUESTION REVIEW INLINE
# =========================
class QuestionReviewInline(admin.StackedInline):
    model = QuestionReview
    extra = 0
    max_num = 1


# =========================
# QUESTION ADMIN
# =========================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = ('id', 'mock_test', 'subject', 'short_question')
    list_filter = ('mock_test', 'subject')
    search_fields = ('question_en', 'question_hi')
    inlines = [OptionInline, QuestionReviewInline]

    def short_question(self, obj):
        return obj.question_en[:50]
    short_question.short_description = "Question"
=======
    list_display = ['id', 'question_preview', 'mock_test', 'subject', 'marks', 'negative_marks', 'order']
    list_filter = ['mock_test', 'subject', 'marks']
    search_fields = ['question_en', 'question_hi']
    list_editable = ['marks', 'negative_marks', 'order']
    list_per_page = 20
    
    # Show options inline with question
    inlines = [OptionInline]
    
    fieldsets = (
        ('Question Information', {
            'fields': ('mock_test', 'subject', 'order')
        }),
        ('Question Content', {
            'fields': ('question_en', 'question_hi')
        }),
        ('Explanation', {
            'fields': ('explanation',),
            'classes': ('wide',)
        }),
        ('Marking Scheme', {
            'fields': ('marks', 'negative_marks')
        }),
    )
    
    def question_preview(self, obj):
        """Show preview of question text"""
        return obj.question_en[:75] + '...' if len(obj.question_en) > 75 else obj.question_en
    question_preview.short_description = 'Question'
    
    def get_form(self, request, obj=None, **kwargs):
        """Auto-set order when adding new question"""
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Only for new objects
            # Get the next order number for the mock test
            mock_test_id = request.GET.get('mock_test') or request.POST.get('mock_test')
            if mock_test_id:
                max_order = Question.objects.filter(mock_test_id=mock_test_id).aggregate(
                    Max('order')
                )['order__max']
                initial_order = (max_order or 0) + 1
                form.base_fields['order'].initial = initial_order
        return form
    
    def save_model(self, request, obj, form, change):
        """Auto-set order if not provided"""
        if not obj.order and obj.mock_test:
            # Get the next order number
            max_order = Question.objects.filter(mock_test=obj.mock_test).aggregate(
                Max('order')
            )['order__max']
            obj.order = (max_order or 0) + 1
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related(
            'mock_test', 'subject'
        )

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description_short']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else '-'
    description_short.short_description = 'Description'
    
    # Add this to handle any errors
    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, f"Error saving category: {str(e)}", level='ERROR')

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'description_short']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    list_per_page = 20
    prepopulated_fields = {'slug': ('name',)}
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else '-'
    description_short.short_description = 'Description'
    
    # Add this to handle any errors
    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, f"Error saving subcategory: {str(e)}", level='ERROR')
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)


# =========================
# SUBJECT INLINE (Inside MockTest)
# =========================
class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1


# =========================
# MOCK TEST ADMIN
# =========================
@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = ('title', 'subcategory', 'duration', 'is_active', 'created_at')
    list_filter = ('subcategory', 'is_active')
    search_fields = ('title',)
    inlines = [SubjectInline]
=======
    list_display = ['title', 'subcategory', 'duration', 'total_marks', 'is_active', 'created_at']
    list_filter = ['is_active', 'subcategory__category', 'subcategory']
    search_fields = ['title']
    list_editable = ['is_active']
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subcategory', 'is_active')
        }),
        ('Test Settings', {
            'fields': ('duration', 'time_limit', 'total_marks')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subcategory')
    
    # Add this to handle any errors
    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, f"Error saving mock test: {str(e)}", level='ERROR')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'start_question_no', 'end_question_no', 'question_count']
    list_filter = ['mock_test']
    search_fields = ['name', 'mock_test__title']
    list_per_page = 20
    
    def question_count(self, obj):
        """Show number of questions in this subject"""
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('mock_test').prefetch_related('questions')

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'option_preview', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__mock_test']
    search_fields = ['text_en', 'text_hi', 'question__question_en']
    list_editable = ['is_correct', 'order']
    list_per_page = 30
    
    def option_preview(self, obj):
        """Preview of option text"""
        text = obj.text_en[:40] + '...' if len(obj.text_en) > 40 else obj.text_en
        if obj.is_correct:
            return format_html('<b style="color: green;">✓ {}</b>', text)
        return text
    option_preview.short_description = 'Option Text'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question')
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)


# =========================
# EXAM CATEGORY ADMIN
# =========================
@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'slug')


# =========================
# SUB CATEGORY ADMIN
# =========================
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    list_filter = ('category',)
    search_fields = ('name',)


# =========================
# ATTEMPT ADMIN
# =========================
@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = (
        'user', 'mock_test', 'score',
        'percentage', 'correct_answers',
        'wrong_answers', 'is_completed'
    )
    list_filter = ('mock_test', 'is_completed')
    readonly_fields = ('percentage', 'time_taken')


# =========================
# RANK ADMIN
# =========================
@admin.register(TestRank)
class TestRankAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'rank', 'percentile', 'total_participants')


@admin.register(TopRanker)
class TopRankerAdmin(admin.ModelAdmin):
    list_display = ('mock_test', 'user', 'rank', 'percentage')
    list_filter = ('mock_test',)


@admin.register(UserRankHistory)
class UserRankHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'mock_test', 'rank', 'percentile')
    list_filter = ('mock_test', 'user')


@admin.register(RankStatistics)
class RankStatisticsAdmin(admin.ModelAdmin):
    list_display = (
        'mock_test',
        'total_attempts',
        'highest_score',
        'average_score',
        'last_updated'
    )


# =========================
# ATTEMPT REVIEW ADMIN
# =========================
@admin.register(AttemptReview)
class AttemptReviewAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'easy_accuracy', 'medium_accuracy', 'hard_accuracy')


@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'is_correct', 'found_difficult')


@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'attempt', 'started_at', 'is_completed')
=======
    list_display = ['user', 'mock_test', 'score', 'percentage_display', 'correct_answers', 
                   'wrong_answers', 'skipped_answers', 'is_completed', 'submitted_at']
    list_filter = ['is_completed', 'mock_test']
    search_fields = ['user__username', 'user__email', 'mock_test__title']
    readonly_fields = ['started_at', 'submitted_at', 'score', 'total_marks', 
                      'correct_answers', 'wrong_answers', 'skipped_answers']
    list_per_page = 20
    
    fieldsets = (
        ('User & Test', {
            'fields': ('user', 'mock_test')
        }),
        ('Performance', {
            'fields': ('score', 'total_marks', 'correct_answers', 'wrong_answers', 'skipped_answers')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'is_completed')
        }),
    )
    
    def percentage_display(self, obj):
        """Show percentage with color coding"""
        percentage = obj.percentage
        color = 'green' if percentage >= 60 else 'orange' if percentage >= 35 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', 
                          color, percentage)
    percentage_display.short_description = 'Percentage'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'mock_test')

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_info', 'question_preview', 'answer_status', 'time_taken']
    list_filter = ['is_correct', 'attempt__mock_test']
    search_fields = ['attempt__user__username', 'question__question_en']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 30
    
    fieldsets = (
        ('Attempt Info', {
            'fields': ('attempt', 'question')
        }),
        ('Answer Details', {
            'fields': ('selected_option', 'is_correct', 'time_taken')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        return f"{obj.attempt.user.username} ({obj.attempt.user.email})"
    user_info.short_description = 'User'
    
    def question_preview(self, obj):
        return obj.question.question_en[:50] + '...'
    question_preview.short_description = 'Question'
    
    def answer_status(self, obj):
        if obj.is_correct:
            return format_html('<span style="color: green;">✓ Correct</span>')
        elif obj.selected_option:
            return format_html('<span style="color: red;">✗ Wrong</span>')
        else:
            return format_html('<span style="color: gray;">- Skipped</span>')
    answer_status.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attempt', 'attempt__user', 'question', 'selected_option'
        )

# Customize admin site header
admin.site.site_header = 'Mock Test Administration'
admin.site.site_title = 'Mock Test Admin'
admin.site.index_title = 'Mock Test Management'
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
