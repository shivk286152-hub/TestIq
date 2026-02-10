from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    ExamNotification,
    NotificationHighlight,
    NotificationTable,
    NotificationTableRow,
    NotificationTableCell,
    NotificationBlock
)

# ---------- TABLE CELLS ----------
class NotificationTableCellInline(admin.TabularInline):
    model = NotificationTableCell
    extra = 2


# ---------- TABLE ROWS ----------
class NotificationTableRowInline(admin.TabularInline):
    model = NotificationTableRow
    extra = 2


@admin.register(NotificationTableRow)
class NotificationTableRowAdmin(admin.ModelAdmin):
    inlines = [NotificationTableCellInline]


# ---------- TABLE ----------
class NotificationTableInline(admin.TabularInline):
    model = NotificationTable
    extra = 1


@admin.register(NotificationTable)
class NotificationTableAdmin(admin.ModelAdmin):
    inlines = [NotificationTableRowInline]


# ---------- HIGHLIGHTS ----------
class NotificationHighlightInline(admin.TabularInline):
    model = NotificationHighlight
    extra = 2


# ---------- BLOCKS ----------
class NotificationBlockInline(admin.TabularInline):
    model = NotificationBlock
    extra = 2
    ordering = ("order",)


# ---------- MAIN NOTIFICATION ----------
@admin.register(ExamNotification)
class ExamNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title",)
    inlines = [
        NotificationHighlightInline,
        NotificationTableInline,
        NotificationBlockInline,
    ]


# ---------- SIMPLE REGISTRATION ----------
admin.site.register(NotificationTableCell)
admin.site.register(NotificationBlock)
admin.site.register(NotificationHighlight)
