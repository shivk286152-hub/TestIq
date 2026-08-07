from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import (
    Subject, Topic, Part, Question, 
    QuestionImage, QuestionTable, ComprehensiveContent,
    QuestionCategory
)

class QuestionImageInline(admin.TabularInline):
    model = QuestionImage
    extra = 1
    fields = ['image', 'caption', 'caption_hi', 'order']
    ordering = ['order']


class QuestionTableInline(admin.TabularInline):
    model = QuestionTable
    extra = 1
    fields = ['table_data', 'caption', 'caption_hi', 'order']
    ordering = ['order']


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color_preview', 'icon', 'is_active', 'order', 'question_count']
    list_filter = ['is_active']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    
    fieldsets = (
        ('Content', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'color', 'icon')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
    )
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 30px; background-color: {}; border-radius: 50%; border: 2px solid #ddd; display: inline-block;"></div>',
            obj.color
        )
    color_preview.short_description = "Color"
    
    def question_count(self, obj):
        count = obj.questions.filter(is_active=True).count()
        url = reverse('admin:QA_question_changelist') + f'?categories__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} questions</a>', url, count)
    question_count.short_description = "Questions"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'part', 'question_type', 'difficulty', 'categories_display', 'published_date', 'order', 'is_active', 'views']
    list_filter = ['difficulty', 'question_type', 'is_active', 'categories', 'published_date', 'is_featured', 'part__topic__subject']
    search_fields = ['question', 'question_hi', 'answer', 'answer_hi', 'tags']
    inlines = [QuestionImageInline, QuestionTableInline]
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['views', 'created_at', 'updated_at']
    filter_horizontal = ['categories']
    date_hierarchy = 'published_date'
    
    fieldsets = (
        ('English Content', {
            'fields': ('question', 'answer')
        }),
        ('Hindi Content', {
            'fields': ('question_hi', 'answer_hi'),
            'classes': ('collapse',)
        }),
        ('Categories & Type', {
            'fields': ('categories', 'question_type', 'difficulty'),
        }),
        ('Filtering & Meta', {
            'fields': ('published_date', 'is_featured', 'tags', 'is_active'),
        }),
        ('Metadata', {
            'fields': ('part', 'order', 'views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        preview = obj.question[:100] + "..." if len(obj.question) > 100 else obj.question
        return format_html('<span style="font-weight:500;">{}</span>', preview)
    question_preview.short_description = "Question"
    
    def categories_display(self, obj):
        categories = obj.categories.filter(is_active=True)
        if categories.exists():
            html_parts = []
            for cat in categories:
                html_parts.append(
                    f'<span style="display:inline-block; background-color: {cat.color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin: 2px; font-weight: 500;">{cat.name}</span>'
                )
            return mark_safe(''.join(html_parts))
        return mark_safe('<span style="color: #9ca3af;">-</span>')
    categories_display.short_description = "Categories"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categories')


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic', 'order', 'is_active', 'questions_count', 'views']
    list_filter = ['is_active', 'topic__subject']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['views']
    
    fieldsets = (
        ('Content', {
            'fields': ('topic', 'name', 'name_hi', 'slug', 'description', 'description_hi',
                      'comprehensive_content', 'comprehensive_content_hi')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active', 'views'),
        }),
    )
    
    def questions_count(self, obj):
        count = obj.questions.filter(is_active=True).count()
        url = reverse('admin:QA_question_changelist') + f'?part__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} questions</a>', url, count)
    questions_count.short_description = "Questions"


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'is_active', 'parts_count']
    list_filter = ['is_active', 'subject']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    
    fieldsets = (
        ('Content', {
            'fields': ('subject', 'name', 'name_hi', 'slug', 'description', 'description_hi',
                      'comprehensive_content', 'comprehensive_content_hi')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
    )
    
    def parts_count(self, obj):
        count = obj.parts.filter(is_active=True).count()
        url = reverse('admin:QA_part_changelist') + f'?topic__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} parts</a>', url, count)
    parts_count.short_description = "Parts"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active', 'topics_count']
    list_filter = ['is_active']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    
    fieldsets = (
        ('Content', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'description_hi', 'icon', 'image')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
    )
    
    def topics_count(self, obj):
        count = obj.topics.filter(is_active=True).count()
        url = reverse('admin:QA_topic_changelist') + f'?subject__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} topics</a>', url, count)
    topics_count.short_description = "Topics"


@admin.register(ComprehensiveContent)
class ComprehensiveContentAdmin(admin.ModelAdmin):
    list_display = ['heading', 'content_type', 'subject_link', 'topic_link', 'part_link', 'order', 'is_active']
    list_filter = ['content_type', 'is_active']
    search_fields = ['heading', 'heading_hi', 'content', 'content_hi']
    list_editable = ['order', 'is_active']
    list_per_page = 20

    fieldsets = (
        ('Content Type', {
            'fields': ('content_type', 'subject', 'topic', 'part'),
        }),
        ('Content', {
            'fields': ('heading', 'heading_hi', 'content', 'content_hi'),
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
    )
    
    def subject_link(self, obj):
        if obj.subject:
            url = reverse('admin:QA_subject_change', args=[obj.subject.id])
            return format_html('<a href="{}">{}</a>', url, obj.subject.name)
        return "-"
    subject_link.short_description = "Subject"
    
    def topic_link(self, obj):
        if obj.topic:
            url = reverse('admin:QA_topic_change', args=[obj.topic.id])
            return format_html('<a href="{}">{}</a>', url, obj.topic.name)
        return "-"
    topic_link.short_description = "Topic"
    
    def part_link(self, obj):
        if obj.part:
            url = reverse('admin:QA_part_change', args=[obj.part.id])
            return format_html('<a href="{}">{}</a>', url, obj.part.name)
        return "-"
    part_link.short_description = "Part"


# Customize admin site
admin.site.site_header = "QA Management System"
admin.site.site_title = "QA Admin"
admin.site.index_title = "Welcome to QA Management"

# Add custom admin actions
@admin.action(description='Mark selected questions as featured')
def mark_as_featured(modeladmin, request, queryset):
    queryset.update(is_featured=True)
    modeladmin.message_user(request, f"{queryset.count()} questions marked as featured.")

@admin.action(description='Remove featured from selected questions')
def remove_featured(modeladmin, request, queryset):
    queryset.update(is_featured=False)
    modeladmin.message_user(request, f"Featured removed from {queryset.count()} questions.")

# Register the actions with QuestionAdmin
QuestionAdmin.actions = [mark_as_featured, remove_featured]