from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
<<<<<<< HEAD
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib import messages
import json

from .models import (
    ExamCategory, SubCategory, MockTest, Question, Subject,
    Option, MockTestAttempt, UserAnswer, TestRank, TopRanker,
    UserRankHistory, RankStatistics, QuestionReview, AttemptReview,
    QuestionFeedback, ReviewSession
=======
from django.core.paginator import Paginator
from django.db.models import Count, Avg, F, Q

from .models import (
    ExamCategory,
    SubCategory,
    MockTest,
    Question,
    Subject,
    MockTestAttempt,
    UserAnswer
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
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
<<<<<<< HEAD
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
=======
        "tests": tests,
    })

def mocktest_detail(request, pk):
    mock_test = get_object_or_404(MockTest, id=pk)

    questions = Question.objects.filter(mock_test=mock_test)
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)

    return render(request, "exams/mocktest_detail.html", {
        "mock_test": mock_test,
        "questions": questions,
<<<<<<< HEAD
        "total_attempts": total_attempts,
        "avg_score": round(avg_score, 2),
        "user_attempt": user_attempt,
        "top_rankers": top_rankers,
=======
    })
# ==============================
# START TEST (CREATE ATTEMPT)
# ==============================
@login_required
def start_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)

    MockTestAttempt.objects.get_or_create(
        user=request.user,
        mock_test=mocktest,
        is_completed=False,
        defaults={"started_at": timezone.now()}
    )

    return redirect("exams:attempt_test", mocktest_id=mocktest.id)


# ==============================
# ATTEMPT TEST (SERVER TIMER)
# ==============================
@login_required
def attempt_test(request, mocktest_id):

    mocktest = get_object_or_404(MockTest, id=mocktest_id)

    attempt, created = MockTestAttempt.objects.get_or_create(
        user=request.user,
        mock_test=mocktest,
        is_completed=False,
        defaults={"started_at": timezone.now()}
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

    return render(request, "exams/attempt_test.html", {
        "mocktest": mocktest,
        "questions": questions,
        "subjects": subjects,
        "remaining_seconds": remaining_seconds,
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
    })


# ==============================
<<<<<<< HEAD
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
=======
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
# SAVE ANSWER (SESSION)
# ==============================
@login_required
def save_answer(request):
<<<<<<< HEAD
    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith("question_"):
                qid = int(key.replace("question_", ""))
                question = get_object_or_404(Question, id=qid)
                
                answers = request.session.get(
                    f"answers_{question.mock_test.id}", {}
                )
                
=======

    if request.method == "POST":

        for key, value in request.POST.items():
            if key.startswith("question_"):

                qid = int(key.replace("question_", ""))
                question = get_object_or_404(Question, id=qid)

                answers = request.session.get(
                    f"answers_{question.mock_test.id}", {}
                )

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
                if value == "":
                    answers.pop(str(qid), None)
                else:
                    answers[str(qid)] = int(value)
<<<<<<< HEAD
                
                request.session[f"answers_{question.mock_test.id}"] = answers
                
        return JsonResponse({"status": "ok"})
    
=======

                request.session[
                    f"answers_{question.mock_test.id}"
                ] = answers

        return JsonResponse({"status": "ok"})

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
    return JsonResponse({"status": "error"})


# ==============================
# AJAX QUESTION LOAD
# ==============================
@login_required
def ajax_question(request, mocktest_id):
<<<<<<< HEAD
=======

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    questions = Question.objects.filter(
        mock_test=mocktest
    ).prefetch_related("options").order_by("id")
<<<<<<< HEAD
    
    q_number = request.GET.get("q", 1)
    
=======

    q_number = request.GET.get("q")

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
    try:
        q_number = int(q_number)
    except:
        q_number = 1
<<<<<<< HEAD
    
    q_number = max(1, min(q_number, questions.count()))
    question = questions[q_number - 1]
    
    saved_answers = request.session.get(f"answers_{mocktest.id}", {})
    selected_option = saved_answers.get(str(question.id))
    
    # Get question review data if exists
    try:
        review = QuestionReview.objects.get(question=question)
    except QuestionReview.DoesNotExist:
        review = None
    
=======

    q_number = max(1, min(q_number, questions.count()))
    question = questions[q_number - 1]

    saved_answers = request.session.get(
        f"answers_{mocktest.id}", {}
    )

    selected_option = saved_answers.get(str(question.id))

>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
    return render(request, "exams/ajax_question.html", {
        "question": question,
        "question_number": q_number,
        "total_questions": questions.count(),
        "selected_option": selected_option,
<<<<<<< HEAD
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
=======
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
        return redirect("exams:home")

    # Prevent double submit
    if attempt.is_completed:
        return redirect("exams:result_dashboard", attempt_id=attempt.id)

    attempt.submitted_at = timezone.now()
    attempt.is_completed = True

    questions = Question.objects.filter(mock_test=mocktest)
    session_answers = request.session.get(
        f"answers_{mocktest.id}", {}
    )

    correct = 0
    wrong = 0
    skipped = 0

    for question in questions:

        selected_id = session_answers.get(str(question.id))

        if not selected_id:
            skipped += 1
            UserAnswer.objects.create(
                attempt=attempt,
                question=question
            )
            continue

        ua = UserAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_option_id=selected_id
        )

        if ua.selected_option.is_correct:
            correct += 1
        else:
            wrong += 1

    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped_answers = skipped
    attempt.total_marks = questions.count()
    attempt.score = correct - (wrong * 0.25)

    attempt.save()

    request.session.pop(f"answers_{mocktest.id}", None)

    return redirect(
        "exams:result_dashboard",
        attempt_id=attempt.id
    )


# ==============================
# RESULT DASHBOARD
# ==============================
@login_required
def result_dashboard(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user
    )

    answers = attempt.answers.select_related(
        "question",
        "selected_option"
    ).prefetch_related("question__options")

    # Basic calculations
    total_questions = answers.count()
    correct = answers.filter(
        selected_option__is_correct=True
    ).count()  # This works if selected_option has is_correct field
    
    # Or calculate manually if the above doesn't work
    # correct = 0
    # for answer in answers:
    #     if answer.selected_option and answer.selected_option.is_correct:
    #         correct += 1
    
    wrong = total_questions - correct
    
    # Calculate percentage
    percentage = 0
    if total_questions > 0:
        percentage = round((correct / total_questions) * 100, 1)
    
    # Simple subject stats (if you have subjects)
    subject_stats = []
    # You can add subject stats logic here if needed
    
    recent_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).exclude(id=attempt_id).order_by("-submitted_at")[:5]

    return render(request, "exams/result_dashboard.html", {
        "attempt": attempt,
        "answers": answers,
        "attempts": recent_attempts,
        "total_questions": total_questions,
        "correct": correct,
        "wrong": wrong,
        "percentage": percentage,
        "subject_stats": subject_stats,  # Pass empty list if not used
    })


   # Add this to your existing views.py

@login_required
def view_rankings(request, attempt_id):
    """
    View rankings for a specific mock test attempt
    """
    # Get the current user's attempt
    current_attempt = get_object_or_404(
        MockTestAttempt, 
        id=attempt_id, 
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
        user=request.user,
        is_completed=True
    )
    
<<<<<<< HEAD
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
=======
    mock_test = current_attempt.mock_test
    
    # Get all completed attempts for this mock test
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=mock_test,
        is_completed=True
    ).select_related('user').annotate(
        total_questions=F('total_marks'),  # Using total_marks as total questions
        score_percentage=(
            F('correct_answers') * 100.0 / F('total_marks')
        )  # Calculate percentage
    ).order_by('-score_percentage', 'submitted_at')  # Sort by score, then submission time
    
    # Calculate ranks and prepare data
    ranked_attempts = []
    current_rank = 1
    prev_score = None
    prev_rank = 1
    
    for attempt in all_attempts:
        # Handle ties (same score gets same rank)
        if prev_score != attempt.score_percentage:
            rank = current_rank
        else:
            rank = prev_rank
        
        # Get user's full name or username
        user_name = attempt.user.get_full_name()
        if not user_name:
            user_name = attempt.user.username
        
        # Get user initials for avatar
        initials = get_user_initials(attempt.user)
        
        ranked_attempts.append({
            'rank': rank,
            'user_id': attempt.user.id,
            'user_name': user_name,
            'email': attempt.user.email,
            'initials': initials,
            'score': round(attempt.score_percentage, 1) if attempt.score_percentage else 0,
            'correct': attempt.correct_answers,
            'total': attempt.total_marks,
            'wrong': attempt.wrong_answers,
            'skipped': attempt.skipped_answers,
            'submitted_at': attempt.submitted_at,
            'is_current': attempt.id == current_attempt.id,
            'attempt_id': attempt.id
        })
        
        prev_score = attempt.score_percentage
        prev_rank = rank
        current_rank += 1
    
    # Find current user's rank
    current_user_rank = None
    for item in ranked_attempts:
        if item['is_current']:
            current_user_rank = item['rank']
            break
    
    # Calculate statistics
    total_attempts = len(ranked_attempts)
    
    # Calculate average score
    avg_score = 0
    if total_attempts > 0:
        total_score_sum = sum(item['score'] for item in ranked_attempts)
        avg_score = round(total_score_sum / total_attempts, 1)
    
    # Get highest score
    highest_score = ranked_attempts[0]['score'] if ranked_attempts else 0
    
    # Calculate percentile
    your_percentile = calculate_percentile(ranked_attempts, current_attempt.id)
    
    # Pagination
    paginator = Paginator(ranked_attempts, 20)  # Show 20 rankings per page
    page_number = request.GET.get('page')
    
    # If viewing current user's rank and no page specified, go to that page
    if not page_number and current_user_rank:
        page_number = (current_user_rank - 1) // 20 + 1
    
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total_attempts': total_attempts,
        'average_score': avg_score,
        'highest_score': highest_score,
        'your_percentile': your_percentile,
    }
    
    context = {
        'mock_test': mock_test,
        'current_attempt': current_attempt,
        'rankings': page_obj,
        'stats': stats,
        'current_user_rank': current_user_rank,
        'total_pages': paginator.num_pages,
    }
    
    return render(request, 'exams/rankings.html', context)


def get_user_initials(user):
    """Helper function to get user initials for avatar"""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[:2].upper()
    else:
        return user.username[:2].upper()


def calculate_percentile(ranked_attempts, current_attempt_id):
    """Calculate user's percentile rank"""
    if not ranked_attempts:
        return 100
    
    total = len(ranked_attempts)
    
    # Find current attempt's score
    current_score = None
    for item in ranked_attempts:
        if item['attempt_id'] == current_attempt_id:
            current_score = item['score']
            break
    
    if current_score is None:
        return 100
    
    # Count attempts with lower score
    lower_count = sum(1 for item in ranked_attempts if item['score'] < current_score)
    
    # Calculate percentile (number of people below you / total * 100)
    percentile = (lower_count / total) * 100
    
    return round(percentile, 1)  

# Add this to your existing views.py

# views.py - Add this function

@login_required
def detailed_analysis(request, attempt_id):
    """
    Detailed analysis showing all questions with filtering by correct/wrong
    """
    try:
        # Get the attempt with error handling
        attempt = get_object_or_404(
            MockTestAttempt, 
            id=attempt_id, 
            user=request.user,
            is_completed=True
        )
        
        # Get all answers with related data
        answers = attempt.answers.select_related(
            'question',
            'selected_option',
            'question__subject'
        ).prefetch_related('question__options').all()
        
        # Check if answers exist
        if not answers.exists():
            # Handle case with no answers
            return render(request, 'exams/detailed_analysis.html', {
                'attempt': attempt,
                'questions_data': [],
                'total_questions': 0,
                'correct_count': 0,
                'wrong_count': 0,
                'skipped_count': 0,
                'accuracy': 0,
                'subject_stats': {},
                'error_message': 'No answers found for this attempt.'
            })
        
        # Prepare questions data with detailed information
        questions_data = []
        correct_count = 0
        wrong_count = 0
        
        for index, answer in enumerate(answers, start=1):
            question = answer.question
            selected_option = answer.selected_option
            
            # Get all options for this question
            options = question.options.all().order_by('id')
            
            # Determine if answer is correct
            is_correct = False
            correct_option = None
            
            if selected_option:
                is_correct = getattr(selected_option, 'is_correct', False)
                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1
                    
                # Find the correct option for explanation
                correct_option = question.options.filter(is_correct=True).first()
            
            # Prepare option details with safe attribute access
            options_data = []
            for opt_index, option in enumerate(options, start=1):
                option_dict = {
                    'id': option.id,
                    'text': getattr(option, 'text', ''),
                    'is_correct': getattr(option, 'is_correct', False),
                    'is_selected': selected_option and selected_option.id == option.id,
                    'is_wrong_selection': selected_option and selected_option.id == option.id and not getattr(option, 'is_correct', False),
                    'letter': chr(64 + opt_index)  # A, B, C, D
                }
                options_data.append(option_dict)
            
            # Get subject name safely
            subject_name = 'General'
            if hasattr(question, 'subject') and question.subject:
                subject_name = getattr(question.subject, 'name', 'General')
            
            # Get difficulty safely
            difficulty = 'Medium'
            if hasattr(question, 'difficulty'):
                difficulty = question.difficulty
            
            # Get explanation safely
            explanation = 'No explanation available.'
            if hasattr(question, 'explanation') and question.explanation:
                explanation = question.explanation
            
            # Get selected option text safely
            selected_option_text = 'Not Answered'
            if selected_option and hasattr(selected_option, 'text'):
                selected_option_text = selected_option.text
            
            # Get correct option text safely
            correct_option_text = 'No correct option found'
            if correct_option and hasattr(correct_option, 'text'):
                correct_option_text = correct_option.text
            
            question_data = {
                'id': question.id,
                'question_number': index,
                'text': getattr(question, 'text', ''),
                'subject': subject_name,
                'difficulty': difficulty,
                'explanation': explanation,
                'options': options_data,
                'selected_option': selected_option,
                'selected_option_text': selected_option_text,
                'is_correct': is_correct,
                'is_answered': selected_option is not None,
                'correct_option': correct_option,
                'correct_option_text': correct_option_text,
            }
            questions_data.append(question_data)
        
        # Calculate statistics
        total_questions = len(questions_data)
        answered_count = correct_count + wrong_count
        skipped_count = total_questions - answered_count
        
        # Calculate accuracy safely
        accuracy = 0
        if total_questions > 0:
            accuracy = round((correct_count / total_questions * 100), 1)
        
        # Subject-wise performance
        subject_stats = {}
        for q in questions_data:
            subject = q['subject']
            if subject not in subject_stats:
                subject_stats[subject] = {
                    'total': 0,
                    'correct': 0,
                    'wrong': 0,
                    'skipped': 0
                }
            subject_stats[subject]['total'] += 1
            if q['is_correct']:
                subject_stats[subject]['correct'] += 1
            elif q['is_answered']:
                subject_stats[subject]['wrong'] += 1
            else:
                subject_stats[subject]['skipped'] += 1
        
        # Calculate subject percentages
        for subject, stats in subject_stats.items():
            if stats['total'] > 0:
                stats['percentage'] = round((stats['correct'] / stats['total'] * 100), 1)
            else:
                stats['percentage'] = 0
        
        context = {
            'attempt': attempt,
            'questions_data': questions_data,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'skipped_count': skipped_count,
            'accuracy': accuracy,
            'subject_stats': subject_stats,
        }
        
        return render(request, 'exams/detailed_analysis.html', context)
    
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in detailed_analysis for attempt {attempt_id}: {str(e)}")
        
        # Return a friendly error page
        return render(request, 'exams/error.html', {
            'error_message': 'Unable to load detailed analysis. Please try again later.',
            'attempt_id': attempt_id
        })
        
# views.py - Update your dashboard view

@login_required
def dashboard(request):
    """
    User dashboard showing all test attempts and statistics
    """
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
    # Calculate overall statistics
    total_tests = attempts.count()
    
    # Calculate average score
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
    
    # Get subject-wise performance (you can enhance this based on your data)
    subject_stats = []  # Add your subject stats logic here
    
    context = {
        'attempts': attempts,
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'subject_stats': subject_stats,
    }
    
    return render(request, 'exams/dashboard.html', context)        
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
