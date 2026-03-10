from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Prefetch
from .models import Subject, Topic, SubjectMockTest
import traceback

def subject_list(request):
    """Show all subjects"""
    subjects = Subject.objects.filter(is_active=True).prefetch_related(
        Prefetch('topics', queryset=Topic.objects.filter(is_active=True))
    )
    return render(request, 'subject_mocktests/subject_list.html', {
        'subjects': subjects
    })

def subject_detail(request, slug):
    """Show topics and mocktests under subject"""
    try:
        subject = get_object_or_404(Subject, slug=slug, is_active=True)
        print(f"Found subject: {subject.name}")  # Debug print
        
        # Get all mocktests
        mocktests = SubjectMockTest.objects.filter(
            subject=subject,
            is_active=True
        ).select_related('topic')
        
        print(f"Found {mocktests.count()} mocktests")  # Debug print
        
        # Group by topic
        topics_data = []
        topics = subject.topics.filter(is_active=True)
        print(f"Found {topics.count()} topics")  # Debug print
        
        for topic in topics:
            topic_tests = mocktests.filter(topic=topic)
            if topic_tests.exists():
                topics_data.append({
                    'topic': topic,
                    'tests': topic_tests
                })
        
        # Tests without topic
        no_topic_tests = mocktests.filter(topic__isnull=True)
        
        context = {
            'subject': subject,
            'topics_data': topics_data,
            'no_topic_tests': no_topic_tests
        }
        
        return render(request, 'subject_mocktests/subject_detail.html', context)
    
    except Subject.DoesNotExist:
        messages.error(request, 'Subject not found.')
        return redirect('subject_mocktests:subject_list')
    
    except Exception as e:
        print("="*50)
        print("ERROR in subject_detail:")
        print(traceback.format_exc())
        print("="*50)
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('subject_mocktests:subject_list')



@login_required
def pretest_page(request, mocktest_id):
    """Pretest page before redirecting to old app"""
    subject_mocktest = get_object_or_404(SubjectMockTest, id=mocktest_id, is_active=True)
    
    # Get the actual mocktest from old app to show details
    from exams.models import MockTest
    try:
        old_mocktest = MockTest.objects.get(id=subject_mocktest.mocktest_id)
    except MockTest.DoesNotExist:
        messages.error(request, 'Test not found. Please contact support.')
        return redirect('subject_mocktests:subject_list')
    
    # Check if user has incomplete attempt in old app
    from exams.models import MockTestAttempt
    existing_attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=old_mocktest,
        is_completed=False
    ).first()
    
    context = {
        'subject_mocktest': subject_mocktest,
        'old_mocktest': old_mocktest,
        'existing_attempt': existing_attempt,
        'languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'hi', 'name': 'हिन्दी'},
        ]
    }
    return render(request, 'subject_mocktests/pretest_page.html', context)

@login_required
def start_test(request, mocktest_id):
    """Handle pretest and redirect to old app's start_test"""
    if request.method == 'POST':
        subject_mocktest = get_object_or_404(SubjectMockTest, id=mocktest_id)
        
        # Validate terms
        terms_accepted = request.POST.get('terms_accepted')
        if not terms_accepted:
            messages.error(request, 'You must accept the terms to continue.')
            return redirect('subject_mocktests:pretest_page', mocktest_id=mocktest_id)
        
        # Validate language
        language = request.POST.get('language')
        if not language:
            messages.error(request, 'Please select your preferred language.')
            return redirect('subject_mocktests:pretest_page', mocktest_id=mocktest_id)
        
        # Store language in session for old app
        request.session['test_language'] = language
        request.session[f'test_{subject_mocktest.mocktest_id}_language'] = language
        
        # Redirect to old app's start_test
        # Old app's start_test will create MockTestAttempt and redirect to attempt_test
        return redirect('exams:start_test', mocktest_id=subject_mocktest.mocktest_id)
    
    return redirect('subject_mocktests:pretest_page', mocktest_id=mocktest_id)