from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django import forms
from .models import (
    Subject, Topic, Part, Question, 
    QuestionImage, QuestionTable, ComprehensiveContent,
    QuestionCategory
)


# ============================================
# INLINE ADMIN CLASSES
# ============================================

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


# ============================================
# CUSTOM FORM FOR PART WITH CONTENT HELP
# ============================================

class PartAdminForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 30,
                'style': 'width: 100%; font-family: "Consolas", "Monaco", monospace; font-size: 14px; line-height: 1.6;',
                'placeholder': '''
=== TABLE EXAMPLE ===
[table]
Name | Age | City | Occupation
John | 25 | NYC | Engineer
Jane | 30 | LA | Designer
Mike | 35 | CHI | Developer
[/table]

=== LIST EXAMPLE ===
[list]
* Key concepts covered in this chapter
* Important formulas and equations
* Common applications and examples
* Practice questions and solutions
[/list]

=== IMAGE EXAMPLE ===
[image: /media/images/diagram.jpg]Figure 1: System Architecture Diagram[/image]

=== CODE EXAMPLE ===
[code]
def calculate_area(radius):
    return 3.14159 * radius ** 2
[/code]

=== QUOTE EXAMPLE ===
[quote]This is an important quote from the text.[/quote]

=== HIGHLIGHT EXAMPLE ===
[highlight]Key concept: Understanding the fundamentals[/highlight]
                '''
            }),
            'content_hi': forms.Textarea(attrs={
                'rows': 30,
                'style': 'width: 100%; font-family: "Consolas", "Monaco", monospace; font-size: 14px; line-height: 1.6;'
            }),
        }


# ============================================
# MODEL ADMIN CLASSES
# ============================================

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color_preview', 'icon', 'is_active', 'order', 'question_count']
    list_filter = ['is_active']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'color', 'icon')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
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
            'fields': ('part', 'order', 'views'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_featured', 'remove_featured', 'mark_as_active', 'mark_as_inactive']
    
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
    
    # Admin Actions
    @admin.action(description='Mark selected questions as featured')
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} questions marked as featured.")
    
    @admin.action(description='Remove featured from selected questions')
    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f"Featured removed from {queryset.count()} questions.")
    
    @admin.action(description='Mark selected questions as active')
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} questions marked as active.")
    
    @admin.action(description='Mark selected questions as inactive')
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} questions marked as inactive.")


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    form = PartAdminForm
    list_display = ['name', 'topic', 'order', 'is_active', 'questions_count', 'views', 'content_preview']
    list_filter = ['is_active', 'topic__subject', 'topic']
    search_fields = ['name', 'name_hi', 'description', 'content', 'content_hi']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['views', 'created_at', 'updated_at', 'rendered_content_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('topic', 'name', 'name_hi', 'slug', 'order', 'is_active')
        }),
        ('Descriptions', {
            'fields': ('description', 'description_hi')
        }),
        ('Main Content', {
            'fields': ('content', 'content_hi'),
            'classes': ('wide',),
            'description': '''
            <div class="alert alert-info" style="padding: 15px; background-color: #e7f3ff; border-left: 4px solid #1a73e8; margin-bottom: 20px;">
                <h4 style="margin-top: 0; color: #1a73e8;">📝 Content Formatting Guide</h4>
                <ul style="margin-bottom: 0;">
                    <li><strong>Tables:</strong> Use <code>[table]...[/table]</code> with <code>|</code> as column separator</li>
                    <li><strong>Lists:</strong> Use <code>[list]...[/list]</code> with <code>*</code> for each item</li>
                    <li><strong>Images:</strong> Use <code>[image: path/to/image]Caption[/image]</code></li>
                    <li><strong>Code:</strong> Use <code>[code]...[/code]</code> for code blocks</li>
                    <li><strong>Quotes:</strong> Use <code>[quote]...[/quote]</code> for quotations</li>
                    <li><strong>Highlights:</strong> Use <code>[highlight]...[/highlight]</code> for important text</li>
                </ul>
                <p style="margin-top: 10px; margin-bottom: 0;">
                    <strong>💡 Tip:</strong> Copy data from Excel/CSV and paste directly into table format!
                </p>
            </div>
            '''
        }),
        ('Preview', {
            'fields': ('rendered_content_preview',),
            'classes': ('collapse',),
            'description': 'Preview of rendered content with all formatting applied.'
        }),
        ('Statistics', {
            'fields': ('views',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def questions_count(self, obj):
        count = obj.questions.filter(is_active=True).count()
        url = reverse('admin:QA_question_changelist') + f'?part__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} questions</a>', url, count)
    questions_count.short_description = "Questions"
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
            return format_html(
                '<span style="color: #6b7280; font-size: 12px;">{}</span>',
                preview.replace('\n', ' ').strip()
            )
        return mark_safe('<span style="color: #9ca3af;">-</span>')
    content_preview.short_description = "Content Preview"
    
    def rendered_content_preview(self, obj):
        """Show a preview of the rendered content with all formatting"""
        if obj.content:
            rendered = obj.render_content()
            return format_html(
                '''
                <div style="border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; background-color: #fafafa; max-height: 500px; overflow-y: auto;">
                    <div style="margin-bottom: 10px; color: #6b7280; font-size: 12px;">
                        <strong>📄 Rendered Preview (English):</strong>
                    </div>
                    {}
                    <hr style="margin: 20px 0; border: 1px dashed #e5e7eb;">
                    <div style="color: #6b7280; font-size: 12px;">
                        <strong>📄 Raw Content:</strong>
                    </div>
                    <pre style="background-color: #f3f4f6; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; white-space: pre-wrap; word-wrap: break-word;">{}</pre>
                </div>
                ''',
                rendered,
                obj.content[:1000] + ('...' if len(obj.content) > 1000 else '')
            )
        return mark_safe('<span style="color: #9ca3af;">No content to preview</span>')
    rendered_content_preview.short_description = "Rendered Content Preview"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'is_active', 'parts_count']
    list_filter = ['is_active', 'subject']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('subject', 'name', 'name_hi', 'slug', 'description', 'description_hi')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parts_count(self, obj):
        count = obj.parts.filter(is_active=True).count()
        url = reverse('admin:QA_part_changelist') + f'?topic__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} parts</a>', url, count)
    parts_count.short_description = "Parts"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active', 'topics_count', 'icon_preview']
    list_filter = ['is_active']
    search_fields = ['name', 'name_hi', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    list_per_page = 20
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('name', 'name_hi', 'slug', 'description', 'description_hi', 'icon', 'image')
        }),
        ('Metadata', {
            'fields': ('order', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def topics_count(self, obj):
        count = obj.topics.filter(is_active=True).count()
        url = reverse('admin:QA_topic_changelist') + f'?subject__id__exact={obj.id}'
        return format_html('<a href="{}" style="font-weight:600; text-decoration:none;">{} topics</a>', url, count)
    topics_count.short_description = "Topics"
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<i class="fa {}" style="font-size: 20px;"></i>', obj.icon)
        return mark_safe('<span style="color: #9ca3af;">-</span>')
    icon_preview.short_description = "Icon"


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
        return mark_safe('<span>-</span>')
    subject_link.short_description = "Subject"
    
    def topic_link(self, obj):
        if obj.topic:
            url = reverse('admin:QA_topic_change', args=[obj.topic.id])
            return format_html('<a href="{}">{}</a>', url, obj.topic.name)
        return mark_safe('<span>-</span>')
    topic_link.short_description = "Topic"
    
    def part_link(self, obj):
        if obj.part:
            url = reverse('admin:QA_part_change', args=[obj.part.id])
            return format_html('<a href="{}">{}</a>', url, obj.part.name)
        return mark_safe('<span>-</span>')
    part_link.short_description = "Part"


@admin.register(QuestionTable)
class QuestionTableAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'question', 'order']
    list_filter = ['question']
    search_fields = ['table_data', 'caption']
    list_per_page = 20
    
    fieldsets = (
        ('Table Content', {
            'fields': ('question', 'table_data', 'caption', 'caption_hi')
        }),
        ('Metadata', {
            'fields': ('order',)
        }),
    )


# ============================================
# CUSTOMIZE ADMIN SITE
# ============================================

admin.site.site_header = "QA Management System"
admin.site.site_title = "QA Admin"
admin.site.index_title = "Welcome to QA Management"