from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile
from .forms import ProfileForm
@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Get dashboard data from the exams app
    from exams.models import MockTestAttempt, UserAnswer
    from django.db.models import Count, F, Q, Case, When, IntegerField
    
    # Get all completed attempts
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
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
    
    # Get recent activity (last 3 completed attempts)
    recent_attempts = attempts[:3]
    
    # Get in-progress attempts
    in_progress_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=False
    ).select_related('mock_test')[:2]  # Limit to 2 for display
    
    # Calculate statistics for dashboard cards
    total_questions_attempted = 0
    total_correct = 0
    
    for attempt in attempts:
        total_questions_attempted += attempt.total_marks or 0
        total_correct += attempt.correct_answers or 0
    
    overall_accuracy = 0
    if total_questions_attempted > 0:
        overall_accuracy = round((total_correct / total_questions_attempted) * 100)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        # Dashboard statistics
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'overall_accuracy': overall_accuracy,
        'total_correct': total_correct,
        'total_questions_attempted': total_questions_attempted,
        # Recent activity
        'recent_attempts': recent_attempts,
        'in_progress_attempts': in_progress_attempts,
    }
    
    return render(request, 'User/profile.html', context)