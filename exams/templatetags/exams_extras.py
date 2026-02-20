from django import template

register = template.Library()

@register.filter
def chr(value):
    """Convert number to letter (1 -> A, 2 -> B, etc.)"""
    try:
        return chr(int(value) + 64)
    except (ValueError, TypeError):
        return value