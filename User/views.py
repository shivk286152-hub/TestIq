# User/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Case, When, IntegerField, F, Q
import json
from datetime import timedelta, date
from django.utils import timezone

from .forms import ProfileForm
from .models import Profile
from exams.models import MockTestAttempt as ExamsAttempt, UserAnswer as ExamsAnswer, Testimonial
from subject_mocktests.models import MockTestAttempt as SubjectAttempt, UserAnswer as SubjectAnswer


@login_required
def profile_view(request):
    """
    User profile page with collapsible profile form and separate dashboards for each app.
    """
    user = request.user
    
    # Get or create profile
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Handle profile form submission
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
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
        form = ProfileForm(instance=profile)
    
    # Get user's testimonial if exists
    try:
        user_testimonial = Testimonial.objects.filter(user=user).first()
    except:
        user_testimonial = None
    
    # ========== EXAMS APP DATA ==========
    exams_attempts = ExamsAttempt.objects.filter(
        user=user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
    exams_total = exams_attempts.count()
    
    if exams_total > 0:
        exams_total_percentage = 0
        exams_best_score = 0
        exams_total_correct = 0
        exams_total_questions = 0
        
        for attempt in exams_attempts:
            if attempt.total_marks > 0:
                percentage = (attempt.correct_answers / attempt.total_marks) * 100
                exams_total_percentage += percentage
                if percentage > exams_best_score:
                    exams_best_score = percentage
                
                exams_total_correct += attempt.correct_answers or 0
                exams_total_questions += attempt.total_marks or 0
        
        exams_avg_score = round(exams_total_percentage / exams_total, 1)
        exams_best_score = round(exams_best_score, 1)
        exams_accuracy = round((exams_total_correct / exams_total_questions * 100), 1) if exams_total_questions > 0 else 0
    else:
        exams_avg_score = 0
        exams_best_score = 0
        exams_accuracy = 0
        exams_total_correct = 0
        exams_total_questions = 0
    
    # Exams in-progress
    exams_in_progress = ExamsAttempt.objects.filter(
        user=user,
        is_completed=False
    ).count()
    
    # Exams recent attempts
    exams_recent = []
    for attempt in exams_attempts[:5]:
        exams_recent.append({
            'id': attempt.id,
            'title': attempt.mock_test.title,
            'score': round((attempt.correct_answers / attempt.total_marks * 100), 1) if attempt.total_marks else 0,
            'correct': attempt.correct_answers,
            'total': attempt.total_marks,
            'date': attempt.submitted_at.strftime('%b %d, %Y') if attempt.submitted_at else 'N/A',
        })
    
    # Exams subject-wise performance
    exams_answers = ExamsAnswer.objects.filter(
        attempt__user=user,
        attempt__is_completed=True
    ).select_related('question__subject', 'selected_option')
    
    exams_subject_stats = {}
    for answer in exams_answers:
        subject_name = answer.question.subject.name if answer.question.subject else 'General'
        if subject_name not in exams_subject_stats:
            exams_subject_stats[subject_name] = {'total': 0, 'correct': 0}
        exams_subject_stats[subject_name]['total'] += 1
        if answer.selected_option and answer.selected_option.is_correct:
            exams_subject_stats[subject_name]['correct'] += 1
    
    exams_subject_labels = []
    exams_subject_scores = []
    for subject, stats in exams_subject_stats.items():
        if stats['total'] > 0:
            exams_subject_labels.append(subject)
            exams_subject_scores.append(round((stats['correct'] / stats['total'] * 100), 1))
    
    # Exams weekly trend
    exams_weekly_labels = []
    exams_weekly_scores = []
    for i in range(6, -1, -1):
        date_obj = timezone.now().date() - timedelta(days=i)
        exams_weekly_labels.append(date_obj.strftime('%a'))
        
        day_attempts = [a for a in exams_attempts if a.submitted_at and a.submitted_at.date() == date_obj]
        
        if day_attempts:
            day_score = 0
            day_max = 0
            for a in day_attempts:
                day_score += a.raw_score or 0
                day_max += a.total_marks or 0
            exams_weekly_scores.append(round(day_score / day_max * 100, 1) if day_max > 0 else 0)
        else:
            exams_weekly_scores.append(0)
    
    # ========== SUBJECT MOCKTESTS APP DATA ==========
    subject_attempts = SubjectAttempt.objects.filter(
        user=user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subject').order_by('-submitted_at')
    
    subject_total = subject_attempts.count()
    
    if subject_total > 0:
        subject_total_percentage = 0
        subject_best_score = 0
        subject_total_correct = 0
        subject_total_questions = 0
        
        for attempt in subject_attempts:
            if attempt.total_marks > 0:
                if hasattr(attempt, 'percentage'):
                    percentage = attempt.percentage
                else:
                    percentage = (attempt.correct_answers / attempt.total_marks) * 100
                subject_total_percentage += percentage
                if percentage > subject_best_score:
                    subject_best_score = percentage
                
                subject_total_correct += attempt.correct_answers or 0
                subject_total_questions += attempt.total_marks or 0
        
        subject_avg_score = round(subject_total_percentage / subject_total, 1)
        subject_best_score = round(subject_best_score, 1)
        subject_accuracy = round((subject_total_correct / subject_total_questions * 100), 1) if subject_total_questions > 0 else 0
    else:
        subject_avg_score = 0
        subject_best_score = 0
        subject_accuracy = 0
        subject_total_correct = 0
        subject_total_questions = 0
    
    # Subject in-progress
    subject_in_progress = SubjectAttempt.objects.filter(
        user=user,
        is_completed=False
    ).count()
    
    # Subject recent attempts
    subject_recent = []
    for attempt in subject_attempts[:5]:
        subject_recent.append({
            'id': attempt.id,
            'title': attempt.mock_test.title,
            'score': round(attempt.percentage, 1) if hasattr(attempt, 'percentage') else round((attempt.correct_answers / attempt.total_marks * 100), 1),
            'correct': attempt.correct_answers,
            'total': attempt.total_marks,
            'date': attempt.submitted_at.strftime('%b %d, %Y') if attempt.submitted_at else 'N/A',
        })
    
    # Subject topic-wise performance
    subject_answers = SubjectAnswer.objects.filter(
        attempt__user=user,
        attempt__is_completed=True
    ).select_related('question', 'selected_option')
    
    subject_topic_stats = {}
    for answer in subject_answers:
        topic_name = answer.question.topic or answer.question.mock_test.subject.name or 'General'
        if topic_name not in subject_topic_stats:
            subject_topic_stats[topic_name] = {'total': 0, 'correct': 0}
        subject_topic_stats[topic_name]['total'] += 1
        if answer.is_correct:
            subject_topic_stats[topic_name]['correct'] += 1
    
    subject_topic_labels = []
    subject_topic_scores = []
    for topic, stats in subject_topic_stats.items():
        if stats['total'] > 0:
            subject_topic_labels.append(topic)
            subject_topic_scores.append(round((stats['correct'] / stats['total'] * 100), 1))
    
    # Subject weekly trend
    subject_weekly_labels = []
    subject_weekly_scores = []
    for i in range(6, -1, -1):
        date_obj = timezone.now().date() - timedelta(days=i)
        subject_weekly_labels.append(date_obj.strftime('%a'))
        
        day_attempts = [a for a in subject_attempts if a.submitted_at and a.submitted_at.date() == date_obj]
        
        if day_attempts:
            day_score = 0
            day_max = 0
            for a in day_attempts:
                day_score += a.score or 0
                day_max += a.total_marks or 0
            subject_weekly_scores.append(round(day_score / day_max * 100, 1) if day_max > 0 else 0)
        else:
            subject_weekly_scores.append(0)
    
    # Prepare JSON data
    exams_subject_labels_json = json.dumps(exams_subject_labels)
    exams_subject_scores_json = json.dumps(exams_subject_scores)
    exams_weekly_labels_json = json.dumps(exams_weekly_labels)
    exams_weekly_scores_json = json.dumps(exams_weekly_scores)
    
    subject_topic_labels_json = json.dumps(subject_topic_labels)
    subject_topic_scores_json = json.dumps(subject_topic_scores)
    subject_weekly_labels_json = json.dumps(subject_weekly_labels)
    subject_weekly_scores_json = json.dumps(subject_weekly_scores)
    
    context = {
        'form': form,
        'user_testimonial': user_testimonial,
        
        # Exams app data
        'exams_total': exams_total,
        'exams_avg_score': exams_avg_score,
        'exams_best_score': exams_best_score,
        'exams_accuracy': exams_accuracy,
        'exams_in_progress': exams_in_progress,
        'exams_recent': exams_recent,
        'exams_subject_labels_json': exams_subject_labels_json,
        'exams_subject_scores_json': exams_subject_scores_json,
        'exams_weekly_labels_json': exams_weekly_labels_json,
        'exams_weekly_scores_json': exams_weekly_scores_json,
        
        # Subject app data
        'subject_total': subject_total,
        'subject_avg_score': subject_avg_score,
        'subject_best_score': subject_best_score,
        'subject_accuracy': subject_accuracy,
        'subject_in_progress': subject_in_progress,
        'subject_recent': subject_recent,
        'subject_topic_labels_json': subject_topic_labels_json,
        'subject_topic_scores_json': subject_topic_scores_json,
        'subject_weekly_labels_json': subject_weekly_labels_json,
        'subject_weekly_scores_json': subject_weekly_scores_json,
    }
    
    return render(request, 'User/profile.html', context)