from django.contrib import admin
from .models import Subject, Topic, SubjectMockTest, Question

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['subject']

@admin.register(SubjectMockTest)
class SubjectMockTestAdmin(admin.ModelAdmin):
    # Updated list_display - removed mocktest_id, added new fields
    list_display = ['title', 'subject', 'topic', 'difficulty', 'time_limit', 
                   'total_marks', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['subject', 'topic', 'difficulty', 'is_active']
    search_fields = ['title']
    
    # Organized fields into sections
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'topic', 'order', 'is_active')
        }),
        ('Test Configuration', {
            'fields': ('difficulty', 'time_limit', 'total_marks', 'duration',
                      'negative_marking_type', 'negative_marking_value')
        }),
    )

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'mocktest', 'marks']
    list_filter = ['mocktest']
    search_fields = ['question_text']