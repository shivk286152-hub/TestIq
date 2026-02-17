from django.contrib import admin
from .models import (
    ExamCategory,
    SubCategory,
    MockTest,
    Subject,
    Question,
    Option,
    MockTestAttempt
)

# ===============================
# Exam Category
# ===============================
@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


# ===============================
# Sub Category
# ===============================
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


# ===============================
# Mock Test
# ===============================
# @admin.register(MockTest)
# class MockTestAdmin(admin.ModelAdmin):
#     list_display = ("title", "subcategory", "total_questions", "duration","time_limit", "is_active")
#     list_filter = ("subcategory", "is_active")
#     ordering = ("-created_at",)
#     search_fields = ("title",)


# ===============================
# Subject
# ===============================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "mock_test", "start_question_no", "end_question_no")
    list_filter = ("mock_test",)
    search_fields = ("name",)


# ===============================
# Question + Option Inline
# ===============================
class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    min_num = 4
    max_num = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_question", "mock_test", "subject")
    list_filter = ("mock_test", "subject")
    search_fields = ("question_text",)
    inlines = [OptionInline]

    def short_question(self, obj):
         return (obj.question_en or "")[:50]
    short_question.short_description = "Question"

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ("title", "duration", "created_at")
    list_filter = ("duration",)
    search_fields = ("title",)
    ordering = ("-created_at",)

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "mock_test",
        "score",
        "total_marks",
        "percentage",
        "time_taken",
        "is_completed",
        "started_at",
    )
    list_filter = ("is_completed", "mock_test", "started_at")
    search_fields = ("user__username", "mock_test__title")
    readonly_fields = ("started_at", "submitted_at")
    ordering = ("-started_at",)
