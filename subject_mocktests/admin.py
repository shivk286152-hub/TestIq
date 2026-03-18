from django.contrib import admin
from .models import Subject, Topic, MockTest, Question, Option, MockTestAttempt, UserAnswer

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    max_num = 4
    fields = ['text_en', 'text_hi', 'is_correct', 'order']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'test_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
    def test_count(self, obj):
        return obj.mock_tests.count()
    test_count.short_description = 'Tests'

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'test_count']
    list_filter = ['subject']
    search_fields = ['name', 'subject__name']
    
    def test_count(self, obj):
        return obj.mock_tests.count()
    test_count.short_description = 'Tests'

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'topic', 'difficulty', 'duration', 'is_active']
    list_filter = ['subject', 'topic', 'difficulty', 'is_active']
    search_fields = ['title', 'subject__name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'subject', 'topic', 'description')
        }),
        ('Settings', {
            'fields': ('difficulty', 'duration', 'is_active', 'is_free')
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value'),
        }),
        ('Instructions', {
            'fields': ('instructions',)
        }),
    )
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['total_questions', 'total_marks']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_question', 'mock_test', 'difficulty', 'marks', 'order']
    list_filter = ['mock_test', 'difficulty']
    search_fields = ['question_en']
    list_editable = ['marks', 'order', 'difficulty']
    inlines = [OptionInline]
    
    fieldsets = (
        ('Question', {
            'fields': ('mock_test', 'order', 'difficulty', 'topic')
        }),
        ('Content (English)', {
            'fields': ('question_en', 'explanation_en')
        }),
        ('Content (Hindi)', {
            'fields': ('question_hi', 'explanation_hi'),
            'classes': ('collapse',)
        }),
        ('Marks', {
            'fields': ('marks', 'negative_marks_override'),
            'description': 'Leave negative_marks_override blank to use difficulty-based defaults (Easy:0.25, Medium:0.33, Hard:0.50)'
        }),
    )
    
    def short_question(self, obj):
        return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
    short_question.short_description = 'Question'

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct']
    list_editable = ['is_correct', 'order']
    search_fields = ['text_en', 'question__question_en']
    
    def short_text(self, obj):
        return obj.text_en[:30] + '...' if len(obj.text_en) > 30 else obj.text_en
    short_text.short_description = 'Option'

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'mock_test', 'score', 'percentage', 'correct_answers', 'is_completed']
    list_filter = ['is_completed', 'mock_test']
    search_fields = ['user__username', 'mock_test__title']
    readonly_fields = ['raw_score', 'score_with_negative', 'total_marks', 'correct_answers', 
                       'wrong_answers', 'skipped_answers', 'negative_marks_applied', 'started_at', 'submitted_at']
    
    fieldsets = (
        ('User & Test', {
            'fields': ('user', 'mock_test', 'language')
        }),
        ('Scores', {
            'fields': ('raw_score', 'score_with_negative', 'total_marks', 'negative_marks_applied')
        }),
        ('Performance', {
            'fields': ('correct_answers', 'wrong_answers', 'skipped_answers')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'is_completed')
        }),
    )
    
    def percentage(self, obj):
        return f"{obj.percentage_with_negative}%"
    percentage.short_description = 'Percentage'

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'question_preview', 'is_correct', 'marks']
    list_filter = ['is_correct']
    search_fields = ['attempt__user__username', 'question__question_en']
    
    def user(self, obj):
        return obj.attempt.user.username
    user.short_description = 'User'
    
    def question_preview(self, obj):
        return obj.question.question_en[:30] + '...'
    question_preview.short_description = 'Question'
    
    def marks(self, obj):
        if not obj.selected_option:
            return "0 (Skipped)"
        if obj.is_correct:
            return f"+{obj.question.marks}"
        else:
            return f"-{obj.question.get_effective_negative_marks()}"
    marks.short_description = 'Marks'

# Admin site header
admin.site.site_header = 'Subject Mock Tests Admin'
admin.site.site_title = 'Subject Mock Tests Admin'
admin.site.index_title = 'Subject Mock Tests Management'