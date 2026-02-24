# profile/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Case, When, IntegerField, F, Q
from django.contrib import messages
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
            return redirect('profile')  # Make sure this URL name matches your URL pattern
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=user.profile)
    
    # ----- DASHBOARD DATA (copied from your dashboard view) -----
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

    # ----- Subject performance data (for potential future expansion) -----
    user_answers = UserAnswer.objects.filter(
        attempt__user=user,
        attempt__is_completed=True
    ).select_related('question__subject', 'selected_option')

    # Aggregate per subject (if you want to show subject-wise stats)
    subject_stats = user_answers.values(
        subject_name=F('question__subject__name')
    ).annotate(
        total=Count('id'),
        correct=Count(Case(
            When(selected_option__is_correct=True, then=1),
            output_field=IntegerField()
        ))
    ).order_by('subject_name')

    # ----- Recent activity (latest 3 attempts) -----
    recent_attempts = attempts[:3]  # Get latest 3 attempts
    
    # ----- Calculate in-progress tests (if needed) -----
    in_progress_tests = MockTestAttempt.objects.filter(
        user=user,
        is_completed=False
    ).count()
    
    # ----- Calculate total questions answered -----
    total_questions_answered = UserAnswer.objects.filter(
        attempt__user=user
    ).count()
    
    # ----- Calculate accuracy rate -----
    correct_answers = UserAnswer.objects.filter(
        attempt__user=user,
        selected_option__is_correct=True
    ).count()
    
    accuracy_rate = 0
    if total_questions_answered > 0:
        accuracy_rate = round((correct_answers / total_questions_answered) * 100, 1)
    
    # ----- Get latest attempt date -----
    latest_attempt = attempts.first()
    last_activity_date = latest_attempt.submitted_at if latest_attempt else None
    
    context = {
        'form': form,
        # Core dashboard stats
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'recent_attempts': recent_attempts,
        'user_testimonial': user_testimonial,
        
        # Additional stats you might want to display
        'attempts_count': total_tests,
        'completed_exams': total_tests,  # Since is_completed=True, total_tests = completed
        'in_progress_tests': in_progress_tests,
        'total_questions_answered': total_questions_answered,
        'accuracy_rate': accuracy_rate,
        'correct_answers': correct_answers,
        'last_activity_date': last_activity_date,
        
        # Subject data (if you want to display subject-wise performance)
        'subject_stats': subject_stats,
        
        # For debugging (remove in production)
        'debug_attempts': attempts[:5],  # Show first 5 attempts for debugging
    }
    
    return render(request, 'profile/profile.html', context)


@login_required
def profile_edit_view(request):
    """
    Separate view for editing profile if you want a dedicated edit page.
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            # Update email
            if form.cleaned_data['email'] != request.user.email:
                request.user.email = form.cleaned_data['email']
                request.user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'profile/profile_edit.html', {'form': form})
