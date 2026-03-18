# exams/context_processors.py
from .models import MockTest
from subject_mocktests.models import Subject
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

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
        
        return {
            'latest_mocktests': latest_tests
        }
    except Exception as e:
        # print(f"Error in latest_mocktests context processor: {e}")
        return {
            'latest_mocktests': []
        }

def subject_mocktests_subjects(request):
    """Get subjects from subject_mocktests app for sidebar dropdown"""
    try:
        # Get all subjects with their mock test counts
        subjects = Subject.objects.all().annotate(
            test_count=Count('mock_tests', filter=Q(mock_tests__is_active=True))
        ).order_by('order', 'name')[:10]  # Limit to 10 subjects
        
        return {
            'subject_mocktests_subjects': subjects
        }
    except Exception as e:
        # print(f"Error in subject_mocktests_subjects context processor: {e}")
        return {
            'subject_mocktests_subjects': []
        }

def all_context(request):
    """Combined context processor that returns all data"""
    context = {}
    
    # Add site settings
    context.update(site_settings(request))
    
    # Add latest mocktests
    context.update(latest_mocktests(request))
    
    # Add subject mocktests subjects
    context.update(subject_mocktests_subjects(request))
    
    # Add current year for copyright
    from datetime import datetime
    context['current_year'] = datetime.now().year
    
    # Add user to context
    context['user'] = request.user
    
    return context