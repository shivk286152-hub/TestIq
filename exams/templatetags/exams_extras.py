from django import template

register = template.Library()

@register.filter
def chr(value):
    """Convert number to letter (1->A, 2->B, etc.)"""
    try:
        return chr(64 + int(value))
    except (ValueError, TypeError):
        return value
    
@register.filter
def get_letter(value):
    """Convert 1 to A, 2 to B, etc."""
    letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    if 1 <= value <= len(letters):
        return letters[value - 1]
    return str(value)

    
    