from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Max, Count, Avg, Sum
from django.urls import reverse
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from .models import (
    ExamCategory, SubCategory, MockTest, Subject, 
    Question, Option, MockTestAttempt, UserAnswer, Testimonial
)

# ============================================
# CUSTOM FILTERS
# ============================================

class HasNegativeMarkingFilter(SimpleListFilter):
    """Custom filter to filter tests by negative marking presence"""
    title = 'has negative marking'
    parameter_name = 'has_negative'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(negative_marking_type='no_negative')
        if self.value() == 'no':
            return queryset.filter(negative_marking_type='no_negative')


class TestCompletionFilter(SimpleListFilter):
    """Filter attempts by completion status"""
    title = 'completion status'
    parameter_name = 'completion'

    def lookups(self, request, model_admin):
        return (
            ('completed', 'Completed'),
            ('incomplete', 'Incomplete'),
            ('auto_submitted', 'Auto-submitted'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'completed':
            return queryset.filter(is_completed=True, submitted_at__isnull=False)
        if self.value() == 'incomplete':
            return queryset.filter(is_completed=False, submitted_at__isnull=True)
        if self.value() == 'auto_submitted':
            return queryset.filter(
                is_completed=True,
                submitted_at__isnull=False,
                submitted_at__gt=models.F('started_at') + timedelta(minutes=models.F('mock_test__duration'))
            )


# ============================================
# INLINE MODELS
# ============================================

class OptionInline(admin.TabularInline):
    """Inline admin for options within question"""
    model = Option
    extra = 4
    max_num = 4
    min_num = 2
    fields = ['text_en', 'text_hi', 'is_correct', 'order', 'option_preview']
    readonly_fields = ['option_preview']
    ordering = ['order']
    classes = ['collapse']
    
    def option_preview(self, obj):
        if obj.pk:  # Only for existing objects
            text = obj.text_en[:30] + '...' if len(obj.text_en) > 30 else obj.text_en
            if obj.is_correct:
                return format_html('<span style="color: green; font-weight: bold;">✓ {}</span>', text)
            return format_html('<span style="color: #666;">✗ {}</span>', text)
        return "New option"
    option_preview.short_description = 'Preview'


class QuestionInline(admin.TabularInline):
    """Inline admin for questions within subject"""
    model = Question
    extra = 1
    fields = ['question_preview', 'difficulty', 'marks', 'order']
    readonly_fields = ['question_preview']
    ordering = ['order']
    classes = ['collapse']
    
    def question_preview(self, obj):
        if obj.pk:
            return obj.question_en[:50] + '...' if len(obj.question_en) > 50 else obj.question_en
        return "New question"
    question_preview.short_description = 'Question'


# ============================================
# EXAM CATEGORY ADMIN
# ============================================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description_short', 'logo_preview', 'subcategories_count', 'mocktests_count']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    readonly_fields = ['logo_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Logo', {
            'fields': ('logo', 'logo_preview'),
            'classes': ('wide',)
        }),
    )

    def description_short(self, obj):
        if obj.description:
            return obj.description[:75] + '...' if len(obj.description) > 75 else obj.description
        return '-'
    description_short.short_description = 'Description'

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.logo.url)
        return "No logo"
    logo_preview.short_description = 'Logo Preview'

    def subcategories_count(self, obj):
        count = obj.subcategories.count()
        url = reverse('admin:exams_subcategory_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} Subcategories</a>', url, count)
    subcategories_count.short_description = 'Subcategories'

    def mocktests_count(self, obj):
        count = MockTest.objects.filter(subcategory__category=obj).count()
        return count
    mocktests_count.short_description = 'Total Tests'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'icon_preview', 'description_short', 'mocktests_count']
    list_filter = ['category']
    search_fields = ['name', 'category__name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    readonly_fields = ['icon_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'description', 'slug')
        }),
        ('Icon', {
            'fields': ('icon', 'icon_preview'),
            'classes': ('wide',)
        }),
    )

    def description_short(self, obj):
        if obj.description:
            return obj.description[:75] + '...' if len(obj.description) > 75 else obj.description
        return '-'
    description_short.short_description = 'Description'

    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" style="max-height: 40px; max-width: 40px;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon Preview'

    def mocktests_count(self, obj):
        count = obj.mock_tests.count()
        url = reverse('admin:exams_mocktest_changelist') + f'?subcategory__id__exact={obj.id}'
        return format_html('<a href="{}">{} Tests</a>', url, count)
    mocktests_count.short_description = 'Tests'


# ============================================
# MOCK TEST ADMIN
# ============================================

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'subcategory', 'difficulty_colored', 'duration', 
        'total_marks', 'negative_marking_display', 'question_count',
        'attempts_count', 'is_active_colored', 'created_at'
    ]
    list_filter = [
        'is_active', 'difficulty', 'negative_marking_type', 
        'subcategory__category', 'subcategory', HasNegativeMarkingFilter
    ]
    search_fields = ['title', 'subcategory__name', 'subcategory__category__name']
    list_editable = []
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['activate_tests', 'deactivate_tests', 'recalculate_total_marks']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subcategory', 'difficulty', 'is_active')
        }),
        ('Test Settings', {
            'fields': ('duration', 'time_limit'),
            'description': 'Duration: Total time for test in minutes. Time limit: Per attempt time limit.'
        }),
        ('Negative Marking', {
            'fields': ('negative_marking_type', 'negative_marking_value'),
            'description': 'Configure negative marking rules for this test',
            'classes': ('wide',)
        }),
        ('System Fields', {
            'fields': ('total_marks',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_marks', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'subcategory', 'subcategory__category'
        ).prefetch_related('questions', 'attempts')

    def difficulty_colored(self, obj):
        colors = {
            'Beginner': 'green',
            'Intermediate': 'orange',
            'Advanced': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.difficulty, 'black'),
            obj.difficulty
        )
    difficulty_colored.short_description = 'Difficulty'
    difficulty_colored.admin_order_field = 'difficulty'

    def is_active_colored(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Inactive</span>')
    is_active_colored.short_description = 'Status'
    is_active_colored.admin_order_field = 'is_active'

    def negative_marking_display(self, obj):
        if obj.negative_marking_type == 'no_negative':
            return format_html('<span style="color: gray;">No Negative</span>')
        elif obj.negative_marking_type == 'fixed_per_question':
            return format_html('<span style="color: red;">-{} marks</span>', obj.negative_marking_value)
        else:
            return format_html('<span style="color: orange;">-{}%</span>', obj.negative_marking_value)
    negative_marking_display.short_description = 'Negative Marking'
    negative_marking_display.admin_order_field = 'negative_marking_type'

    def question_count(self, obj):
        count = obj.question_count
        url = reverse('admin:exams_question_changelist') + f'?mock_test__id__exact={obj.id}'
        return format_html('<a href="{}">{} Questions</a>', url, count)
    question_count.short_description = 'Questions'

    def attempts_count(self, obj):
        count = obj.attempts.count()
        url = reverse('admin:exams_mocktestattempt_changelist') + f'?mock_test__id__exact={obj.id}'
        return format_html('<a href="{}">{} Attempts</a>', url, count)
    attempts_count.short_description = 'Attempts'

    def activate_tests(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} test(s) activated successfully.")
    activate_tests.short_description = "Activate selected tests"

    def deactivate_tests(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} test(s) deactivated successfully.")
    deactivate_tests.short_description = "Deactivate selected tests"

    def recalculate_total_marks(self, request, queryset):
        for test in queryset:
            test.update_total_marks()
        self.message_user(request, f"Total marks recalculated for {queryset.count()} test(s).")
    recalculate_total_marks.short_description = "Recalculate total marks"


# ============================================
# SUBJECT ADMIN
# ============================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'mock_test', 'start_question_no', 'end_question_no', 
                    'question_count', 'total_marks']
    list_filter = ['mock_test', 'mock_test__subcategory__category']
    search_fields = ['name', 'mock_test__title']
    list_per_page = 20
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('mock_test', 'name')
        }),
        ('Question Range', {
            'fields': ('start_question_no', 'end_question_no'),
            'description': 'Define the range of question numbers for this subject'
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mock_test'
        ).prefetch_related('questions')

    def question_count(self, obj):
        count = obj.questions.count()
        return count
    question_count.short_description = 'Questions'
    question_count.admin_order_field = 'questions__count'

    def total_marks(self, obj):
        total = obj.questions.aggregate(total=Sum('marks'))['total'] or 0
        return total
    total_marks.short_description = 'Total Marks'

    def clean(self):
        """Validate question number range"""
        if self.start_question_no >= self.end_question_no:
            raise ValidationError('End question number must be greater than start question number')


# ============================================
# QUESTION ADMIN
# ============================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'question_preview', 'mock_test', 'subject', 
        'difficulty_colored', 'topic', 'marks', 'negative_marks_display',
        'options_count', 'order', 'has_correct_options'
    ]
    list_filter = [
        'mock_test', 'subject', 'difficulty', 'mock_test__subcategory__category'
    ]
    search_fields = ['question_en', 'question_hi', 'topic', 'explanation']
    list_editable = ['marks', 'order', 'difficulty', 'topic']
    list_per_page = 20
    inlines = [OptionInline]
    actions = [
        'set_difficulty_easy', 'set_difficulty_medium', 'set_difficulty_hard',
        'bulk_update_marks', 'bulk_update_negative_marks'
    ]
    save_as = True
    save_as_continue = True
    
    fieldsets = (
        ('Question Information', {
            'fields': ('mock_test', 'subject', 'order')
        }),
        ('Question Content (English)', {
            'fields': ('question_en',),
            'classes': ('wide',)
        }),
        ('Question Content (Hindi)', {
            'fields': ('question_hi',),
            'classes': ('wide', 'collapse')
        }),
        ('Question Classification', {
            'fields': ('difficulty', 'topic'),
            'classes': ('wide',),
            'description': 'Set difficulty level (Easy/Medium/Hard) and topic (e.g., Algebra, Grammar)'
        }),
        ('Explanation', {
            'fields': ('explanation', 'explanation_hi'),
            'classes': ('wide', 'collapse')
        }),
        ('Marking Scheme', {
            'fields': ('marks', 'negative_marks'),
            'description': 'Marks: Positive marks for correct answer. Negative Marks: Leave blank to use test default.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mock_test', 'subject'
        ).prefetch_related('options')

    def question_preview(self, obj):
        text = obj.question_en[:75] + '...' if len(obj.question_en) > 75 else obj.question_en
        return format_html('<span title="{}">{}</span>', obj.question_en, text)
    question_preview.short_description = 'Question'
    question_preview.admin_order_field = 'question_en'

    def difficulty_colored(self, obj):
        colors = {
            'Easy': 'green',
            'Medium': 'orange',
            'Hard': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.difficulty, 'black'),
            obj.difficulty
        )
    difficulty_colored.short_description = 'Difficulty'
    difficulty_colored.admin_order_field = 'difficulty'

    def negative_marks_display(self, obj):
        if obj.has_custom_negative_marks():
            return format_html(
                '<span style="color: red; font-weight: bold;">-{} (custom)</span>',
                obj.negative_marks
            )
        elif obj.mock_test.has_negative_marking:
            return format_html(
                '<span style="color: orange;">Uses test default</span>'
            )
        return format_html('<span style="color: gray;">No negative</span>')
    negative_marks_display.short_description = 'Negative Marks'
    negative_marks_display.admin_order_field = 'negative_marks'

    def options_count(self, obj):
        count = obj.options.count()
        if count == 4:
            return format_html('<span style="color: green;">{}/4</span>', count)
        elif count > 0:
            return format_html('<span style="color: orange;">{}/4</span>', count)
        return format_html('<span style="color: red;">{}/4</span>', count)
    options_count.short_description = 'Options'

    def has_correct_options(self, obj):
        if obj.options.filter(is_correct=True).exists():
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_correct_options.short_description = 'Has Correct'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Only for new objects
            mock_test_id = request.GET.get('mock_test') or request.POST.get('mock_test')
            if mock_test_id:
                # Auto-set order
                max_order = Question.objects.filter(mock_test_id=mock_test_id).aggregate(Max('order'))['order__max']
                form.base_fields['order'].initial = (max_order or 0) + 1
                
                # Auto-set subjects from mock_test
                form.base_fields['subject'].queryset = Subject.objects.filter(mock_test_id=mock_test_id)
            
            form.base_fields['difficulty'].initial = 'Medium'
        
        # Ensure required fields
        form.base_fields['question_en'].required = True
        form.base_fields['question_hi'].required = False
        form.base_fields['topic'].required = False
        
        return form

    def save_model(self, request, obj, form, change):
        if not obj.order and obj.mock_test:
            max_order = Question.objects.filter(mock_test=obj.mock_test).aggregate(Max('order'))['order__max']
            obj.order = (max_order or 0) + 1
        if not obj.difficulty:
            obj.difficulty = 'Medium'
        super().save_model(request, obj, form, change)
        
        # Update mock test total marks
        if obj.mock_test:
            obj.mock_test.update_total_marks()

    def delete_model(self, request, obj):
        mock_test = obj.mock_test
        super().delete_model(request, obj)
        if mock_test:
            mock_test.update_total_marks()

    def delete_queryset(self, request, queryset):
        mock_tests = set(queryset.values_list('mock_test', flat=True))
        super().delete_queryset(request, queryset)
        for mock_test_id in mock_tests:
            try:
                MockTest.objects.get(id=mock_test_id).update_total_marks()
            except MockTest.DoesNotExist:
                pass

    # Bulk Actions
    def set_difficulty_easy(self, request, queryset):
        updated = queryset.update(difficulty='Easy')
        self.message_user(request, f"{updated} questions set to Easy difficulty.")
    set_difficulty_easy.short_description = "Set difficulty to Easy"

    def set_difficulty_medium(self, request, queryset):
        updated = queryset.update(difficulty='Medium')
        self.message_user(request, f"{updated} questions set to Medium difficulty.")
    set_difficulty_medium.short_description = "Set difficulty to Medium"

    def set_difficulty_hard(self, request, queryset):
        updated = queryset.update(difficulty='Hard')
        self.message_user(request, f"{updated} questions set to Hard difficulty.")
    set_difficulty_hard.short_description = "Set difficulty to Hard"

    def bulk_update_marks(self, request, queryset):
        """Custom action to bulk update marks"""
        if 'apply' in request.POST:
            marks_value = float(request.POST.get('marks_value', 0))
            updated = queryset.update(marks=marks_value)
            self.message_user(request, f"Updated {updated} questions with marks = {marks_value}")
            return HttpResponseRedirect(request.get_full_path())
        
        # Show intermediate form
        from django.shortcuts import render
        return render(request, 'admin/bulk_update_marks.html', {
            'questions': queryset,
            'action_name': 'bulk_update_marks',
        })
    bulk_update_marks.short_description = "Bulk update marks"

    def bulk_update_negative_marks(self, request, queryset):
        """Custom action to bulk update negative marks"""
        if 'apply' in request.POST:
            neg_value = request.POST.get('negative_marks_value')
            if neg_value:
                neg_value = float(neg_value)
                updated = queryset.update(negative_marks=neg_value)
                self.message_user(request, f"Updated {updated} questions with negative marks = {neg_value}")
            else:
                updated = queryset.update(negative_marks=None)
                self.message_user(request, f"Reset negative marks for {updated} questions to use test default")
            return HttpResponseRedirect(request.get_full_path())
        
        from django.shortcuts import render
        return render(request, 'admin/bulk_update_negative.html', {
            'questions': queryset,
            'action_name': 'bulk_update_negative_marks',
        })
    bulk_update_negative_marks.short_description = "Bulk update negative marks"


# ============================================
# OPTION ADMIN
# ============================================

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'option_preview', 'question_link', 'is_correct_colored', 'order']
    list_filter = ['is_correct', 'question__mock_test', 'question__subject']
    search_fields = ['text_en', 'text_hi', 'question__question_en']
    list_editable = ['is_correct', 'order']
    list_per_page = 30
    actions = ['mark_as_correct', 'mark_as_incorrect', 'reorder_options']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question')

    def option_preview(self, obj):
        text = obj.text_en[:50] + '...' if len(obj.text_en) > 50 else obj.text_en
        if obj.is_correct:
            return format_html('<span style="color: green; font-weight: bold;">✓ {}</span>', text)
        return format_html('<span style="color: #666;">✗ {}</span>', text)
    option_preview.short_description = 'Option Text'

    def question_link(self, obj):
        url = reverse('admin:exams_question_change', args=[obj.question.id])
        return format_html('<a href="{}">{}</a>', url, obj.question.question_en[:50] + '...')
    question_link.short_description = 'Question'

    def is_correct_colored(self, obj):
        if obj.is_correct:
            return format_html('<span style="color: green; font-weight: bold;">✓ Correct</span>')
        return format_html('<span style="color: gray;">✗ Incorrect</span>')
    is_correct_colored.short_description = 'Correct'
    is_correct_colored.admin_order_field = 'is_correct'

    def mark_as_correct(self, request, queryset):
        for option in queryset:
            # First, make sure only one correct option per question
            option.question.options.exclude(pk=option.pk).update(is_correct=False)
            option.is_correct = True
            option.save()
        self.message_user(request, f"{queryset.count()} options marked as correct (others in same question were unmarked).")
    mark_as_correct.short_description = "Mark as correct (and unmark others in same question)"

    def mark_as_incorrect(self, request, queryset):
        updated = queryset.update(is_correct=False)
        self.message_user(request, f"{updated} options marked as incorrect.")
    mark_as_incorrect.short_description = "Mark as incorrect"

    def reorder_options(self, request, queryset):
        """Reset order numbers for selected options"""
        for i, option in enumerate(queryset.order_by('order', 'id'), 1):
            option.order = i
            option.save(update_fields=['order'])
        self.message_user(request, f"Reordered {queryset.count()} options.")
    reorder_options.short_description = "Reset order numbers"


# ============================================
# MOCK TEST ATTEMPT ADMIN
# ============================================

@admin.register(MockTestAttempt)
class MockTestAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user_info', 'mock_test_link', 'score_display', 'percentage_display',
        'correct_wrong_ratio', 'time_info', 'completion_status', 'language'
    ]
    list_filter = [
        'is_completed', 'language', 'is_paid_user', 'is_archived',
        'mock_test', TestCompletionFilter, 'started_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'mock_test__title'
    ]
    readonly_fields = [
        'started_at', 'submitted_at', 'score', 'total_marks',
        'correct_answers', 'wrong_answers', 'skipped_answers',
        'percentage', 'time_taken', 'time_remaining'
    ]
    list_per_page = 20
    date_hierarchy = 'started_at'
    actions = ['recalculate_scores', 'archive_attempts', 'export_as_csv']
    
    fieldsets = (
        ('User & Test', {
            'fields': ('user', 'mock_test', 'language', 'is_paid_user')
        }),
        ('Performance Summary', {
            'fields': (
                ('score', 'total_marks', 'percentage'),
                ('correct_answers', 'wrong_answers', 'skipped_answers'),
            )
        }),
        ('Timing Information', {
            'fields': (
                ('started_at', 'submitted_at'),
                ('time_taken', 'time_remaining', 'is_completed')
            )
        }),
        ('Data Retention', {
            'fields': ('is_archived', 'has_detailed_data', 'permanently_deleted'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'mock_test'
        ).prefetch_related('answers')

    def user_info(self, obj):
        name = obj.user.get_full_name() or obj.user.username
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a><br/><small>{}</small>', url, name, obj.user.email)
    user_info.short_description = 'User'
    user_info.admin_order_field = 'user__username'

    def mock_test_link(self, obj):
        url = reverse('admin:exams_mocktest_change', args=[obj.mock_test.id])
        return format_html('<a href="{}">{}</a>', url, obj.mock_test.title)
    mock_test_link.short_description = 'Mock Test'
    mock_test_link.admin_order_field = 'mock_test__title'

    def score_display(self, obj):
        return f"{obj.score:.2f} / {obj.total_marks:.2f}"
    score_display.short_description = 'Score'
    score_display.admin_order_field = 'score'

    def percentage_display(self, obj):
        percentage = obj.percentage
        if percentage >= 70:
            color = 'green'
            icon = '🏆'
        elif percentage >= 40:
            color = 'orange'
            icon = '📊'
        else:
            color = 'red'
            icon = '📉'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.1f}%</span>',
            color, icon, percentage
        )
    percentage_display.short_description = 'Percentage'
    percentage_display.admin_order_field = 'score'

    def correct_wrong_ratio(self, obj):
        total = obj.correct_answers + obj.wrong_answers
        if total > 0:
            ratio = (obj.correct_answers / total) * 100
            return format_html(
                '{} / {}<br/><small>{:.1f}% correct</small>',
                obj.correct_answers, obj.wrong_answers, ratio
            )
        return "0 / 0"
    correct_wrong_ratio.short_description = 'C/W Ratio'

    def time_info(self, obj):
        if obj.submitted_at:
            return format_html(
                '<span title="{}">{}</span>',
                obj.submitted_at,
                obj.time_taken or 'N/A'
            )
        elif obj.is_completed:
            return "Completed"
        elif obj.time_remaining > 0:
            minutes = obj.time_remaining // 60
            seconds = obj.time_remaining % 60
            return format_html(
                '<span style="color: green;">{}:{:02d} left</span>',
                minutes, seconds
            )
        else:
            return format_html('<span style="color: red;">Time up!</span>')
    time_info.short_description = 'Time Info'

    def completion_status(self, obj):
        if obj.is_completed and obj.submitted_at:
            return format_html('<span style="color: green;">✓ Completed</span>')
        elif obj.is_completed:
            return format_html('<span style="color: orange;">Auto-submitted</span>')
        else:
            return format_html('<span style="color: gray;">⏳ In Progress</span>')
    completion_status.short_description = 'Status'
    completion_status.admin_order_field = 'is_completed'

    def recalculate_scores(self, request, queryset):
        count = 0
        for attempt in queryset:
            attempt.calculate_score()
            count += 1
        self.message_user(request, f"Recalculated scores for {count} attempts.")
    recalculate_scores.short_description = "Recalculate scores"

    def archive_attempts(self, request, queryset):
        count = 0
        for attempt in queryset.filter(is_archived=False):
            attempt.archive_details()
            count += 1
        self.message_user(request, f"Archived {count} attempts (deleted detailed answers).")
    archive_attempts.short_description = "Archive details (delete answers)"

    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attempts_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Email', 'Mock Test', 'Score', 'Total', 'Percentage',
            'Correct', 'Wrong', 'Skipped', 'Started', 'Submitted', 'Status'
        ])
        
        for attempt in queryset.select_related('user', 'mock_test'):
            writer.writerow([
                attempt.user.username,
                attempt.user.email,
                attempt.mock_test.title,
                attempt.score,
                attempt.total_marks,
                attempt.percentage,
                attempt.correct_answers,
                attempt.wrong_answers,
                attempt.skipped_answers,
                attempt.started_at,
                attempt.submitted_at,
                'Completed' if attempt.is_completed else 'In Progress'
            ])
        
        return response
    export_as_csv.short_description = "Export selected as CSV"


# ============================================
# USER ANSWER ADMIN
# ============================================

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_info', 'question_info', 'selected_option_info', 
                    'answer_status', 'marks_obtained_display', 'time_spent']
    list_filter = ['is_correct', 'attempt__mock_test', 'attempt__language']
    search_fields = [
        'attempt__user__username', 'attempt__user__email',
        'question__question_en', 'selected_option__text_en'
    ]
    readonly_fields = ['created_at', 'updated_at', 'marks_obtained']
    list_per_page = 30
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Attempt Info', {
            'fields': ('attempt', 'question')
        }),
        ('Answer Details', {
            'fields': ('selected_option', 'is_correct', 'time_taken', 'marks_obtained')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attempt', 'attempt__user', 'question', 'selected_option'
        )

    def user_info(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.attempt.user.id])
        return format_html(
            '<a href="{}">{}</a><br/><small>{}</small>',
            url, obj.attempt.user.username, obj.attempt.user.email
        )
    user_info.short_description = 'User'
    user_info.admin_order_field = 'attempt__user__username'

    def question_info(self, obj):
        return obj.question.question_en[:50] + '...' if obj.question.question_en else 'N/A'
    question_info.short_description = 'Question'
    question_info.admin_order_field = 'question__question_en'

    def selected_option_info(self, obj):
        if obj.selected_option:
            text = obj.selected_option.text_en[:30] + '...' if len(obj.selected_option.text_en) > 30 else obj.selected_option.text_en
            return text
        return "Not answered"
    selected_option_info.short_description = 'Selected Option'

    def answer_status(self, obj):
        if obj.is_correct:
            return format_html('<span style="color: green; font-weight: bold;">✓ Correct</span>')
        elif obj.selected_option:
            return format_html('<span style="color: red; font-weight: bold;">✗ Wrong</span>')
        else:
            return format_html('<span style="color: gray;">- Skipped</span>')
    answer_status.short_description = 'Status'
    answer_status.admin_order_field = 'is_correct'

    def marks_obtained_display(self, obj):
        marks = obj.marks_obtained
        if marks > 0:
            return format_html('<span style="color: green;">+{:.2f}</span>', marks)
        elif marks < 0:
            return format_html('<span style="color: red;">{:.2f}</span>', marks)
        else:
            return format_html('<span style="color: gray;">0.00</span>')
    marks_obtained_display.short_description = 'Marks'
    marks_obtained_display.admin_order_field = 'marks_obtained'

    def time_spent(self, obj):
        return obj.time_spent_formatted
    time_spent.short_description = 'Time Spent'


# ============================================
# TESTIMONIAL ADMIN
# ============================================

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'stars_display', 'achievement_short', 'text_preview',
        'is_active_colored', 'is_featured_colored', 'display_order', 'created_at'
    ]
    list_filter = ['is_active', 'is_featured', 'stars', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'text', 'achievement']
    list_editable = ['display_order']
    actions = ['approve_testimonials', 'feature_testimonials', 'unfeature_testimonials']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Testimonial Content', {
            'fields': ('text', 'stars', 'achievement')
        }),
        ('Admin Control', {
            'fields': ('is_active', 'is_featured', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def user_name(self, obj):
        name = obj.user_name()
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        initials = obj.user_initials()
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<span style="background-color: #f0f0f0; border-radius: 50%; width: 24px; height: 24px; '
            'display: inline-flex; align-items: center; justify-content: center; margin-right: 8px;">'
            '{}</span>'
            '<a href="{}">{}</a>'
            '</div>',
            initials, url, name
        )
    user_name.short_description = 'User'
    user_name.admin_order_field = 'user__username'

    def stars_display(self, obj):
        stars = '★' * obj.stars + '☆' * (5 - obj.stars)
        return format_html('<span style="color: gold; font-size: 16px;">{}</span>', stars)
    stars_display.short_description = 'Rating'
    stars_display.admin_order_field = 'stars'

    def achievement_short(self, obj):
        if obj.achievement:
            return obj.achievement[:30] + '...' if len(obj.achievement) > 30 else obj.achievement
        return '-'
    achievement_short.short_description = 'Achievement'

    def text_preview(self, obj):
        preview = obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return format_html('<span title="{}">{}</span>', obj.text, preview)
    text_preview.short_description = 'Testimonial'

    def is_active_colored(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_colored.short_description = 'Active'
    is_active_colored.admin_order_field = 'is_active'

    def is_featured_colored(self, obj):
        if obj.is_featured:
            return format_html('<span style="color: blue; font-weight: bold;">★ Featured</span>')
        return format_html('<span style="color: gray;">Not Featured</span>')
    is_featured_colored.short_description = 'Featured'
    is_featured_colored.admin_order_field = 'is_featured'

    def approve_testimonials(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} testimonials approved and will be displayed.")
    approve_testimonials.short_description = "Approve selected testimonials"

    def feature_testimonials(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} testimonials marked as featured.")
    feature_testimonials.short_description = "Feature selected testimonials"

    def unfeature_testimonials(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} testimonials unfeatured.")
    unfeature_testimonials.short_description = "Remove featured status"


# ============================================
# DASHBOARD & STATISTICS
# ============================================

class ExamStatistics:
    """Helper class for admin dashboard statistics"""
    
    @staticmethod
    def get_quick_stats():
        from django.db.models import Count, Sum, Avg
        
        total_tests = MockTest.objects.count()
        active_tests = MockTest.objects.filter(is_active=True).count()
        total_questions = Question.objects.count()
        total_attempts = MockTestAttempt.objects.count()
        
        avg_score = MockTestAttempt.objects.filter(
            is_completed=True
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        return {
            'total_tests': total_tests,
            'active_tests': active_tests,
            'total_questions': total_questions,
            'total_attempts': total_attempts,
            'avg_score': round(avg_score, 2)
        }
    
    @staticmethod
    def get_popular_tests(limit=5):
        return MockTest.objects.annotate(
            attempt_count=Count('attempts')
        ).order_by('-attempt_count')[:limit]
    
    @staticmethod
    def get_recent_attempts(limit=10):
        return MockTestAttempt.objects.select_related(
            'user', 'mock_test'
        ).order_by('-started_at')[:limit]


# ============================================
# ADMIN SITE CUSTOMIZATION
# ============================================

# Customize admin site header and titles
admin.site.site_header = 'Mock Test Administration Dashboard'
admin.site.site_title = 'Mock Test Admin'
admin.site.index_title = 'Welcome to Mock Test Management System'

# Add custom admin CSS
class Media:
    css = {
        'all': ('admin/css/custom_admin.css',)
    }

# Optional: Register custom admin views for dashboard
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def admin_dashboard(request):
    stats = ExamStatistics.get_quick_stats()
    popular_tests = ExamStatistics.get_popular_tests()
    recent_attempts = ExamStatistics.get_recent_attempts()
    
    context = {
        'stats': stats,
        'popular_tests': popular_tests,
        'recent_attempts': recent_attempts,
        'title': 'Dashboard',
    }
    return render(request, 'admin/dashboard.html', context)

# Add to admin URLs (in your urls.py)
from django.urls import path

def get_admin_urls(urls):
    def get_urls():
        my_urls = [
            path('dashboard/', admin_dashboard, name='dashboard'),
        ]
        return my_urls + urls
    return get_urls

admin_urls = get_admin_urls(admin.site.get_urls())
admin.site.get_urls = admin_urls
