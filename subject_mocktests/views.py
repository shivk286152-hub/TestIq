from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.db import transaction
import json
import logging

from .models import (
    Subject, Topic, MockTest, Question, Option,
    MockTestAttempt, UserAnswer
)

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def prepare_mocktest_data(mocktest):
    """
    Prepare mock test data with proper totals
    Ensures total_questions and total_marks are set
    """
    if mocktest.total_questions == 0:
        mocktest.total_questions = mocktest.questions.count()
    
    if mocktest.total_marks == 0:
        total_marks = mocktest.questions.aggregate(Sum('marks'))['marks__sum']
        mocktest.total_marks = total_marks if total_marks else mocktest.total_questions
    
    return mocktest


def prepare_tests_queryset(tests):
    """
    Prepare a queryset of tests with proper totals
    """
    result = []
    for test in tests:
        test.total_questions = test.questions.count()
        total_marks = test.questions.aggregate(Sum('marks'))['marks__sum']
        test.total_marks = total_marks if total_marks else test.total_questions
        result.append(test)
    
    return result


def calculate_question_marks(question, is_correct, mock_test):
    """
    Calculate marks for a single question based on negative marking rules
    """
    base_marks = question.marks if question.marks else 1
    
    if is_correct:
        return base_marks
    else:
        if mock_test.negative_marking_type == 'no_negative':
            return 0
        elif mock_test.negative_marking_type == 'fixed_per_question':
            return -mock_test.negative_marking_value
        elif mock_test.negative_marking_type == 'percentage_of_marks':
            return -(base_marks * mock_test.negative_marking_value / 100)
        else:
            return 0


def recalculate_attempt_stats(attempt):
    """
    Recalculate all stats for an attempt based on answers
    """
    answers = UserAnswer.objects.filter(attempt=attempt).select_related(
        'question', 'selected_option', 'question__mock_test'
    )
    
    correct = 0
    wrong = 0
    skipped = 0
    total_score = 0
    max_possible_score = 0
    
    for answer in answers:
        question = answer.question
        mock_test = question.mock_test
        
        question_marks = question.marks if question.marks else 1
        max_possible_score += question_marks
        
        if not answer.selected_option:
            skipped += 1
            continue
        
        if answer.is_correct:
            correct += 1
            total_score += question_marks
        else:
            wrong += 1
            if mock_test.negative_marking_type == 'fixed_per_question':
                total_score -= mock_test.negative_marking_value
            elif mock_test.negative_marking_type == 'percentage_of_marks':
                total_score -= (question_marks * mock_test.negative_marking_value / 100)
    
    total_score = round(total_score, 2)
    
    return {
        'correct': correct,
        'wrong': wrong,
        'skipped': skipped,
        'total_questions': max_possible_score,
        'score': total_score,
        'max_score': max_possible_score,
    }


def check_if_paid_user(user):
    """Helper function to check if user is paid"""
    if hasattr(user, 'profile') and hasattr(user.profile, 'is_paid_member'):
        return user.profile.is_paid_member
    elif user.groups.filter(name='Premium Users').exists():
        return True
    return False


def get_user_initials(user):
    """Helper function to get user initials for avatar"""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[:2].upper()
    elif user.email:
        return user.email[:2].upper()
    else:
        return user.username[:2].upper()


# ============================================
# SUBJECT & TOPIC VIEWS
# ============================================

def subject_list(request):
    """List all subjects with mock test counts"""
    subjects = Subject.objects.all().annotate(
        test_count=Count('mock_tests', filter=Q(mock_tests__is_active=True))
    ).order_by('order', 'name')
    
    return render(request, 'subject_mocktests/subject_list.html', {
        'subjects': subjects,
        'title': 'Subject Wise Mock Tests'
    })


def subject_detail(request, subject_slug):
    """Show subject details with topics and mock tests"""
    subject = get_object_or_404(Subject, slug=subject_slug)
    
    topics = subject.topics.annotate(
        test_count=Count('mock_tests', filter=Q(mock_tests__is_active=True))
    ).order_by('order', 'name')
    
    direct_tests = MockTest.objects.filter(
        subject=subject,
        topic__isnull=True,
        is_active=True
    ).order_by('-created_at')
    
    direct_tests = prepare_tests_queryset(direct_tests)
    
    return render(request, 'subject_mocktests/subject_detail.html', {
        'subject': subject,
        'topics': topics,
        'direct_tests': direct_tests,
    })


def topic_detail(request, topic_id):
    """Show topic details with mock tests"""
    topic = get_object_or_404(Topic, id=topic_id)
    
    tests = MockTest.objects.filter(
        topic=topic,
        is_active=True
    ).order_by('-created_at')
    
    tests = prepare_tests_queryset(tests)
    
    return render(request, 'subject_mocktests/topic_detail.html', {
        'topic': topic,
        'tests': tests,
    })


def mocktest_list(request, subject_slug):
    """List all mock tests for a subject"""
    subject = get_object_or_404(Subject, slug=subject_slug)
    
    topic_id = request.GET.get('topic')
    if topic_id:
        tests = MockTest.objects.filter(
            subject=subject,
            topic_id=topic_id,
            is_active=True
        )
    else:
        tests = MockTest.objects.filter(
            subject=subject,
            is_active=True
        )
    
    difficulty = request.GET.get('difficulty')
    if difficulty:
        tests = tests.filter(difficulty=difficulty)
    
    sort = request.GET.get('sort', '-created_at')
    tests = tests.order_by(sort)
    
    tests = prepare_tests_queryset(tests)
    
    paginator = Paginator(tests, 12)
    page = request.GET.get('page')
    tests_page = paginator.get_page(page)
    
    return render(request, 'subject_mocktests/mocktest_list.html', {
        'subject': subject,
        'tests': tests_page,
        'difficulties': ['Easy', 'Medium', 'Hard', 'Expert'],
    })


def mocktest_list_by_topic(request, topic_id):
    """List mock tests for a specific topic"""
    topic = get_object_or_404(Topic, id=topic_id)
    tests = MockTest.objects.filter(topic=topic, is_active=True)
    
    tests = prepare_tests_queryset(tests)
    
    return render(request, 'subject_mocktests/mocktest_list.html', {
        'topic': topic,
        'subject': topic.subject,
        'tests': tests,
    })


# ============================================
# PRETEST AND TEST START
# ============================================

@login_required
def pretest_detail(request, mocktest_id):
    """Pretest page with instructions and language selection"""
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
    
    mocktest = prepare_mocktest_data(mocktest)
    
    existing_attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    previous_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=True
    ).count()
    
    previous_best = None
    if previous_attempts > 0:
        best_attempt = MockTestAttempt.objects.filter(
            user=request.user,
            mock_test=mocktest,
            is_completed=True
        ).order_by('-score').first()
        
        if best_attempt:
            previous_best = f"{best_attempt.percentage}%"
    
    context = {
        'mocktest': mocktest,
        'existing_attempt': existing_attempt,
        'previous_attempts': previous_attempts,
        'previous_best': previous_best,
        'languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'hi', 'name': 'हिन्दी (Hindi)'},
        ]
    }
    return render(request, 'subject_mocktests/pretest_detail.html', context)


@login_required
def start_test(request, mocktest_id):
    """Start or resume a test after language selection"""
    if request.method == 'POST':
        mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
        
        terms_accepted = request.POST.get('terms_accepted')
        selected_language = request.POST.get('language')
        
        if not terms_accepted:
            messages.error(request, 'You must accept the terms to start the test.')
            return redirect('subject_mocktests:pretest_detail', mocktest_id=mocktest.id)
        
        if not selected_language:
            messages.error(request, 'Please select your preferred language.')
            return redirect('subject_mocktests:pretest_detail', mocktest_id=mocktest.id)
        
        request.session[f'subject_test_{mocktest.id}_language'] = selected_language
        
        is_paid = check_if_paid_user(request.user)
        
        attempt, created = MockTestAttempt.objects.get_or_create(
            user=request.user,
            mock_test=mocktest,
            is_completed=False,
            defaults={
                'started_at': timezone.now(),
                'language': selected_language,
                'is_paid_user': is_paid,
                'has_detailed_data': True,
                'total_marks': mocktest.total_questions,
            }
        )
        
        if not created:
            if not attempt.started_at:
                attempt.started_at = timezone.now()
            attempt.language = selected_language
            attempt.total_marks = mocktest.total_questions
            attempt.save()
        
        return redirect('subject_mocktests:attempt_test', mocktest_id=mocktest.id)
    
    return redirect('subject_mocktests:pretest_detail', mocktest_id=mocktest_id)


# ============================================
# TEST ATTEMPT VIEWS
# ============================================

@login_required
def attempt_test(request, mocktest_id):
    """Main test-taking interface"""
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    
    attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    if not attempt:
        messages.error(request, 'No active test found. Please start a new test.')
        return redirect('subject_mocktests:pretest_detail', mocktest_id=mocktest.id)
    
    language = request.session.get(f'subject_test_{mocktest.id}_language', attempt.language)
    
    duration = mocktest.duration * 60
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining_seconds = int(duration - elapsed)
    
    if remaining_seconds <= 0:
        return redirect('subject_mocktests:submit_test', mocktest_id=mocktest.id)
    
    questions = mocktest.questions.all().order_by('order', 'id')
    
    topics = {}
    for q in questions:
        topic_name = q.topic or 'General'
        if topic_name not in topics:
            topics[topic_name] = []
        topics[topic_name].append(q)
    
    return render(request, 'subject_mocktests/attempt_test.html', {
        'mocktest': mocktest,
        'questions': questions,
        'topics': topics,
        'remaining_seconds': remaining_seconds,
        'language': language,
        'attempt': attempt,
        'total_questions': questions.count(),
    })


@login_required
def ajax_question(request, mocktest_id):
    """AJAX endpoint to load question content"""
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    
    attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    if not attempt:
        return JsonResponse({'error': 'No active attempt'}, status=400)
    
    questions = mocktest.questions.all().order_by('order', 'id')
    
    q_number = request.GET.get('q', 1)
    try:
        q_number = int(q_number)
    except ValueError:
        q_number = 1
    
    q_number = max(1, min(q_number, questions.count()))
    
    if questions.count() == 0:
        return JsonResponse({'error': 'No questions found'}, status=404)
    
    question = questions[q_number - 1]
    
    saved_answers = request.session.get(f'subject_answers_{mocktest.id}', {})
    selected_option = saved_answers.get(str(question.id))
    
    return render(request, 'subject_mocktests/ajax_question.html', {
        'question': question,
        'question_number': q_number,
        'total_questions': questions.count(),
        'selected_option': selected_option,
        'language': attempt.language,
    })


@login_required
def save_answer(request):
    """Save answer to session (AJAX)"""
    if request.method == 'POST':
        try:
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    qid = int(key.replace('question_', ''))
                    question = get_object_or_404(Question, id=qid)
                    
                    answers = request.session.get(
                        f'subject_answers_{question.mock_test.id}', {}
                    )
                    
                    if value == '':
                        answers.pop(str(qid), None)
                    else:
                        answers[str(qid)] = int(value)
                    
                    request.session[f'subject_answers_{question.mock_test.id}'] = answers
            
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logger.error(f"Error saving answer: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error'}, status=400)


# ============================================
# SUBMIT TEST
# ============================================

@login_required
@transaction.atomic
def submit_test(request, mocktest_id):
    """Submit test with proper negative marking calculation"""
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    
    subject_attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).select_for_update().first()
    
    if not subject_attempt:
        messages.error(request, 'No active test found.')
        return redirect('subject_mocktests:subject_list')
    
    if subject_attempt.is_completed:
        return redirect('subject_mocktests:result_dashboard', attempt_id=subject_attempt.id)
    
    questions = mocktest.questions.all()
    session_answers = request.session.get(f'subject_answers_{mocktest.id}', {})
    
    correct = 0
    wrong = 0
    skipped = 0
    total_score = 0
    
    for question in questions:
        selected_id = session_answers.get(str(question.id))
        
        if not selected_id:
            skipped += 1
            UserAnswer.objects.create(
                attempt=subject_attempt,
                question=question
            )
        else:
            try:
                selected_option = Option.objects.get(id=selected_id)
                is_correct = selected_option.is_correct
                
                if is_correct:
                    correct += 1
                    question_marks = question.marks if question.marks else 1
                else:
                    wrong += 1
                    if mocktest.negative_marking_type == 'fixed_per_question':
                        question_marks = -mocktest.negative_marking_value
                    elif mocktest.negative_marking_type == 'percentage_of_marks':
                        question_marks = -((question.marks if question.marks else 1) * mocktest.negative_marking_value / 100)
                    else:
                        question_marks = 0
                
                total_score += question_marks
                
                UserAnswer.objects.create(
                    attempt=subject_attempt,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct
                )
            except Option.DoesNotExist:
                skipped += 1
                UserAnswer.objects.create(
                    attempt=subject_attempt,
                    question=question
                )
    
    total_score = round(total_score, 2)
    total_marks = sum(q.marks if q.marks else 1 for q in questions)
    
    subject_attempt.correct_answers = correct
    subject_attempt.wrong_answers = wrong
    subject_attempt.skipped_answers = skipped
    subject_attempt.total_marks = total_marks
    subject_attempt.raw_score = correct
    subject_attempt.score = max(0, total_score)
    subject_attempt.score_with_negative = max(0, total_score)
    subject_attempt.negative_marks_applied = max(0, correct - total_score) if total_score < correct else 0
    subject_attempt.submitted_at = timezone.now()
    subject_attempt.is_completed = True
    subject_attempt.save()
    
    request.session.pop(f'subject_answers_{mocktest.id}', None)
    
    messages.success(request, 'Test submitted successfully!')
    
    return redirect('subject_mocktests:result_dashboard', attempt_id=subject_attempt.id)


# ============================================
# RESULTS AND ANALYTICS
# ============================================

@login_required
def result_dashboard(request, attempt_id):
    """Subject mock tests result dashboard"""
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    stats = recalculate_attempt_stats(attempt)
    
    answers = attempt.answers.select_related(
        'question', 'selected_option', 'question__mock_test'
    ).all()
    
    percentage = attempt.percentage
    
    marks_obtained = stats['score']
    max_marks = stats['max_score']
    raw_marks = stats['correct'] - stats['wrong']
    negative_applied = marks_obtained - raw_marks if marks_obtained < raw_marks else 0
    
    topic_stats = []
    topic_performance = {}
    
    for answer in answers:
        question = answer.question
        topic_name = question.topic or 'General'
        mock_test = question.mock_test
        
        if topic_name not in topic_performance:
            topic_performance[topic_name] = {
                'name': topic_name,
                'total': 0,
                'correct': 0,
                'wrong': 0,
                'skipped': 0,
                'marks_obtained': 0,
                'max_marks': 0,
                'accuracy': 0
            }
        
        question_marks = question.marks if question.marks else 1
        topic_performance[topic_name]['total'] += 1
        topic_performance[topic_name]['max_marks'] += question_marks
        
        if not answer.selected_option:
            topic_performance[topic_name]['skipped'] += 1
        elif answer.is_correct:
            topic_performance[topic_name]['correct'] += 1
            topic_performance[topic_name]['marks_obtained'] += question_marks
        else:
            topic_performance[topic_name]['wrong'] += 1
            if mock_test.negative_marking_type == 'fixed_per_question':
                topic_performance[topic_name]['marks_obtained'] -= mock_test.negative_marking_value
            elif mock_test.negative_marking_type == 'percentage_of_marks':
                topic_performance[topic_name]['marks_obtained'] -= (question_marks * mock_test.negative_marking_value / 100)
    
    for topic, data in topic_performance.items():
        data['marks_obtained'] = round(data['marks_obtained'], 2)
        if data['total'] > 0:
            data['accuracy'] = round((data['correct'] / data['total']) * 100, 1)
        topic_stats.append(data)
    
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=attempt.mock_test,
        is_completed=True
    ).order_by('-score')
    
    rank = None
    for idx, att in enumerate(all_attempts, 1):
        if att.id == attempt.id:
            rank = idx
            break
    
    percentile = None
    if all_attempts.count() > 0:
        better_than = all_attempts.filter(score__lt=attempt.score).count()
        percentile = round((better_than / all_attempts.count()) * 100, 1)
    
    mock_test = attempt.mock_test
    negative_marking_info = {
        'type': mock_test.get_negative_marking_type_display(),
        'value': mock_test.negative_marking_value,
        'has_negative': mock_test.negative_marking_type != 'no_negative'
    }
    
    context = {
        'attempt': attempt,
        'answers': answers,
        'total_questions': stats['total_questions'],
        'correct': stats['correct'],
        'wrong': stats['wrong'],
        'skipped': stats['skipped'],
        'raw_marks': raw_marks,
        'marks_obtained': marks_obtained,
        'max_marks': max_marks,
        'negative_applied': abs(negative_applied),
        'percentage': percentage,
        'rank': rank,
        'percentile': percentile,
        'topic_stats': topic_stats,
        'negative_marking': negative_marking_info,
    }
    
    return render(request, 'subject_mocktests/result_dashboard.html', context)


@login_required
def subject_dashboard(request):
    """Dashboard showing all subject mock test attempts"""
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subject').order_by('-submitted_at')
    
    total_tests = attempts.count()
    avg_accuracy = 0
    best_accuracy = 0
    total_marks_obtained = 0
    total_max_marks = 0
    
    if total_tests > 0:
        total_accuracy = 0
        for attempt in attempts:
            if attempt.total_marks and attempt.total_marks > 0:
                accuracy = round((attempt.correct_answers / attempt.total_marks) * 100, 1)
                total_accuracy += accuracy
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
            
            total_marks_obtained += attempt.score
            total_max_marks += attempt.total_marks
        
        avg_accuracy = round(total_accuracy / total_tests, 1)
        total_marks_obtained = round(total_marks_obtained, 2)
    
    subject_stats = []
    subject_data = {}
    
    for attempt in attempts:
        subject_name = attempt.mock_test.subject.name
        if subject_name not in subject_data:
            subject_data[subject_name] = {
                'name': subject_name,
                'tests_taken': 0,
                'total_questions': 0,
                'correct': 0,
                'wrong': 0,
                'skipped': 0,
                'marks_obtained': 0,
                'max_marks': 0
            }
        
        subject_data[subject_name]['tests_taken'] += 1
        subject_data[subject_name]['total_questions'] += attempt.total_marks
        subject_data[subject_name]['correct'] += attempt.correct_answers
        subject_data[subject_name]['wrong'] += attempt.wrong_answers
        subject_data[subject_name]['skipped'] += attempt.skipped_answers
        subject_data[subject_name]['marks_obtained'] += attempt.score
        subject_data[subject_name]['max_marks'] += attempt.total_marks
    
    for subject, data in subject_data.items():
        if data['total_questions'] > 0:
            data['accuracy'] = round((data['correct'] / data['total_questions']) * 100, 1)
            data['avg_marks_per_test'] = round(data['marks_obtained'] / data['tests_taken'], 2)
            data['marks_obtained'] = round(data['marks_obtained'], 2)
        else:
            data['accuracy'] = 0
            data['avg_marks_per_test'] = 0
        
        subject_stats.append(data)
    
    subject_labels = [s['name'] for s in subject_stats]
    subject_accuracies = [s['accuracy'] for s in subject_stats]
    subject_marks = [s['avg_marks_per_test'] for s in subject_stats]
    
    attempts_data = []
    for attempt in attempts[:10]:
        if attempt.total_marks and attempt.total_marks > 0:
            accuracy = round((attempt.correct_answers / attempt.total_marks) * 100, 1)
        else:
            accuracy = 0
            
        attempts_data.append({
            'date': attempt.submitted_at.strftime('%Y-%m-%d'),
            'test_name': attempt.mock_test.title,
            'accuracy': accuracy,
            'marks': round(attempt.score, 2),
            'max_marks': attempt.total_marks,
        })
    
    subject_labels_json = json.dumps(subject_labels)
    subject_accuracies_json = json.dumps(subject_accuracies)
    subject_marks_json = json.dumps(subject_marks)
    attempts_json = json.dumps(attempts_data)
    
    streak = 0
    if attempts.exists():
        from datetime import date, timedelta
        attempt_dates = set(attempt.submitted_at.date() for attempt in attempts)
        today = date.today()
        current_date = today
        while current_date in attempt_dates:
            streak += 1
            current_date -= timedelta(days=1)
    
    context = {
        'attempts': attempts,
        'total_tests': total_tests,
        'avg_accuracy': avg_accuracy,
        'best_accuracy': best_accuracy,
        'total_marks_obtained': total_marks_obtained,
        'total_max_marks': total_max_marks,
        'streak': streak,
        'subject_stats': subject_stats,
        'subject_labels_json': subject_labels_json,
        'subject_accuracies_json': subject_accuracies_json,
        'subject_marks_json': subject_marks_json,
        'attempts_json': attempts_json,
    }
    
    return render(request, 'subject_mocktests/dashboard.html', context)


@login_required
def view_rankings(request, attempt_id):
    """View rankings with marks consideration"""
    current_attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    mock_test = current_attempt.mock_test
    
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=mock_test,
        is_completed=True
    ).select_related('user').order_by('-score', 'submitted_at')
    
    user_best_scores = {}
    for att in all_attempts:
        user_id = att.user.id
        if user_id not in user_best_scores or att.score > user_best_scores[user_id]['score']:
            user_best_scores[user_id] = {
                'attempt': att,
                'score': att.score
            }
    
    best_attempts_list = [data['attempt'] for data in user_best_scores.values()]
    best_attempts_list.sort(key=lambda x: x.score, reverse=True)
    
    top_score = 0
    if best_attempts_list:
        top_attempt = best_attempts_list[0]
        if top_attempt.total_marks and top_attempt.total_marks > 0:
            top_score = round(top_attempt.percentage, 1)
    
    ranked_attempts = []
    current_rank = 1
    prev_score = None
    prev_rank = 1
    
    for attempt in best_attempts_list:
        if attempt.total_marks and attempt.total_marks > 0:
            score_percentage = round(attempt.percentage, 1)
        else:
            score_percentage = 0
        
        if prev_score != attempt.score:
            rank = current_rank
        else:
            rank = prev_rank
        
        user_name = attempt.user.get_full_name() or attempt.user.username
        initials = get_user_initials(attempt.user)
        
        ranked_attempts.append({
            'rank': rank,
            'user_id': attempt.user.id,
            'user_name': user_name,
            'email': attempt.user.email,
            'initials': initials,
            'score': score_percentage,
            'marks': round(attempt.score, 2),
            'correct': attempt.correct_answers,
            'total': attempt.total_marks,
            'wrong': attempt.wrong_answers,
            'skipped': attempt.skipped_answers,
            'submitted_at': attempt.submitted_at,
            'is_current': attempt.id == current_attempt.id,
            'attempt_id': attempt.id
        })
        
        prev_score = attempt.score
        prev_rank = rank
        current_rank += 1
    
    current_user_rank = None
    for item in ranked_attempts:
        if item['is_current']:
            current_user_rank = item['rank']
            break
    
    total_attempts_count = len(ranked_attempts)
    if total_attempts_count > 0:
        avg_score = round(sum(item['score'] for item in ranked_attempts) / total_attempts_count, 1)
        avg_marks = round(sum(item['marks'] for item in ranked_attempts) / total_attempts_count, 2)
    else:
        avg_score = 0
        avg_marks = 0
    
    highest_score = ranked_attempts[0]['score'] if ranked_attempts else 0
    
    your_percentile = 100
    if total_attempts_count > 0 and current_user_rank:
        your_percentile = round(((total_attempts_count - current_user_rank) / total_attempts_count) * 100, 1)
    
    paginator = Paginator(ranked_attempts, 20)
    page_number = request.GET.get('page')
    if not page_number and current_user_rank:
        page_number = (current_user_rank - 1) // 20 + 1
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total_attempts': total_attempts_count,
        'average_score': avg_score,
        'average_marks': avg_marks,
        'highest_score': highest_score,
        'your_percentile': your_percentile,
        'your_marks': round(current_attempt.score, 2),
        'your_score': round(current_attempt.percentage, 1) if current_attempt.total_marks > 0 else 0,
    }
    
    context = {
        'mock_test': mock_test,
        'current_attempt': current_attempt,
        'rankings': page_obj,
        'stats': stats,
        'current_user_rank': current_user_rank,
        'total_pages': paginator.num_pages,
        'top_score': top_score,
    }
    
    return render(request, 'exams/rankings.html', context)


@login_required
def test_statistics(request, attempt_id):
    """Test statistics with negative marking consideration"""
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    stats = recalculate_attempt_stats(attempt)
    
    answers = attempt.answers.select_related('question', 'selected_option', 'question__mock_test').all()
    
    total_questions = stats['total_questions']
    correct = stats['correct']
    wrong = stats['wrong']
    skipped = stats['skipped']
    raw_score = stats['score']
    score_with_negative = stats['score']
    negative_applied = abs(raw_score - correct) if raw_score < correct else 0
    
    topic_performance = {}
    for answer in answers:
        question = answer.question
        mock_test = question.mock_test
        topic_name = question.topic or 'General'
        
        if topic_name not in topic_performance:
            topic_performance[topic_name] = {
                'total': 0, 'correct': 0, 'wrong': 0, 'skipped': 0,
                'marks_obtained': 0, 'max_marks': 0, 'total_time': 0
            }
        
        question_marks = question.marks if question.marks else 1
        topic_performance[topic_name]['total'] += 1
        topic_performance[topic_name]['max_marks'] += question_marks
        
        if not answer.selected_option:
            topic_performance[topic_name]['skipped'] += 1
        elif answer.is_correct:
            topic_performance[topic_name]['correct'] += 1
            topic_performance[topic_name]['marks_obtained'] += question_marks
        else:
            topic_performance[topic_name]['wrong'] += 1
            if mock_test.negative_marking_type == 'fixed_per_question':
                topic_performance[topic_name]['marks_obtained'] -= mock_test.negative_marking_value
            elif mock_test.negative_marking_type == 'percentage_of_marks':
                topic_performance[topic_name]['marks_obtained'] -= (question_marks * mock_test.negative_marking_value / 100)
    
    subject_data = []
    for name, data in topic_performance.items():
        accuracy = round((data['marks_obtained'] / data['max_marks'] * 100), 1) if data['max_marks'] > 0 else 0
        raw_accuracy = round((data['correct'] / data['total'] * 100), 1) if data['total'] > 0 else 0
        subject_data.append({
            'name': name,
            'total': data['total'],
            'correct': data['correct'],
            'wrong': data['wrong'],
            'skipped': data['skipped'],
            'raw_score': data['marks_obtained'],
            'score_with_negative': round(data['marks_obtained'], 1),
            'accuracy': accuracy,
            'raw_accuracy': raw_accuracy,
            'negative': round(abs(data['marks_obtained'] - data['correct']), 1) if data['marks_obtained'] < data['correct'] else 0
        })
    
    subject_data.sort(key=lambda x: x['score_with_negative'], reverse=True)
    
    difficulty_data = []
    difficulty_counts = {}
    
    for answer in answers:
        diff = answer.question.difficulty
        if diff not in difficulty_counts:
            difficulty_counts[diff] = {'total': 0, 'correct': 0, 'score': 0}
        difficulty_counts[diff]['total'] += 1
        if answer.is_correct:
            difficulty_counts[diff]['correct'] += 1
            difficulty_counts[diff]['score'] += 1
        elif answer.selected_option and not answer.is_correct:
            if attempt.mock_test.negative_marking_type == 'fixed_per_question':
                difficulty_counts[diff]['score'] -= attempt.mock_test.negative_marking_value
            elif attempt.mock_test.negative_marking_type == 'percentage_of_marks':
                difficulty_counts[diff]['score'] -= (1 * attempt.mock_test.negative_marking_value / 100)
    
    for diff_name, data in difficulty_counts.items():
        difficulty_data.append({
            'name': diff_name,
            'total': data['total'],
            'correct': data['correct'],
            'score': round(data['score'], 1)
        })
    
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=attempt.mock_test,
        is_completed=True
    ).select_related('user').order_by('-score')
    
    total_attempts = all_attempts.count()
    
    rank = None
    for idx, att in enumerate(all_attempts, 1):
        if att.id == attempt.id:
            rank = idx
            break
    
    percentile = None
    if rank and total_attempts > 0:
        percentile = round(((total_attempts - rank) / total_attempts) * 100, 1)
    
    global_avg = 0
    top_score = 0
    
    if total_attempts > 0:
        total_percentage = sum(att.percentage for att in all_attempts)
        global_avg = round(total_percentage / total_attempts, 1)
        top_attempt = all_attempts.first()
        if top_attempt:
            top_score = round(top_attempt.percentage, 1)
    
    user_best_scores = {}
    for att in all_attempts:
        user_id = att.user.id
        if user_id not in user_best_scores or att.score > user_best_scores[user_id]['score']:
            user_best_scores[user_id] = {
                'attempt': att,
                'score': att.score
            }
    
    best_attempts_list = [data['attempt'] for data in user_best_scores.values()]
    best_attempts_list.sort(key=lambda x: x.score, reverse=True)
    
    top_scorers = []
    for idx, att in enumerate(best_attempts_list[:10], 1):
        top_scorers.append({
            'rank': idx,
            'name': att.user.get_full_name() or att.user.username,
            'initials': (att.user.first_name[0] if att.user.first_name else att.user.username[0]).upper(),
            'score': round(att.percentage, 1),
            'correct': att.correct_answers,
            'total': att.total_marks,
            'is_current': att.id == attempt.id
        })
    
    insights = []
    if subject_data:
        strongest = subject_data[0]
        insights.append(f"Strongest: {strongest['name']} ({strongest['accuracy']}%)")
        weakest = subject_data[-1]
        if weakest['accuracy'] < 60:
            insights.append(f"Focus on: {weakest['name']} ({weakest['accuracy']}%)")
    
    if attempt.score < stats['max_score'] * 0.3:
        insights.append("📚 Practice more to improve your score.")
    
    if attempt.wrong_answers > 0 and attempt.mock_test.negative_marking_type != 'no_negative':
        marks_lost = abs(attempt.score - correct)
        insights.append(f"⚠️ You lost {round(marks_lost, 2)} marks due to negative marking.")
    
    if attempt.percentage > global_avg:
        insights.append(f"Above global average by {round(attempt.percentage - global_avg, 1)}%")
    
    distribution_ranges = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%']
    distribution_data = [0, 0, 0, 0, 0]
    
    for att in all_attempts:
        if att.total_marks > 0:
            pct = (att.correct_answers / att.total_marks) * 100
            if pct <= 20:
                distribution_data[0] += 1
            elif pct <= 40:
                distribution_data[1] += 1
            elif pct <= 60:
                distribution_data[2] += 1
            elif pct <= 80:
                distribution_data[3] += 1
            else:
                distribution_data[4] += 1
    
    chart_data = {
        'subject_names': [s['name'] for s in subject_data],
        'subject_scores': [s['score_with_negative'] for s in subject_data],
        'difficulty_labels': [d['name'] for d in difficulty_data],
        'difficulty_scores': [d['score'] for d in difficulty_data],
        'distribution_ranges': distribution_ranges,
        'distribution_data': distribution_data,
    }
    
    context = {
        'attempt': attempt,
        'total_questions': total_questions,
        'correct': correct,
        'wrong': wrong,
        'skipped': skipped,
        'raw_score': raw_score,
        'score_with_negative': score_with_negative,
        'negative_applied': negative_applied,
        'percentage_raw': attempt.percentage,
        'percentage_with_negative': attempt.percentage,
        'subject_data': subject_data,
        'difficulty_data': difficulty_data,
        'top_scorers': top_scorers,
        'rank': rank,
        'percentile': percentile,
        'total_attempts': total_attempts,
        'global_avg': global_avg,
        'top_score': top_score,
        'insights': insights,
        'chart_data_json': json.dumps(chart_data),
    }
    
    return render(request, 'exams/test_statistics.html', context)


@login_required
def detailed_analysis(request, attempt_id):
    """Detailed analysis with question-wise negative marking display"""
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    selected_language = request.GET.get('lang', attempt.language)
    mock_test = attempt.mock_test
    
    answers = attempt.answers.select_related(
        'question',
        'selected_option',
        'question__mock_test'
    ).prefetch_related('question__options').all()
    
    questions_data = []
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    total_marks_obtained = 0
    
    for index, answer in enumerate(answers, start=1):
        question = answer.question
        selected_option = answer.selected_option
        
        options = question.options.all().order_by('order')
        
        is_correct = False
        marks_obtained = 0
        correct_option = None
        
        question_marks = question.marks if question.marks else 1
        
        if selected_option:
            is_correct = selected_option.is_correct
            if is_correct:
                correct_count += 1
                marks_obtained = question_marks
            else:
                wrong_count += 1
                if mock_test.negative_marking_type == 'fixed_per_question':
                    marks_obtained = -mock_test.negative_marking_value
                elif mock_test.negative_marking_type == 'percentage_of_marks':
                    marks_obtained = -(question_marks * mock_test.negative_marking_value / 100)
                else:
                    marks_obtained = 0
            correct_option = question.options.filter(is_correct=True).first()
        else:
            skipped_count += 1
            marks_obtained = 0
        
        total_marks_obtained += marks_obtained
        
        options_data = []
        for opt_index, option in enumerate(options, start=1):
            option_text = option.get_text(selected_language)
            
            options_data.append({
                'id': option.id,
                'text': option_text,
                'is_correct': option.is_correct,
                'is_selected': selected_option and selected_option.id == option.id,
                'letter': chr(64 + opt_index)
            })
        
        question_text = question.get_question_text(selected_language)
        subject_name = question.topic or question.mock_test.subject.name or 'General'
        explanation = question.get_explanation_text(selected_language)
        
        selected_option_text = 'Not Answered'
        if selected_option:
            selected_option_text = selected_option.get_text(selected_language)
        
        correct_option_text = 'No correct option found'
        if correct_option:
            correct_option_text = correct_option.get_text(selected_language)
        
        question_data = {
            'id': question.id,
            'question_number': index,
            'text': question_text,
            'subject': subject_name,
            'topic': question.topic or 'General',
            'difficulty': question.difficulty,
            'explanation': explanation,
            'options': options_data,
            'selected_option_text': selected_option_text,
            'correct_option_text': correct_option_text,
            'is_correct': is_correct,
            'is_answered': selected_option is not None,
            'marks_obtained': round(marks_obtained, 2),
            'max_marks': question_marks,
        }
        questions_data.append(question_data)
    
    total_questions = len(questions_data)
    accuracy = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0
    total_marks_obtained = round(total_marks_obtained, 2)
    max_possible_marks = sum(q['max_marks'] for q in questions_data)
    
    subject_stats = {}
    for q in questions_data:
        subject = q['subject']
        if subject not in subject_stats:
            subject_stats[subject] = {
                'name': subject,
                'total': 0,
                'correct': 0,
                'wrong': 0,
                'skipped': 0,
                'marks_obtained': 0,
                'max_marks': 0
            }
        subject_stats[subject]['total'] += 1
        subject_stats[subject]['max_marks'] += q['max_marks']
        if q['is_correct']:
            subject_stats[subject]['correct'] += 1
            subject_stats[subject]['marks_obtained'] += q['max_marks']
        elif q['is_answered']:
            subject_stats[subject]['wrong'] += 1
            subject_stats[subject]['marks_obtained'] += q['marks_obtained']
        else:
            subject_stats[subject]['skipped'] += 1
    
    for subject, stats in subject_stats.items():
        if stats['total'] > 0:
            stats['accuracy'] = round((stats['correct'] / stats['total'] * 100), 1)
            stats['score_percentage'] = round((stats['marks_obtained'] / stats['max_marks'] * 100), 1) if stats['max_marks'] > 0 else 0
            stats['marks_obtained'] = round(stats['marks_obtained'], 2)
        else:
            stats['accuracy'] = 0
            stats['score_percentage'] = 0
    
    if not attempt.has_detailed_data:
        return render(request, 'exams/detailed_analysis_unavailable.html', {
            'attempt': attempt,
            'message': 'Detailed answers are no longer available for free users after 7 days. Upgrade to paid to keep your detailed history!'
        })
    
    negative_marking_info = {
        'type': mock_test.get_negative_marking_type_display(),
        'value': mock_test.negative_marking_value,
        'has_negative': mock_test.negative_marking_type != 'no_negative'
    }
    
    context = {
        'attempt': attempt,
        'questions_data': questions_data,
        'total_questions': total_questions,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'skipped_count': skipped_count,
        'accuracy': accuracy,
        'marks_obtained': total_marks_obtained,
        'max_marks': max_possible_marks,
        'subject_stats': subject_stats,
        'selected_language': selected_language,
        'negative_marking': negative_marking_info,
        'languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'hi', 'name': 'हिन्दी (Hindi)'},
        ]
    }
    
    return render(request, 'exams/detailed_analysis.html', context)