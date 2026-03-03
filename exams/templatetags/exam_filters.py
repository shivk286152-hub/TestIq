# templatetags/exam_filters.py
from django import template

register = template.Library()

@register.filter
def chr_upper(value):
    """Convert number to uppercase letter (1 -> A, 2 -> B, etc.)"""
    try:
        return chr(64 + int(value))
    except (ValueError, TypeError):
        return value
    
@register.filter
def format_time(seconds):
    """Convert seconds to MM:SS format"""
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "00:00"    