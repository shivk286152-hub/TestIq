from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Columns to display in the list view
    list_display = ('user', 'name', 'email', 'phone', 'city', 'state', 'get_profile_pic_preview')
    
    # Clickable fields in list view
    list_display_links = ('user', 'name')
    
    # Filters sidebar
    list_filter = ('state', 'city')
    
    # Searchable fields
    search_fields = ('user__username', 'name', 'email', 'phone', 'city')
    
    # Number of items per page
    list_per_page = 25
    
    # Organize fields into sections
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Profile Picture', {
            'fields': ('profile_pic',),
            'classes': ('wide',)
        }),
        ('Address Details', {
            'fields': ('city', 'state', 'pincode'),
            'classes': ('collapse',)  # Collapsible section
        }),
    )
    
    # Read-only fields
    readonly_fields = ('user',)
    
    # Custom method to show profile pic preview
    def get_profile_pic_preview(self, obj):
        if obj.profile_pic:
            return '✅ Has Image'
        return '❌ No Image'
    get_profile_pic_preview.short_description = 'Profile Picture'