# exams/context_processors.py
from .models import MockTest
from django.utils import timezone
from datetime import timedelta

def site_settings(request):
    """Make site-wide settings available in all templates"""
    return {
        'site_name': 'TestIQ',  # Your site name
    }

def latest_mocktests(request):
    """Get latest 5 mock tests for sidebar"""
    try:
        # Get active mock tests, ordered by newest first
        latest_tests = MockTest.objects.filter(
            is_active=True
        ).order_by('-created_at', '-id')[:5]
        
        # Add debug print to console
        print(f"Context processor - Found {latest_tests.count()} mock tests")
        for test in latest_tests:
            print(f"  - {test.id}: {test.title}")
        
        return {
            'latest_mocktests': latest_tests
        }
    except Exception as e:
        print(f"Error in latest_mocktests context processor: {e}")
        return {
            'latest_mocktests': []
        }