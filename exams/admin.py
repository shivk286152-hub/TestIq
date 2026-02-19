from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ExamCategory, SubCategory, MockTest, Subject, Question, 
    Option, MockTestAttempt, UserAnswer, TestRank, TopRanker,
    UserRankHistory, RankStatistics, QuestionReview, AttemptReview,
    QuestionFeedback, ReviewSession
)

# ==================== INLINE CLASSES ====================

class OptionInline(admin.TabularInline):
    """Shows all options directly under question"""
    model = Option
    extra = 4
    max_num = 4
    fields = ['option_letter', 'text_en', 'text_hi', 'is_correct']
    
    def option_letter(self, obj):
        """Auto-assign A,B,C,D based on position"""
        if not obj.pk:  # New objects
            count = self.model.objects.filter(question=self.instance).count()
            return chr(65 + count)  # A=65, B=66, etc.
        return obj.option_letter
    option_letter.short_description = "Option"

class QuestionInline(admin.TabularInline):
    """Shows questions directly under mock test"""
    model = Question
    extra = 1
    fields = ['question_number', 'question_en', 'subject', 'explanation_preview']
    readonly_fields = ['explanation_preview']
    
    def explanation_preview(self, obj):
        if obj.explanation:
            return obj.explanation[:50] + "..." if len(obj.explanation) > 50 else obj.explanation
        return "-"
    explanation_preview.short_description = "Explanation"

# ==================== MAIN ADMIN CLASSES ====================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'subcategories_count', 'is_active']
    list_filter = ['name']
    search_fields = ['name']
    
    def subcategories_count(self, obj):
        return obj.subcategories.count()
    subcategories_count.short_description = "Sub Categories"
    
    def is_active(self, obj):
        return obj.subcategories.filter(mock_tests__is_active=True).exists()
    is_active.boolean = True
    is_active.short_description = "Has Active Tests"

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'tests_count']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    
    def tests_count(self, obj):
        return obj.mock_tests.count()
    tests_count.short_description = "Mock Tests"

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subcategory', 'duration', 'is_active', 'questions_count']
    list_filter = ['is_active', 'subcategory__category']
    search_fields = ['title', 'subcategory__name']
    list_editable = ['is_active']
    
    inlines = [QuestionInline]
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = "Total Questions"

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'question_range']
    list_filter = ['mock_test__subcategory__category']
    search_fields = ['name', 'mock_test__title']
    
    def question_range(self, obj):
        return f"{obj.start_question_no} - {obj.end_question_no}"
    question_range.short_description = "Question Range"

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """ALL IN ONE PLACE - Question + Options + Explanation"""
    list_display = ['id', 'mock_test', 'subject', 'question_preview', 'options_count']
    list_filter = ['mock_test', 'subject']
    search_fields = ['question_en', 'question_hi']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('mock_test', 'subject', 'question_number')
        }),
        ('Question Text', {
            'fields': ('question_en', 'question_hi'),
            'description': 'Enter question in English and Hindi'
        }),
        ('Explanation', {
            'fields': ('explanation',),
            'description': 'Add explanation here (optional)'
        }),
    )
    
    inlines = [OptionInline]  # Options show right here!
    
    def question_preview(self, obj):
        return obj.question_en[:70] + "..." if len(obj.question_en) > 70 else obj.question_en
    question_preview.short_description = "Question"
    
    def options_count(self, obj):
        count = obj.options.count()
        return f"{count}/4"
    options_count.short_description = "Options"

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_link', 'option_letter', 'text_preview', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['text_en', 'question__question_en']
    list_editable = ['is_correct']
    
    def question_link(self, obj):
        return f"Q{obj.question.id}: {obj.question.question_en[:30]}..."
    question_link.short_description = "Question"
    
    def text_preview(self, obj):
        return obj.text_en[:40] + "..." if len(obj.text_en) > 40 else obj.text_en
    text_preview.short_description = "Option Text"

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'percentage', 'correct_answers', 'wrong_answers', 'is_completed']
    list_filter = ['is_completed', 'mock_test']
    search_fields = ['user__username', 'mock_test__title']
    readonly_fields = ['percentage', 'time_taken']

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question_preview', 'selected_option', 'is_correct']
    list_filter = ['attempt__mock_test']
    search_fields = ['attempt__user__username']
    
    def question_preview(self, obj):
        return obj.question.question_en[:50] + "..."
    question_preview.short_description = "Question"
    
    def is_correct(self, obj):
        if obj.selected_option and obj.selected_option.is_correct:
            return format_html('<span style="color:green;">✓ Correct</span>')
        elif obj.selected_option:
            return format_html('<span style="color:red;">✗ Wrong</span>')
        return format_html('<span style="color:gray;">- Skipped</span>')
    is_correct.short_description = "Result"

# ==================== RANKING ADMIN ====================

@admin.register(TestRank)
class TestRankAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'rank', 'percentile']
    list_filter = ['attempt__mock_test']
    search_fields = ['attempt__user__username']
    
    def user(self, obj):
        return obj.attempt.user.username
    user.short_description = "User"
    
    def mock_test(self, obj):
        return obj.attempt.mock_test.title
    mock_test.short_description = "Test"

@admin.register(TopRanker)
class TopRankerAdmin(admin.ModelAdmin):
    list_display = ['rank_display', 'user', 'mock_test', 'percentage', 'time_taken']
    list_filter = ['mock_test']
    search_fields = ['user__username']
    
    def rank_display(self, obj):
        if obj.rank == 1:
            return format_html('<span style="color:gold; font-weight:bold;">🥇 1st</span>')
        elif obj.rank == 2:
            return format_html('<span style="color:silver; font-weight:bold;">🥈 2nd</span>')
        elif obj.rank == 3:
            return format_html('<span style="color:#cd7f32; font-weight:bold;">🥉 3rd</span>')
        return f"{obj.rank}th"
    rank_display.short_description = "Rank"

@admin.register(RankStatistics)
class RankStatisticsAdmin(admin.ModelAdmin):
    list_display = ['mock_test', 'total_attempts', 'highest_score', 'average_score', 'last_updated']
    readonly_fields = ['last_updated']

@admin.register(UserRankHistory)
class UserRankHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'rank', 'percentile', 'achieved_at']
    list_filter = ['mock_test']
    search_fields = ['user__username']

# ==================== REVIEW ADMIN ====================

@admin.register(QuestionReview)
class QuestionReviewAdmin(admin.ModelAdmin):
    """All review data for a question in one place"""
    list_display = ['question_link', 'success_rate', 'average_time_taken']
    search_fields = ['question__question_en']
    
    fieldsets = (
        ('Question', {
            'fields': ('question',)
        }),
        ('Explanations', {
            'fields': ('detailed_explanation', 'detailed_explanation_hi'),
            'description': 'Add detailed explanations here'
        }),
        ('Learning Resources', {
            'fields': ('key_concepts', 'common_mistakes', 'video_solution_url'),
            'description': 'Help students learn better'
        }),
        ('Statistics', {
            'fields': ('average_difficulty_rating', 'success_rate', 'average_time_taken'),
            'classes': ('wide',)
        }),
    )
    
    def question_link(self, obj):
        return f"Q{obj.question.id}: {obj.question.question_en[:50]}..."
    question_link.short_description = "Question"

@admin.register(AttemptReview)
class AttemptReviewAdmin(admin.ModelAdmin):
    """Complete review for a test attempt"""
    list_display = ['attempt', 'created_at']
    search_fields = ['attempt__user__username']
    
    fieldsets = (
        ('Attempt', {
            'fields': ('attempt',)
        }),
        ('Feedback', {
            'fields': ('overall_feedback', 'strengths', 'weaknesses', 'recommendations')
        }),
        ('Difficulty Analysis', {
            'fields': ('easy_correct', 'easy_total', 'medium_correct', 'medium_total', 'hard_correct', 'hard_total'),
            'classes': ('wide',)
        }),
        ('Time Analysis', {
            'fields': ('average_time_correct', 'average_time_incorrect'),
        }),
    )

@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question_preview', 'is_correct', 'found_difficult', 'time_spent']
    list_filter = ['is_correct', 'found_difficult']
    search_fields = ['attempt__user__username']
    
    def question_preview(self, obj):
        return obj.question.question_en[:40] + "..."
    question_preview.short_description = "Question"

@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'attempt', 'duration', 'is_completed', 'started_at']
    list_filter = ['is_completed']
    search_fields = ['user__username']

# Simple dashboard-like view for quick access
class ExamDashboard(admin.AdminSite):
    site_header = "Exam Portal Admin"
    site_title = "Exam Admin"
    index_title = "Welcome to Exam Portal Dashboard"

# Register everything simply
admin.site.site_header = "Exam Portal Administration"
admin.site.site_title = "Exam Portal Admin"
admin.site.index_title = "Dashboard"
