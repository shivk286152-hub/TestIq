from django.contrib import admin
from .models import *

# =========================
# OPTION INLINE (Inside Question)
# =========================
class OptionInline(admin.TabularInline):
    model = Option
    extra = 4   # Show 4 empty options by default
    min_num = 2
    max_num = 6


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
    list_display = ('id', 'mock_test', 'subject', 'short_question')
    list_filter = ('mock_test', 'subject')
    search_fields = ('question_en', 'question_hi')
    inlines = [OptionInline, QuestionReviewInline]

    def short_question(self, obj):
        return obj.question_en[:50]
    short_question.short_description = "Question"


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
    list_display = ('title', 'subcategory', 'duration', 'is_active', 'created_at')
    list_filter = ('subcategory', 'is_active')
    search_fields = ('title',)
    inlines = [SubjectInline]


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
