from django.shortcuts import render,redirect
from django.shortcuts import render, get_object_or_404
from .models import ExamCategory, SubCategory, MockTest, Question, Subject,MockTestAttempt
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MockTest, MockTestAttempt

from django.utils import timezone
from .models import Question, UserAnswer



# Home page
def home(request):
    categories = ExamCategory.objects.all()
    mock_tests = MockTest.objects.filter(is_active=True)[:5]

    return render(request, "exams/home.html", {
        "categories": categories,
        "mock_tests": mock_tests,
        "site_name": "TestIQ",
        "hero_title": "Where Preparation , Meets success”,
        "hero_desc": "Take real-style mock tests, track your progress, and move one step closer to your dream exam",
        })


# Category detail → show subcategories
def category_detail(request, slug):
    category = get_object_or_404(ExamCategory, slug=slug)
    subcategories = SubCategory.objects.filter(category=category)
    return render(request, "exams/subcategory_list.html", {
        "category": category,
        "subcategories": subcategories,
        
    })

# Subcategory → show mock tests
def subcategory_detail(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    tests = MockTest.objects.filter(subcategory=subcategory)

    return render(request, "exams/mocktest_list.html", {
        "subcategory": subcategory,
        "tests": tests,
        
        
    })



def mocktest_detail(request, id):
    mock_test = get_object_or_404(MockTest, id=id)

    questions = Question.objects.filter(mock_test=mock_test)

    return render(request, 'exams/mocktest_detail.html', {
        'mock_test': mock_test,
        'questions': questions,
    })


# Start test page
def start_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)

    # Get language from GET or session
    lang = request.GET.get("lang")

    if lang:
        request.session["lang"] = lang
    else:
        lang = request.session.get("lang", "en")

    questions = mocktest.questions.all().prefetch_related("options")

    return render(request, "exams/start_test.html", {
        "mocktest": mocktest,
        "questions": questions,
        "lang": lang
    })
    


def attempt_test(request, mocktest_id):
    """
    Main exam page: loads timer, palette, and container for questions.
    Questions are loaded via AJAX.
    """
    mocktest = get_object_or_404(MockTest, id=mocktest_id)

    # Fetch subjects for filter dropdown
    subjects = Subject.objects.filter(questions__mock_test=mocktest).distinct()

    # Pass all questions for palette
    questions = mocktest.questions.all().order_by("id")

    # Optional subject filter for palette highlighting
    subject_id = request.GET.get("subject")
    if subject_id:
        questions = questions.filter(subject_id=subject_id)

    context = {
        "mocktest": mocktest,
        "questions": questions,
        "subjects": subjects,
        "question_number": 1,  # initial question loaded via AJAX
    }

    return render(request, "exams/attempt_test.html", context)


def ajax_question(request, mocktest_id):
    """
    AJAX view: returns a single question HTML fragment.
    """
    mocktest = get_object_or_404(MockTest, id=mocktest_id)
    q_number = int(request.GET.get("q", 1))

    # Optional subject filter
    subject_id = request.GET.get("subject")
    questions = mocktest.questions.all().prefetch_related("options").order_by("id")
    if subject_id:
        questions = questions.filter(subject_id=subject_id)

    total_questions = questions.count()
    if total_questions < q_number:
        return render(request, "exams/ajax_question.html", {"question": None})

    question = questions[q_number - 1]

    # Track answered questions in session (optional)
    answered_questions = request.session.get(f"answers_{mocktest.id}", [])

    context = {
        "question": question,
        "question_number": q_number,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
    }

    return render(request, "exams/ajax_question.html", context)



@login_required
def dashboard(request):
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related("mock_test")

    context = {
        "attempts": attempts,
    }
    return render(request, "exams/dashboard.html", context)


@login_required
def result_dashboard(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user
    )

    answers = attempt.answers.select_related(
        "question", "selected_option"
    ).prefetch_related("question__options")

    return render(request, "exams/result_dashboard.html", {
        "attempt": attempt,
        "answers": answers,
    })



@login_required
def submit_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id)

    # Create attempt
    attempt = MockTestAttempt.objects.create(
        user=request.user,
        mock_test=mocktest,
        started_at=timezone.now(),
        submitted_at=timezone.now(),
        is_completed=True
    )

    questions = Question.objects.filter(mock_test=mocktest)

    correct = 0
    wrong = 0
    skipped = 0

    for question in questions:
        selected_option_id = request.POST.get(f"question_{question.id}")

        if not selected_option_id:
            skipped += 1
            UserAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_option=None
            )
            continue

        user_answer = UserAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_option_id=selected_option_id
        )

        if user_answer.selected_option.is_correct:
            correct += 1
        else:
            wrong += 1

    total_questions = questions.count()

    # Raw marks logic (example: +1 correct, -0.25 wrong)
    score = correct * 1 - wrong * 0.25

    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped_answers = skipped
    attempt.total_marks = total_questions
    attempt.score = score
    attempt.save()

    return redirect("exams:result_dashboard", attempt_id=attempt.id)


@login_required
def result_dashboard(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user
    )

    answers = attempt.answers.select_related(
        "question", "selected_option"
    ).prefetch_related("question__options")

    recent_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).order_by("-submitted_at")[:5]

    return render(request, "exams/result_dashboard.html", {
        "attempt": attempt,
        "answers": answers,
        "total_questions": attempt.total_marks,
        "correct": attempt.correct_answers,
        "wrong": attempt.wrong_answers,
        "skipped": attempt.skipped_answers,
        "score": attempt.score,
        "percentage": attempt.percentage,
        "attempts": recent_attempts,
    })



