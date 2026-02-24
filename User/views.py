# User/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Case, When, IntegerField, F, Q
from django.contrib import messages
import json
from datetime import datetime

from .forms import ProfileForm

# Import from your exams app
from exams.models import MockTestAttempt, UserAnswer, Testimonial

@login_required
def profile_view(request):
    """
    User profile page with editable profile information and dashboard statistics.
    """
    user = request.user
    
    # Handle profile form submission
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user.profile)
        if form.is_valid():
            form.save()
            # Update email if changed
            if form.cleaned_data['email'] != user.email:
                user.email = form.cleaned_data['email']
                user.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('User:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=user.profile)
    
    # ----- DASHBOARD DATA (from your exams app) -----
    # Get all completed attempts
    attempts = MockTestAttempt.objects.filter(
        user=user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')

    # Get user's testimonial if exists
    try:
        user_testimonial = Testimonial.objects.filter(user=user).first()
    except:
        user_testimonial = None

    # ----- Overall statistics -----
    total_tests = attempts.count()
    avg_score = 0
    best_score = 0

    if total_tests > 0:
        total_percentage = 0
        for attempt in attempts:
            if attempt.total_marks > 0:
                percentage = (attempt.correct_answers / attempt.total_marks) * 100
                total_percentage += percentage
                if percentage > best_score:
                    best_score = percentage

        avg_score = round(total_percentage / total_tests, 1)
        best_score = round(best_score, 1)

    # ----- Subject performance data for bar chart -----
    user_answers = UserAnswer.objects.filter(
        attempt__user=user,
        attempt__is_completed=True
    ).select_related('question__subject', 'selected_option')

    # Aggregate per subject
    subject_stats_qs = user_answers.values(
        subject_name=F('question__subject__name')
    ).annotate(
        total=Count('id'),
        correct=Count(Case(
            When(selected_option__is_correct=True, then=1),
            output_field=IntegerField()
        ))
    ).order_by('subject_name')

    # Convert to list for template (makes it easier to work with)
    subject_stats = []
    for stat in subject_stats_qs:
        subject_stats.append({
            'subject_name': stat['subject_name'] or 'Uncategorized',
            'total': stat['total'],
            'correct': stat['correct'],
            'percentage': round((stat['correct'] / stat['total'] * 100), 1) if stat['total'] > 0 else 0
        })

    # ----- Recent activity (latest 5 attempts) -----
    recent_attempts = attempts[:5]
    
    # Prepare recent attempts data for line chart (convert to list of dicts)
    recent_attempts_list = []
    for attempt in recent_attempts:
        if attempt.total_marks > 0:
            percentage = (attempt.correct_answers / attempt.total_marks) * 100
        else:
            percentage = 0
            
        recent_attempts_list.append({
            'id': attempt.id,
            'mock_test__title': attempt.mock_test.title,
            'submitted_at': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            'correct_answers': attempt.correct_answers,
            'total_marks': attempt.total_marks,
            'percentage': round(percentage, 1)
        })
    
    # ----- Additional useful stats -----
    in_progress_tests = MockTestAttempt.objects.filter(
        user=user,
        is_completed=False
    ).count()
    
    total_questions_answered = UserAnswer.objects.filter(
        attempt__user=user
    ).count()
    
    correct_answers = UserAnswer.objects.filter(
        attempt__user=user,
        selected_option__is_correct=True
    ).count()
    
    accuracy_rate = 0
    if total_questions_answered > 0:
        accuracy_rate = round((correct_answers / total_questions_answered) * 100, 1)
    
    latest_attempt = attempts.first()
    last_activity_date = latest_attempt.submitted_at if latest_attempt else None
    
    # Convert subject_stats to JSON for JavaScript
    subject_stats_json = json.dumps(subject_stats)
    
    context = {
        'form': form,
        # Core dashboard stats
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'recent_attempts': attempts[:3],  # Keep original for template loop
        'user_testimonial': user_testimonial,
        
        # Additional stats
        'attempts_count': total_tests,
        'completed_exams': total_tests,
        'in_progress_tests': in_progress_tests,
        'total_questions_answered': total_questions_answered,
        'accuracy_rate': accuracy_rate,
        'correct_answers': correct_answers,
        'last_activity_date': last_activity_date,
        
        # Subject data for both template and charts
        'subject_stats': subject_stats,  # For template loop
        'subject_stats_json': subject_stats_json,  # For charts
        
        # Recent attempts for line chart
        'recent_attempts_json': json.dumps(recent_attempts_list),
    }
    
    return render(request, 'User/profile.html', context)
