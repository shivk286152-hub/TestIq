from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib import messages
import json

from .models import (
    ExamCategory, SubCategory, MockTest, Question, Subject,
    Option, MockTestAttempt, UserAnswer, TestRank, TopRanker,
    UserRankHistory, RankStatistics, QuestionReview, AttemptReview,
    QuestionFeedback, ReviewSession
)

# ==============================
# HOME
# ==============================
def home(request):
    categories = ExamCategory.objects.all()
    mock_tests = MockTest.objects.filter(is_active=True)[:5]
    
    # Get popular tests
    popular_tests = MockTest.objects.filter(
        is_active=True,
        attempts__is_completed=True
    ).annotate(
        attempt_count=Count('attempts')
    ).order_by('-attempt_count')[:3]

    return render(request, "exams/home.html", {
        "categories": categories,
        "mock_tests": mock_tests,
        "popular_tests": popular_tests,
        "site_name": "TestIQ",
    })


# ==============================
# CATEGORY
# ==============================
def category_detail(request, slug):
    category = get_object_or_404(ExamCategory, slug=slug)
    subcategories = SubCategory.objects.filter(category=category)

    return render(request, "exams/subcategory_list.html", {
        "category": category,
        "subcategories": subcategories,
    })


# ==============================
# SUBCATEGORY
# ==============================
def subcategory_detail(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    tests = MockTest.objects.filter(subcategory=subcategory, is_active=True)
    
    # Pagination
    paginator = Paginator(tests, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "exams/mocktest_list.html", {
        "subcategory": subcategory,
        "page_obj": page_obj,
    })


# ==============================
# MOCK TEST DETAIL
# ==============================
def mocktest_detail(request, pk):
    mock_test = get_object_or_404(MockTest, id=pk, is_active=True)
    questions = Question.objects.filter(mock_test=mock_test)
    
    # Get test statistics
    total_attempts = MockTestAttempt.objects.filter(
        mock_test=mock_test,
        is_completed=True
    ).count()
    
    avg_score = MockTestAttempt.objects.filter(
        mock_test=mock_test,
        is_completed=True
    ).aggregate(Avg('percentage'))['percentage__avg'] or 0
    
    # Check if user has attempted
    user_attempt = None
    if request.user.is_authenticated:
        user_attempt = MockTestAttempt.objects.filter(
            user=request.user,
            mock_test=mock_test,
            is_completed=True
        ).order_by('-submitted_at').first()
    
    # Get top rankers for this test
    top_rankers = TopRanker.objects.filter(
        mock_test=mock_test
    ).select_related('user').order_by('rank')[:3]

    return render(request, "exams/mocktest_detail.html", {
        "mock_test": mock_test,
        "questions": questions,
        "total_attempts": total_attempts,
        "avg_score": round(avg_score, 2),
        "user_attempt": user_attempt,
        "top_rankers": top_rankers,
    })


# ==============================
# START TEST (CREATE ATTEMPT)
# ==============================
@login_required
def start_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
    
    # Check for existing incomplete attempt
    existing_attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    if existing_attempt:
        return redirect("exams:attempt_test", mocktest_id=mocktest.id)
    
    # Create new attempt
    attempt = MockTestAttempt.objects.create(
        user=request.user,
        mock_test=mocktest,
        started_at=timezone.now(),
        is_completed=False,
        total_marks=mocktest.questions.count()
    )
    
    # Create review session
    ReviewSession.objects.create(
        user=request.user,
        attempt=attempt
    )

    return redirect("exams:attempt_test", mocktest_id=mocktest.id)


# ==============================
# ATTEMPT TEST (SERVER TIMER)
# ==============================
@login_required
def attempt_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    
    attempt = get_object_or_404(
        MockTestAttempt,
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    )
    
    # Remaining time
    duration = mocktest.duration * 60
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining_seconds = int(duration - elapsed)
    
    # Auto submit if time over
    if remaining_seconds <= 0:
        return redirect("exams:submit_test", mocktest_id=mocktest.id)
    
    subjects = Subject.objects.filter(
        questions__mock_test=mocktest
    ).distinct()
    
    questions = mocktest.questions.all().order_by("id")
    
    # Get saved answers from session
    saved_answers = request.session.get(f"answers_{mocktest.id}", {})
    
    return render(request, "exams/attempt_test.html", {
        "mocktest": mocktest,
        "questions": questions,
        "subjects": subjects,
        "remaining_seconds": remaining_seconds,
        "saved_answers": saved_answers,
    })


# ==============================
# SAVE ANSWER (SESSION)
# ==============================
@login_required
def save_answer(request):
    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith("question_"):
                qid = int(key.replace("question_", ""))
                question = get_object_or_404(Question, id=qid)
                
                answers = request.session.get(
                    f"answers_{question.mock_test.id}", {}
                )
                
                if value == "":
                    answers.pop(str(qid), None)
                else:
                    answers[str(qid)] = int(value)
                
                request.session[f"answers_{question.mock_test.id}"] = answers
                
        return JsonResponse({"status": "ok"})
    
    return JsonResponse({"status": "error"})


# ==============================
# AJAX QUESTION LOAD
# ==============================
@login_required
def ajax_question(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    questions = Question.objects.filter(
        mock_test=mocktest
    ).prefetch_related("options").order_by("id")
    
    q_number = request.GET.get("q", 1)
    
    try:
        q_number = int(q_number)
    except:
        q_number = 1
    
    q_number = max(1, min(q_number, questions.count()))
    question = questions[q_number - 1]
    
    saved_answers = request.session.get(f"answers_{mocktest.id}", {})
    selected_option = saved_answers.get(str(question.id))
    
    # Get question review data if exists
    try:
        review = QuestionReview.objects.get(question=question)
    except QuestionReview.DoesNotExist:
        review = None
    
    return render(request, "exams/ajax_question.html", {
        "question": question,
        "question_number": q_number,
        "total_questions": questions.count(),
        "selected_option": selected_option,
        "review": review,
    })


# ==============================
# SUBMIT TEST (AUTO + MANUAL)
# ==============================
@login_required
def submit_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    
    attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    if not attempt:
        messages.error(request, "No active test found.")
        return redirect("exams:home")
    
    # Prevent double submit
    if attempt.is_completed:
        return redirect("exams:result_dashboard", attempt_id=attempt.id)
    
    attempt.submitted_at = timezone.now()
    attempt.is_completed = True
    
    questions = Question.objects.filter(mock_test=mocktest)
    session_answers = request.session.get(f"answers_{mocktest.id}", {})
    
    correct = 0
    wrong = 0
    skipped = 0
    
    # Create UserAnswer objects and calculate scores
    for question in questions:
        selected_id = session_answers.get(str(question.id))
        
        if not selected_id:
            skipped += 1
            UserAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_option=None
            )
            continue
        
        selected_option = Option.objects.get(id=selected_id)
        ua = UserAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_option=selected_option
        )
        
        if selected_option.is_correct:
            correct += 1
        else:
            wrong += 1
    
    # Update attempt with scores
    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped_answers = skipped
    attempt.total_marks = questions.count()
    attempt.score = correct  # Assuming 1 mark per correct
    
    # Apply negative marking if any
    # attempt.score = correct - (wrong * 0.25)  # Uncomment if you want negative marking
    
    attempt.save()
    
    # Calculate rank
    rank_info = calculate_rank(attempt)
    
    # Create attempt review
    create_attempt_review(attempt)
    
    # Clear session answers
    request.session.pop(f"answers_{mocktest.id}", None)
    
    messages.success(request, "Test submitted successfully!")
    return redirect("exams:result_dashboard", attempt_id=attempt.id)


# ==============================
# RESULT DASHBOARD
# ==============================
@login_required
def result_dashboard(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    answers = attempt.answers.select_related(
        "question",
        "selected_option"
    ).prefetch_related("question__options")
    
    # Get rank info
    rank_info = TestRank.objects.filter(attempt=attempt).first()
    
    # Get top 3 rankers for this test
    top_rankers = TopRanker.objects.filter(
        mock_test=attempt.mock_test
    ).select_related('user').order_by('rank')[:3]
    
    # Get next rankers (4-10)
    next_rankers = TopRanker.objects.filter(
        mock_test=attempt.mock_test,
        rank__gt=3,
        rank__lte=10
    ).select_related('user').order_by('rank')
    
    # Get subject-wise stats
    subject_stats = []
    subjects = Subject.objects.filter(mock_test=attempt.mock_test)
    
    for subject in subjects:
        subject_questions = Question.objects.filter(
            mock_test=attempt.mock_test,
            subject=subject
        )
        q_ids = subject_questions.values_list('id', flat=True)
        
        subject_answers = UserAnswer.objects.filter(
            attempt=attempt,
            question_id__in=q_ids
        )
        
        correct = subject_answers.filter(selected_option__is_correct=True).count()
        total = subject_questions.count()
        wrong = subject_answers.filter(
            selected_option__isnull=False,
            selected_option__is_correct=False
        ).count()
        skipped = total - subject_answers.count()
        
        subject_stats.append({
            'subject': subject.name,
            'correct': correct,
            'wrong': wrong,
            'skipped': skipped,
            'total': total,
            'marks': round((correct / total) * 100, 2) if total > 0 else 0,
        })
    
    # Get attempt review
    try:
        attempt_review = AttemptReview.objects.get(attempt=attempt)
    except AttemptReview.DoesNotExist:
        attempt_review = None
    
    recent_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).exclude(id=attempt.id).order_by("-submitted_at")[:5]
    
    context = {
        "attempt": attempt,
        "answers": answers,
        "rank_info": rank_info,
        "top_rankers": top_rankers,
        "next_rankers": next_rankers,
        "subject_stats": subject_stats,
        "attempt_review": attempt_review,
        "attempts": recent_attempts,
        "correct": attempt.correct_answers,
        "wrong": attempt.wrong_answers,
        "skipped": attempt.skipped_answers,
        "total_questions": attempt.mock_test.questions.count(),
        "percentage": attempt.percentage,
    }
    
    return render(request, "exams/result_dashboard.html", context)


# ==============================
= TEST REVIEW
# ==============================
@login_required
def test_review(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    questions = Question.objects.filter(
        mock_test=attempt.mock_test
    ).order_by('question_number').prefetch_related('options')
    
    user_answers = {
        ans.question_id: ans 
        for ans in UserAnswer.objects.filter(attempt=attempt)
    }
    
    question_data = []
    for q in questions:
        answer = user_answers.get(q.id)
        selected_option = answer.selected_option if answer else None
        correct_option = q.options.filter(is_correct=True).first()
        
        # Get review data
        try:
            review = QuestionReview.objects.get(question=q)
        except QuestionReview.DoesNotExist:
            review = None
        
        question_data.append({
            'question': q,
            'selected_option': selected_option,
            'correct_option': correct_option,
            'is_correct': answer and answer.selected_option and answer.selected_option.is_correct if answer else False,
            'user_answer': answer,
            'review': review,
        })
    
    # Get or create review session
    review_session, created = ReviewSession.objects.get_or_create(
        user=request.user,
        attempt=attempt,
        is_completed=False
    )
    
    context = {
        'attempt': attempt,
        'question_data': question_data,
        'review_session': review_session,
        'total': len(questions),
        'correct': attempt.correct_answers,
        'wrong': attempt.wrong_answers,
        'skipped': attempt.skipped_answers,
    }
    
    return render(request, "exams/test_review.html", context)


# ==============================
# SAVE QUESTION FEEDBACK
# ==============================
@login_required
def save_question_feedback(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        found_difficult = data.get('found_difficult', False)
        personal_notes = data.get('personal_notes', '')
        marked_for_review = data.get('marked_for_review', False)
        time_spent = data.get('time_spent', 0)
        
        attempt = get_object_or_404(MockTestAttempt, id=attempt_id, user=request.user)
        question = get_object_or_404(Question, id=question_id)
        
        user_answer = UserAnswer.objects.filter(
            attempt=attempt,
            question=question
        ).first()
        
        feedback, created = QuestionFeedback.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'user_answer': user_answer,
                'is_correct': user_answer.selected_option.is_correct if user_answer and user_answer.selected_option else False,
                'found_difficult': found_difficult,
                'personal_notes': personal_notes,
                'marked_for_review': marked_for_review,
                'time_spent': time_spent,
            }
        )
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})


# ==============================
# COMPLETE REVIEW SESSION
# ==============================
@login_required
def complete_review_session(request, session_id):
    session = get_object_or_404(
        ReviewSession,
        id=session_id,
        user=request.user
    )
    
    session.is_completed = True
    session.ended_at = timezone.now()
    session.save()
    
    messages.success(request, "Review session completed!")
    return redirect('exams:result_dashboard', attempt_id=session.attempt.id)


# ==============================
# RANKINGS PAGE
# ==============================
@login_required
def rankings(request):
    # Get overall top rankers
    top_overall = TopRanker.objects.select_related(
        'user', 'mock_test'
    ).order_by('-percentage')[:50]
    
    # Get popular tests
    popular_tests = MockTest.objects.filter(
        is_active=True,
        attempts__is_completed=True
    ).annotate(
        attempt_count=Count('attempts')
    ).order_by('-attempt_count')[:10]
    
    # Get user's best rank
    user_best = UserRankHistory.objects.filter(
        user=request.user
    ).order_by('rank').first()
    
    context = {
        'top_overall': top_overall,
        'popular_tests': popular_tests,
        'user_best': user_best,
    }
    
    return render(request, "exams/rankings.html", context)


# ==============================
= TEST RANKINGS
# ==============================
@login_required
def test_rankings(request, test_id):
    test = get_object_or_404(MockTest, id=test_id)
    
    # Get all ranks for this test
    ranks = TestRank.objects.filter(
        attempt__mock_test=test
    ).select_related('attempt__user').order_by('rank')[:100]
    
    # Get current user's rank
    user_rank = TestRank.objects.filter(
        attempt__mock_test=test,
        attempt__user=request.user
    ).first()
    
    # Get statistics
    stats = RankStatistics.objects.filter(mock_test=test).first()
    
    context = {
        'test': test,
        'ranks': ranks,
        'user_rank': user_rank,
        'stats': stats,
    }
    
    return render(request, "exams/test_rankings.html", context)


# ==============================
# LEADERBOARD
# ==============================
@login_required
def leaderboard(request):
    # Top users by average score
    top_users = MockTestAttempt.objects.filter(
        is_completed=True
    ).values(
        'user__id',
        'user__username'
    ).annotate(
        avg_score=Avg('percentage'),
        tests_taken=Count('id'),
        best_score=Max('percentage')
    ).order_by('-avg_score')[:100]
    
    # Add rank
    for idx, user in enumerate(top_users, 1):
        user['rank'] = idx
    
    context = {
        'top_users': top_users,
    }
    
    return render(request, "exams/leaderboard.html", context)


# ==============================
# MY ATTEMPTS HISTORY
# ==============================
@login_required
def my_attempts(request):
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test').order_by('-submitted_at')
    
    # Pagination
    paginator = Paginator(attempts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, "exams/my_attempts.html", context)


# ==============================
# MY PERFORMANCE ANALYTICS
# ==============================
@login_required
def my_performance(request):
    # Overall stats
    total_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).count()
    
    avg_score = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).aggregate(Avg('percentage'))['percentage__avg'] or 0
    
    best_score = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).order_by('-percentage').first()
    
    # Subject-wise performance
    subject_performance = []
    user_answers = UserAnswer.objects.filter(
        attempt__user=request.user,
        attempt__is_completed=True
    ).select_related('question__subject')
    
    subjects_data = {}
    for answer in user_answers:
        subject_name = answer.question.subject.name if answer.question.subject else 'General'
        if subject_name not in subjects_data:
            subjects_data[subject_name] = {'correct': 0, 'total': 0}
        
        subjects_data[subject_name]['total'] += 1
        if answer.selected_option and answer.selected_option.is_correct:
            subjects_data[subject_name]['correct'] += 1
    
    for subject, data in subjects_data.items():
        accuracy = (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
        subject_performance.append({
            'subject': subject,
            'accuracy': round(accuracy, 2),
            'attempted': data['total'],
            'correct': data['correct'],
        })
    
    # Rank history
    rank_history = UserRankHistory.objects.filter(
        user=request.user
    ).select_related('mock_test').order_by('-achieved_at')[:10]
    
    context = {
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 2),
        'best_score': best_score,
        'subject_performance': subject_performance,
        'rank_history': rank_history,
    }
    
    return render(request, "exams/my_performance.html", context)


# ==============================
# USER DASHBOARD
# ==============================
@login_required
def dashboard(request):
    # Get all completed attempts
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related("mock_test").order_by("-submitted_at")
    
    # Get in-progress attempts
    in_progress = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=False
    ).select_related("mock_test").first()
    
    # Calculate statistics
    total_tests = attempts.count()
    avg_score = attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    
    # Get best rank
    best_rank = UserRankHistory.objects.filter(
        user=request.user
    ).order_by('rank').first()
    
    # Get recent activities
    recent_activities = []
    
    # Add test completions
    for attempt in attempts[:5]:
        recent_activities.append({
            'type': 'test_completed',
            'description': f'Completed {attempt.mock_test.title}',
            'timestamp': attempt.submitted_at,
            'score': f"{attempt.percentage}%",
        })
    
    # Add rank achievements
    for rank in UserRankHistory.objects.filter(user=request.user)[:3]:
        recent_activities.append({
            'type': 'rank_achieved',
            'description': f'Achieved Rank #{rank.rank} in {rank.mock_test.title}',
            'timestamp': rank.achieved_at,
        })
    
    # Sort by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        "attempts": attempts[:5],
        "in_progress": in_progress,
        "total_tests": total_tests,
        "avg_score": round(avg_score, 2),
        "best_rank": best_rank,
        "recent_activities": recent_activities[:10],
    }
    
    return render(request, "exams/dashboard.html", context)


# ==============================
# HELPER FUNCTIONS
# ==============================
def calculate_rank(attempt):
    """Calculate and save rank for an attempt"""
    # Get all completed attempts for this test
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=attempt.mock_test,
        is_completed=True
    ).order_by('-percentage', 'submitted_at')
    
    # Find current attempt's position
    rank = 1
    for idx, a in enumerate(all_attempts, 1):
        if a.id == attempt.id:
            rank = idx
            break
    
    total = all_attempts.count()
    percentile = ((total - rank) / total) * 100 if total > 0 else 0
    
    # Save rank
    rank_info, created = TestRank.objects.update_or_create(
        attempt=attempt,
        defaults={
            'rank': rank,
            'total_participants': total,
            'percentile': round(percentile, 2)
        }
    )
    
    # Update or create top ranker cache
    if rank <= 10:
        TopRanker.objects.update_or_create(
            mock_test=attempt.mock_test,
            rank=rank,
            defaults={
                'user': attempt.user,
                'attempt': attempt,
                'percentage': attempt.percentage,
                'time_taken': attempt.time_taken or '00:00:00',
                'achieved_at': attempt.submitted_at or timezone.now()
            }
        )
    
    # Save to user history
    UserRankHistory.objects.create(
        user=attempt.user,
        mock_test=attempt.mock_test,
        attempt=attempt,
        rank=rank,
        total_participants=total,
        percentile=round(percentile, 2),
        achieved_at=attempt.submitted_at or timezone.now()
    )
    
    # Update test statistics
    stats, created = RankStatistics.objects.get_or_create(
        mock_test=attempt.mock_test
    )
    stats.update_stats()
    
    return rank_info

def create_attempt_review(attempt):
    """Create automatic review for an attempt"""
    # Get all answers
    answers = UserAnswer.objects.filter(attempt=attempt).select_related('question')
    
    # Calculate difficulty-wise performance
    easy_correct = easy_total = 0
    medium_correct = medium_total = 0
    hard_correct = hard_total = 0
    
    for answer in answers:
        # This assumes you have difficulty field on Question
        # If not, you can modify or remove this part
        pass
    
    # Create review
    review, created = AttemptReview.objects.get_or_create(
        attempt=attempt,
        defaults={
            'easy_correct': easy_correct,
            'easy_total': easy_total,
            'medium_correct': medium_correct,
            'medium_total': medium_total,
            'hard_correct': hard_correct,
            'hard_total': hard_total,
            'average_time_correct': 0,
            'average_time_incorrect': 0,
        }
    )
    
    # Generate strengths and weaknesses
    # This is a simplified version
    if attempt.percentage >= 80:
        review.strengths = "Excellent performance! You've mastered this topic."
    elif attempt.percentage >= 60:
        review.strengths = "Good performance. Keep practicing to improve further."
    else:
        review.weaknesses = "Need more practice. Focus on understanding concepts."
    
    review.save()
    
    return review
