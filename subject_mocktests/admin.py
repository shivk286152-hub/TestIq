from django.contrib import admin
from .models import Subject, Topic, SubjectMockTest

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
    list_display = ['title', 'subject', 'topic', 'mocktest_id', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['subject', 'topic']
    search_fields = ['title']
    fields = ['title', 'subject', 'topic', 'mocktest_id', 'order', 'is_active']