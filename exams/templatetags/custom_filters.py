# exams/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary by key in Django template"""
    return dictionary.get(key)