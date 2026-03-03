from django.contrib import admin
from .views import current_affairs_detail,CurrentAffairs,CurrentAffairsCategory

# Register your models here.
@admin.register(CurrentAffairsCategory)
class CurrentAffairsCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'articles_count', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ['name']}
    list_editable = ['order', 'is_active']
    
    def articles_count(self, obj):
        return obj.articles.filter(status='published').count()
    articles_count.short_description = 'Published Articles'

@admin.register(CurrentAffairs)
class CurrentAffairsAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'news_date', 'status', 'is_featured', 'views_count']
    list_filter = ['category', 'status', 'is_featured', 'news_date']
    search_fields = ['title', 'content', 'tags']
    prepopulated_fields = {'slug': ['title']}
    readonly_fields = ['views_count', 'published_date', 'updated_date']
    date_hierarchy = 'news_date'
    list_editable = ['status', 'is_featured']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'news_date', 'status', 'is_featured')
        }),
        ('Content', {
            'fields': ('summary', 'content', 'tags')
        }),
        ('Media', {
            'fields': ('featured_image', 'image_caption'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('source', 'display_weight', 'views_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('published_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )