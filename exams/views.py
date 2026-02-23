from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Avg, F, Q, Case, When, IntegerField
from django.contrib import messages
import json

from .models import (
    ExamCategory,
    SubCategory,
    MockTest,
    Question,
    Subject,
    MockTestAttempt,
    UserAnswer,
    Testimonial 
)
from .forms import TestimonialForm


# ==============================
# HOME
# ==============================
# views.py - Update your home view
def home(request):
    try:
        categories = ExamCategory.objects.all()
        mock_tests = MockTest.objects.filter(is_active=True)[:5]
        
        # Get active testimonials (admin controlled)
        testimonials = Testimonial.objects.filter(
            is_active=True
        ).select_related('user')[:10]  # Limit to 10 testimonials
        
        # Check if current user has already submitted a testimonial
        user_testimonial = None
        if request.user.is_authenticated:
            user_testimonial = Testimonial.objects.filter(
                user=request.user
            ).first()
        
        # Add user progress for each category (optional)
        if request.user.is_authenticated:
            for cat in categories:
                # Calculate user progress for this category
                # You can implement this based on your logic
                cat.user_progress = 65  # Placeholder

        return render(request, "exams/home.html", {
            "categories": categories,
            "mock_tests": mock_tests,
            "testimonials": testimonials,
            "user_testimonial": user_testimonial,
            "site_name": "TestIQ",
            "hero_title": "Master Your Competitive Exams",
            "hero_desc": "Practice. Analyze. Improve. Succeed."
        })
    except Exception as e:
        import traceback
        print("="*50)
        print("ERROR in home view:")
        print(traceback.format_exc())
        print("="*50)
        from django.http import HttpResponse
        return HttpResponse(f"Error: {str(e)}", status=500)




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
    tests = MockTest.objects.filter(subcategory=subcategory)

    return render(request, "exams/mocktest_list.html", {
        "subcategory": subcategory,
        "tests": tests,
    })

def mocktest_detail(request, pk):
    mock_test = get_object_or_404(MockTest, id=pk)

    questions = Question.objects.filter(mock_test=mock_test)

    return render(request, "exams/mocktest_detail.html", {
        "mock_test": mock_test,
        "questions": questions,
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

                request.session[
                    f"answers_{question.mock_test.id}"
                ] = answers

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

    q_number = request.GET.get("q")

    try:
        q_number = int(q_number)
    except:
        q_number = 1

    q_number = max(1, min(q_number, questions.count()))
    question = questions[q_number - 1]

    saved_answers = request.session.get(
        f"answers_{mocktest.id}", {}
    )

    selected_option = saved_answers.get(str(question.id))

    return render(request, "exams/ajax_question.html", {
        "question": question,
        "question_number": q_number,
        "total_questions": questions.count(),
        "selected_option": selected_option,
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
        user=request.user,
        is_completed=True
    )
    
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

# views.py - Update your detailed_analysis function
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
        
        # Get user's language preference
        user_language = request.session.get('django_language', 'en')
        
        # Get all answers with related data
        answers = attempt.answers.select_related(
            'question',
            'selected_option',
            'question__subject'
        ).prefetch_related('question__options').all()
        
        # Check if answers exist
        if not answers.exists():
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
        skipped_count = 0
        
        for index, answer in enumerate(answers, start=1):
            question = answer.question
            selected_option = answer.selected_option
            
            # Get all options for this question
            options = question.options.all().order_by('order', 'id')
            
            # Determine if answer is correct
            is_correct = False
            correct_option = None
            
            if selected_option:
                # Check if selected option is correct
                is_correct = selected_option.is_correct
                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1
                    
                # Find the correct option for explanation
                correct_option = question.options.filter(is_correct=True).first()
            else:
                skipped_count += 1
            
            # Prepare option details - FIXED: Use text_en/text_hi based on language
            options_data = []
            for opt_index, option in enumerate(options, start=1):
                # Get option text based on user's language preference
                if user_language == 'hi' and hasattr(option, 'text_hi') and option.text_hi:
                    option_text = option.text_hi
                else:
                    # Default to English or fallback to any available text
                    option_text = option.text_en if hasattr(option, 'text_en') and option.text_en else f"Option {opt_index}"
                
                option_dict = {
                    'id': option.id,
                    'text': option_text,
                    'is_correct': option.is_correct,
                    'is_selected': selected_option and selected_option.id == option.id,
                    'letter': chr(64 + opt_index)  # A, B, C, D
                }
                options_data.append(option_dict)
            
            # Get question text based on language preference
            question_text = "Question text not available"
            if user_language == 'hi' and hasattr(question, 'question_hi') and question.question_hi:
                question_text = question.question_hi
            else:
                question_text = question.question_en if hasattr(question, 'question_en') and question.question_en else "Question text not available"
            
            # Get subject name
            subject_name = question.subject.name if question.subject else 'General'
            
            # Get difficulty
            difficulty = getattr(question, 'difficulty', 'Medium')
            
            # Get explanation
            explanation = getattr(question, 'explanation', 'No explanation available.')
            
            # Get selected option text based on language
            selected_option_text = 'Not Answered'
            if selected_option:
                if user_language == 'hi' and hasattr(selected_option, 'text_hi') and selected_option.text_hi:
                    selected_option_text = selected_option.text_hi
                else:
                    selected_option_text = selected_option.text_en if hasattr(selected_option, 'text_en') and selected_option.text_en else "Selected option"
            
            # Get correct option text based on language
            correct_option_text = 'No correct option found'
            if correct_option:
                if user_language == 'hi' and hasattr(correct_option, 'text_hi') and correct_option.text_hi:
                    correct_option_text = correct_option.text_hi
                else:
                    correct_option_text = correct_option.text_en if hasattr(correct_option, 'text_en') and correct_option.text_en else "Correct option"
            
            # Get topic
            topic = getattr(question, 'topic', '')
            
            question_data = {
                'id': question.id,
                'question_number': index,
                'text': question_text,
                'subject': subject_name,
                'topic': topic,
                'difficulty': difficulty,
                'explanation': explanation,
                'options': options_data,
                'selected_option_text': selected_option_text,
                'correct_option_text': correct_option_text,
                'is_correct': is_correct,
                'is_answered': selected_option is not None,
            }
            questions_data.append(question_data)
        
        # Calculate statistics
        total_questions = len(questions_data)
        
        # Calculate accuracy
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
        import logging
        import traceback
        
        logger = logging.getLogger(__name__)
        logger.error(f"Error in detailed_analysis for attempt {attempt_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a friendly error page
        return render(request, 'exams/error.html', {
            'error_message': f'Unable to load detailed analysis: {str(e)}',
            'attempt_id': attempt_id
        })
        
@login_required
def dashboard(request):
    """
    User dashboard showing all test attempts, statistics, and performance charts.
    """
    # Get all completed attempts
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')

    # Get user's testimonial if exists
    try:
        user_testimonial = Testimonial.objects.filter(user=request.user).first()
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
    # Get all answers from the user's completed attempts
    user_answers = UserAnswer.objects.filter(
        attempt__user=request.user,
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
        # Avoid division by zero (shouldn't happen, but safe)
        percentage = (stat['correct'] / stat['total'] * 100) if stat['total'] > 0 else 0
        subject_scores.append(round(percentage, 1))

    # ----- Attempts data for line chart (chronological order) -----
    attempts_chrono = attempts.order_by('submitted_at')  # oldest first
    attempts_data = []
    for attempt in attempts_chrono:
        if attempt.total_marks > 0:
            score_percentage = (attempt.correct_answers / attempt.total_marks) * 100
        else:
            score_percentage = 0

        attempts_data.append({
            'date': attempt.submitted_at.strftime('%Y-%m-%d'),  # you can also include time if needed
            'test_name': attempt.mock_test.title,
            'score': round(score_percentage, 1),
        })

    # Convert to JSON strings for safe use in JavaScript
    import json
    subject_labels_json = json.dumps(subject_labels)
    subject_scores_json = json.dumps(subject_scores)
    attempts_json = json.dumps(attempts_data)

    context = {
        'attempts': attempts,
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'subject_stats': subject_stats_qs,          # if you still want the original list
        'user_testimonial': user_testimonial,
        # New keys for charts
        'subject_labels_json': subject_labels_json,
        'subject_scores_json': subject_scores_json,
        'attempts_json': attempts_json,
    }

    return render(request, 'exams/dashboard.html', context)

# ==============================
# TESTIMONIAL VIEWS
# ==============================
@login_required
def submit_testimonial(request):
    """Allow users to submit testimonials"""
    # Check if user already has a testimonial
    existing = Testimonial.objects.filter(user=request.user).first()
    if existing:
        messages.warning(request, 'You have already submitted a testimonial. You can edit it from your dashboard.')
        return redirect('exams:dashboard')
    
    if request.method == 'POST':
        form = TestimonialForm(request.POST)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.user = request.user
            testimonial.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Thank you for your testimonial! It will be reviewed by our team.'
                })
            
            messages.success(request, 'Thank you for your testimonial! It will be reviewed by our team.')
            return redirect('exams:dashboard')
    else:
        form = TestimonialForm()
    
    return render(request, 'exams/submit_testimonial.html', {'form': form})

@login_required
def edit_testimonial(request, testimonial_id):
    """Allow users to edit their own testimonials"""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id, user=request.user)
    
    if request.method == 'POST':
        form = TestimonialForm(request.POST, instance=testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your testimonial has been updated!')
            return redirect('exams:dashboard')
    else:
        form = TestimonialForm(instance=testimonial)
    
    return render(request, 'exams/edit_testimonial.html', {
        'form': form, 
        'testimonial': testimonial
    })

@login_required
def delete_testimonial(request, testimonial_id):
    """Allow users to delete their own testimonials"""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id, user=request.user)
    
    if request.method == 'POST':
        testimonial.delete()
        messages.success(request, 'Your testimonial has been deleted.')
        return redirect('exams:dashboard')
    
    return render(request, 'exams/confirm_delete_testimonial.html', {
        'testimonial': testimonial
    })
