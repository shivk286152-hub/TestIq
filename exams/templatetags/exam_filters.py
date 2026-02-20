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