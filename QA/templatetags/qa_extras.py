# QA/templatetags/qa_extras.py
from django import template
import re

register = template.Library()

@register.filter
def safe_render(content):
    """Safely render content by removing broken URL tags"""
    if not content:
        return content
    
    # Remove or fix {% url %} tags with empty arguments
    def fix_url_tags(text):
        # Pattern 1: {% url 'part_detail' 'history' '1857-movement' '' %}
        pattern1 = r"{%\s*url\s+['\"]part_detail['\"]\s+([^%]*?),\s*['\"]{2}\s*%}"
        
        # Pattern 2: {% url 'part_detail' 'history' '1857-movement' %}
        pattern2 = r"{%\s*url\s+['\"]part_detail['\"]\s+([^%]+?)%}"
        
        def replace_func(match):
            args_str = match.group(1).strip()
            # Split by comma and clean each argument
            args = [arg.strip().strip("'\"") for arg in args_str.split(',') if arg.strip()]
            
            if len(args) >= 2:
                return f'<a href="/qa/subject/{args[0]}/{args[1]}/" class="text-indigo-600 hover:text-indigo-800">View Parts</a>'
            return '[Link unavailable]'
        
        # Apply both patterns
        text = re.sub(pattern1, replace_func, text)
        text = re.sub(pattern2, replace_func, text)
        
        return text
    
    return fix_url_tags(content)