from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import (
    ExamCategory, SubCategory, SubjectMaster, MockTest, 
    SubjectSection, Question, Option, MockTestAttempt,
    UserAnswer, UserPerformance, SubjectPerformance,
    UserAchievement, UserActivity, UserTestAnalytics
)

# ===================== INLINE CLASSES =====================

class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    fields = ['name', 'slug', 'icon_preview', 'created_at']
    readonly_fields = ['slug', 'icon_preview', 'created_at']
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon Preview'

class SubjectSectionInline(admin.TabularInline):
    model = SubjectSection
    extra = 0
    fields = ['subject', 'name', 'question_count', 'total_marks', 'order']
    readonly_fields = ['question_count', 'total_marks']
    
    def question_count(self, obj):
        return obj.question_set.count()
    question_count.short_description = 'Questions'

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['question_number', 'question_en_preview', 'subject', 'difficulty', 'marks', 'has_options']
    readonly_fields = ['question_number', 'question_en_preview', 'has_options']
    ordering = ['question_number']
    
    def question_en_preview(self, obj):
        return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
    question_en_preview.short_description = 'Question'
    
    def has_options(self, obj):
        count = obj.options.count()
        return format_html('<span style="color: {};">{} options</span>', 
                          'green' if count >= 2 else 'red', count)
    has_options.short_description = 'Options'

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    fields = ['option_letter', 'text_en_preview', 'is_correct']
    
    def text_en_preview(self, obj):
        return obj.text_en[:30] + '...' if len(obj.text_en) > 30 else obj.text_en
    text_en_preview.short_description = 'Option Text'

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0
    fields = ['question', 'selected_option', 'is_correct', 'marks_obtained']
    readonly_fields = ['is_correct', 'marks_obtained']
    raw_id_fields = ['question', 'selected_option']

# ===================== MAIN ADMIN CLASSES =====================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subcategories_count', 'logo_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ['name']}
    readonly_fields = ['created_at', 'updated_at', 'logo_preview']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Media', {
            'fields': ('logo', 'logo_preview'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [SubCategoryInline]
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100" height="auto" style="max-height: 50px;" />', obj.logo.url)
        return "No logo"
    logo_preview.short_description = 'Logo Preview'
    
    def subcategories_count(self, obj):
        count = obj.subcategories.count()
        url = reverse('admin:app_subcategory_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} Subcategories</a>', url, count)
    subcategories_count.short_description = 'Subcategories'

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'mocktests_count', 'icon_preview', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'category__name', 'description']
    prepopulated_fields = {'slug': ['name']}
    raw_id_fields = ['category']
    readonly_fields = ['created_at', 'updated_at', 'icon_preview', 'mocktests_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Media', {
            'fields': ('icon', 'icon_preview')
        }),
        ('Statistics', {
            'fields': ('mocktests_count',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon Preview'
    
    def mocktests_count(self, obj):
        count = obj.mock_tests.count()
        url = reverse('admin:app_mocktest_changelist') + f'?subcategory__id__exact={obj.id}'
        return format_html('<a href="{}">{} Tests</a>', url, count)
    mocktests_count.short_description = 'Mock Tests'

@admin.register(SubjectMaster)
class SubjectMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'questions_count', 'users_attempted', 'icon_preview']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'icon_preview', 'questions_count', 'users_attempted']
    fieldsets = (
        ('Subject Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Media', {
            'fields': ('icon', 'icon_preview')
        }),
        ('Statistics', {
            'fields': ('questions_count', 'users_attempted'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="40" height="40" style="border-radius: 5px;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon'
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Total Questions'
    
    def users_attempted(self, obj):
        return SubjectPerformance.objects.filter(subject=obj).count()
    users_attempted.short_description = 'Users Attempted'

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subcategory', 'test_type', 'duration', 'total_questions', 
                   'total_marks', 'attempts_count', 'is_active', 'created_at']
    list_filter = ['test_type', 'is_active', 'subcategory__category', 'created_at']
    search_fields = ['title', 'description', 'subcategory__name']
    raw_id_fields = ['subcategory']
    readonly_fields = ['created_at', 'updated_at', 'total_questions', 'total_marks', 
                      'attempts_count', 'subject_breakdown']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subcategory', 'test_type', 'description')
        }),
        ('Test Settings', {
            'fields': ('duration', 'passing_marks', 'instructions', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_questions', 'total_marks', 'attempts_count', 'subject_breakdown'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['activate_tests', 'deactivate_tests']
    inlines = [SubjectSectionInline, QuestionInline]
    
    def attempts_count(self, obj):
        count = obj.attempts.count()
        url = reverse('admin:app_mocktestattempt_changelist') + f'?mock_test__id__exact={obj.id}'
        return format_html('<a href="{}">{} Attempts</a>', url, count)
    attempts_count.short_description = 'Total Attempts'
    
    def subject_breakdown(self, obj):
        breakdown = obj.get_subject_breakdown()
        if not breakdown:
            return "No questions added yet"
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align:left; padding:5px; border-bottom:1px solid #ddd;">Subject</th>'
        html += '<th style="text-align:center; padding:5px; border-bottom:1px solid #ddd;">Questions</th>'
        html += '<th style="text-align:center; padding:5px; border-bottom:1px solid #ddd;">Marks</th></tr>'
        
        for subject, data in breakdown.items():
            html += f'<tr><td style="padding:5px; border-bottom:1px solid #eee;">{subject}</td>'
            html += f'<td style="text-align:center; padding:5px; border-bottom:1px solid #eee;">{data["count"]}</td>'
            html += f'<td style="text-align:center; padding:5px; border-bottom:1px solid #eee;">{data["marks"]}</td></tr>'
        
        html += '</table>'
        return format_html(html)
    subject_breakdown.short_description = 'Subject-wise Breakdown'
    
    def activate_tests(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} tests activated successfully.")
    activate_tests.short_description = "Activate selected tests"
    
    def deactivate_tests(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} tests deactivated successfully.")
    deactivate_tests.short_description = "Deactivate selected tests"

@admin.register(SubjectSection)
class SubjectSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'subject', 'question_count', 'total_marks', 'order']
    list_filter = ['mock_test__subcategory__category', 'subject']
    search_fields = ['name', 'mock_test__title', 'subject__name']
    raw_id_fields = ['mock_test', 'subject']
    readonly_fields = ['question_count', 'total_marks']
    inlines = [QuestionInline]
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_preview', 'mock_test', 'subject', 'difficulty', 
                   'marks', 'options_count', 'created_at']
    list_filter = ['difficulty', 'subject', 'mock_test__subcategory__category', 'created_at']
    search_fields = ['question_en', 'question_hi', 'explanation']
    raw_id_fields = ['mock_test', 'subject', 'section']
    readonly_fields = ['created_at', 'updated_at', 'options_count', 'question_number']
    fieldsets = (
        ('Question Assignment', {
            'fields': ('mock_test', 'subject', 'section', 'question_number')
        }),
        ('Question Content (English)', {
            'fields': ('question_en', 'explanation')
        }),
        ('Question Content (Hindi)', {
            'fields': ('question_hi', 'explanation_hi'),
            'classes': ('wide',)
        }),
        ('Question Settings', {
            'fields': ('difficulty', 'marks', 'negative_marks')
        }),
        ('Statistics', {
            'fields': ('options_count',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [OptionInline]
    actions = ['set_easy', 'set_medium', 'set_hard']
    
    def question_preview(self, obj):
        return obj.question_en[:75] + '...' if len(obj.question_en) > 75 else obj.question_en
    question_preview.short_description = 'Question'
    
    def options_count(self, obj):
        count = obj.options.count()
        color = 'green' if count >= 4 else 'orange' if count >= 2 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, count)
    options_count.short_description = 'Options'
    
    def set_easy(self, request, queryset):
        queryset.update(difficulty='easy')
        self.message_user(request, f"{queryset.count()} questions set to Easy.")
    set_easy.short_description = "Set difficulty to Easy"
    
    def set_medium(self, request, queryset):
        queryset.update(difficulty='medium')
        self.message_user(request, f"{queryset.count()} questions set to Medium.")
    set_medium.short_description = "Set difficulty to Medium"
    
    def set_hard(self, request, queryset):
        queryset.update(difficulty='hard')
        self.message_user(request, f"{queryset.count()} questions set to Hard.")
    set_hard.short_description = "Set difficulty to Hard"

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'option_preview', 'question_link', 'option_letter', 'is_correct']
    list_filter = ['is_correct', 'question__difficulty']
    search_fields = ['text_en', 'text_hi', 'question__question_en']
    raw_id_fields = ['question']
    list_editable = ['is_correct']
    
    def option_preview(self, obj):
        return obj.text_en[:50] + '...' if len(obj.text_en) > 50 else obj.text_en
    option_preview.short_description = 'Option'
    
    def question_link(self, obj):
        url = reverse('admin:app_question_change', args=[obj.question.id])
        return format_html('<a href="{}">{}</a>', url, obj.question.question_en[:30] + '...')
    question_link.short_description = 'Question'

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'mock_test_link', 'score', 'percentage', 
                   'correct_answers', 'wrong_answers', 'is_completed', 'submitted_at']
    list_filter = ['is_completed', 'mock_test__subcategory__category', 'started_at']
    search_fields = ['user__username', 'user__email', 'mock_test__title']
    raw_id_fields = ['user', 'mock_test']
    readonly_fields = ['started_at', 'submitted_at', 'percentage', 'time_taken_display']
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'mock_test')
        }),
        ('Scores', {
            'fields': ('score', 'total_marks', 'percentage', 'subject_performance')
        }),
        ('Statistics', {
            'fields': ('correct_answers', 'wrong_answers', 'skipped_answers')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'time_taken_display', 'is_completed')
        }),
    )
    inlines = [UserAnswerInline]
    actions = ['mark_completed', 'recalculate_scores']
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def mock_test_link(self, obj):
        url = reverse('admin:app_mocktest_change', args=[obj.mock_test.id])
        return format_html('<a href="{}">{}</a>', url, obj.mock_test.title)
    mock_test_link.short_description = 'Mock Test'
    
    def time_taken_display(self, obj):
        return obj.time_taken or 'In Progress'
    time_taken_display.short_description = 'Time Taken'
    
    def mark_completed(self, request, queryset):
        for attempt in queryset:
            if not attempt.is_completed:
                attempt.is_completed = True
                attempt.submitted_at = timezone.now()
                attempt.save()
        self.message_user(request, f"{queryset.count()} attempts marked as completed.")
    mark_completed.short_description = "Mark as completed"
    
    def recalculate_scores(self, request, queryset):
        for attempt in queryset:
            answers = UserAnswer.objects.filter(attempt=attempt)
            attempt.correct_answers = answers.filter(is_correct=True).count()
            attempt.wrong_answers = answers.filter(is_correct=False, selected_option__isnull=False).count()
            attempt.skipped_answers = answers.filter(selected_option__isnull=True).count()
            attempt.score = sum(a.marks_obtained for a in answers)
            attempt.save()
        self.message_user(request, f"Scores recalculated for {queryset.count()} attempts.")
    recalculate_scores.short_description = "Recalculate scores"

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'attempt_link', 'question_preview', 'selected_option_preview', 
                   'is_correct', 'marks_obtained']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['attempt__user__username', 'question__question_en']
    raw_id_fields = ['attempt', 'question', 'selected_option']
    readonly_fields = ['created_at', 'is_correct', 'marks_obtained']
    
    def attempt_link(self, obj):
        url = reverse('admin:app_mocktestattempt_change', args=[obj.attempt.id])
        return format_html('<a href="{}">Attempt #{}</a>', url, obj.attempt.id)
    attempt_link.short_description = 'Attempt'
    
    def question_preview(self, obj):
        return obj.question.question_en[:50] + '...'
    question_preview.short_description = 'Question'
    
    def selected_option_preview(self, obj):
        if obj.selected_option:
            return obj.selected_option.text_en[:30] + '...'
        return 'Skipped'
    selected_option_preview.short_description = 'Selected Option'

@admin.register(UserPerformance)
class UserPerformanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_tests_attempted', 'total_tests_passed', 
                   'average_score', 'highest_score', 'pass_percentage', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']
    readonly_fields = ['last_updated', 'pass_percentage']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Test Statistics', {
            'fields': ('total_tests_attempted', 'total_tests_passed', 'pass_percentage')
        }),
        ('Question Statistics', {
            'fields': ('total_questions_attempted', 'total_correct_answers', 
                      'total_wrong_answers', 'total_skipped_answers')
        }),
        ('Score Statistics', {
            'fields': ('average_score', 'highest_score')
        }),
        ('Time Statistics', {
            'fields': ('total_time_spent',)
        }),
        ('Last Updated', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    actions = ['refresh_stats']
    
    def pass_percentage(self, obj):
        if obj.total_tests_attempted > 0:
            percentage = (obj.total_tests_passed / obj.total_tests_attempted) * 100
            return f"{percentage:.1f}%"
        return "0%"
    pass_percentage.short_description = 'Pass Rate'
    
    def refresh_stats(self, request, queryset):
        for perf in queryset:
            perf.update_stats()
        self.message_user(request, f"Stats refreshed for {queryset.count()} users.")
    refresh_stats.short_description = "Refresh statistics"

@admin.register(SubjectPerformance)
class SubjectPerformanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'total_questions_attempted', 
                   'correct_answers', 'accuracy_display', 'last_attempted']
    list_filter = ['subject', 'last_attempted']
    search_fields = ['user__username', 'subject__name']
    raw_id_fields = ['user', 'subject']
    readonly_fields = ['accuracy_display', 'last_attempted']
    
    def accuracy_display(self, obj):
        color = 'green' if obj.accuracy >= 70 else 'orange' if obj.accuracy >= 40 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', 
                          color, obj.accuracy)
    accuracy_display.short_description = 'Accuracy'

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'achievement_type', 'earned_at']
    list_filter = ['achievement_type', 'earned_at']
    search_fields = ['user__username', 'title', 'description']
    raw_id_fields = ['user']
    readonly_fields = ['earned_at']
    date_hierarchy = 'earned_at'

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'description', 'timestamp']
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['user__username', 'description']
    raw_id_fields = ['user', 'mock_test']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

@admin.register(UserTestAnalytics)
class UserTestAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'rank', 'percentile', 'time_taken_seconds']
    list_filter = ['rank']
    search_fields = ['attempt__user__username', 'attempt__mock_test__title']
    raw_id_fields = ['attempt']
    readonly_fields = ['rank', 'percentile']
    fieldsets = (
        ('Attempt', {
            'fields': ('attempt',)
        }),
        ('Performance Metrics', {
            'fields': ('rank', 'percentile', 'time_taken_seconds')
        }),
        ('Detailed Analytics', {
            'fields': ('question_wise_time', 'subject_wise_accuracy', 'difficulty_wise_performance'),
            'classes': ('wide',)
        }),
    )

# ===================== CUSTOM ADMIN SITE CONFIGURATION =====================

admin.site.site_header = 'Exam Portal Administration'
admin.site.site_title = 'Exam Portal Admin'
admin.site.index_title = 'Dashboard'
