from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse

from .models import (
    ExamCategory,
    SubCategory,
    MockTest,
    Question,
    Subject,
    MockTestAttempt,
    UserAnswer
)

# ==============================
# HOME
# ==============================
def home(request):
    categories = ExamCategory.objects.all()
    mock_tests = MockTest.objects.filter(is_active=True)[:5]

    return render(request, "exams/home.html", {
        "categories": categories,
        "mock_tests": mock_tests,
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
    tests = MockTest.objects.filter(subcategory=subcategory)

    return render(request, "exams/mocktest_list.html", {
        "subcategory": subcategory,
        "tests": tests,
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

    recent_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).order_by("-submitted_at")[:5]

    return render(request, "exams/result_dashboard.html", {
        "attempt": attempt,
        "answers": answers,
        "attempts": recent_attempts,
    })


# ==============================
# USER DASHBOARD
# ==============================
@login_required
def dashboard(request):

    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related("mock_test")

    return render(request, "exams/dashboard.html", {
        "attempts": attempts,
    })
