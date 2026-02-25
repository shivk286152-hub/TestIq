# User/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Case, When, IntegerField, F
import json

from .forms import ProfileForm
from .models import Profile

# Import from your exams app
from exams.models import MockTestAttempt, UserAnswer, Testimonial

@login_required
def profile_view(request):
    """
    User profile page with collapsible profile form and dynamic dashboard data.
    """
    user = request.user
    
    # Handle profile form submission
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user.profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.save()
            
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
    
    # ========== DASHBOARD DATA (EXACTLY FROM YOUR DASHBOARD VIEW) ==========
    
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

    # ----- Subject‑wise performance for bar chart -----
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

    # Build the lists needed for the chart
    subject_labels = []
    subject_scores = []
    for stat in subject_stats_qs:
        subject_labels.append(stat['subject_name'] or 'Uncategorized')
        percentage = (stat['correct'] / stat['total'] * 100) if stat['total'] > 0 else 0
        subject_scores.append(round(percentage, 1))

    # ----- Attempts data for line chart -----
    attempts_chrono = attempts.order_by('submitted_at')
    attempts_data = []
    for attempt in attempts_chrono:
        if attempt.total_marks > 0:
            score_percentage = (attempt.correct_answers / attempt.total_marks) * 100
        else:
            score_percentage = 0

        attempts_data.append({
            'date': attempt.submitted_at.strftime('%Y-%m-%d'),
            'test_name': attempt.mock_test.title,
            'score': round(score_percentage, 1),
        })

    # Convert to JSON for JavaScript
    subject_labels_json = json.dumps(subject_labels)
    subject_scores_json = json.dumps(subject_scores)
    attempts_json = json.dumps(attempts_data)
    
    # ----- Additional stats for dashboard cards -----
    # Total questions answered
    total_questions_answered = UserAnswer.objects.filter(
        attempt__user=user
    ).count()
    
    # Correct answers count
    correct_answers = UserAnswer.objects.filter(
        attempt__user=user,
        selected_option__is_correct=True
    ).count()
    
    # Accuracy rate
    accuracy_rate = 0
    if total_questions_answered > 0:
        accuracy_rate = round((correct_answers / total_questions_answered) * 100, 1)
    
    # In progress tests
    in_progress_tests = MockTestAttempt.objects.filter(
        user=user,
        is_completed=False
    ).count()
    
    # Recent attempts for activity feed
    recent_attempts = attempts[:5]
    
    context = {
        'form': form,
        # Dashboard stats (matching your original dashboard)
        'attempts': attempts,
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'subject_stats': subject_stats_qs,
        'user_testimonial': user_testimonial,
        'subject_labels_json': subject_labels_json,
        'subject_scores_json': subject_scores_json,
        'attempts_json': attempts_json,
        
        # Additional stats for enhanced dashboard
        'accuracy_rate': accuracy_rate,
        'total_questions_answered': total_questions_answered,
        'correct_answers': correct_answers,
        'in_progress_tests': in_progress_tests,
        'recent_attempts': recent_attempts,
    }
    
    return render(request, 'User/profile.html', context)
