import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import (
    Count, Avg, F, Q, Case, When, IntegerField, Sum, Max, Min, 
    ExpressionWrapper, FloatField, Window
)
from django.db.models.functions import Rank, DenseRank, RowNumber
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.models import User
from datetime import datetime, timedelta, date
from collections import defaultdict
import tempfile
import math
import statistics
from decimal import Decimal

# Payment models - Import from exams app models
from .models import (
    PricingConfig,
    UserContentAccess,
    Subscription,
    Payment,
    TransactionLog,
    ExamCategory,
    SubCategory,
    MockTest,
    Question,
    Subject,
    MockTestAttempt,
    UserAnswer,
    Testimonial,
    FAQ,
    Contact,
)

from .forms import ContactForm, TestimonialForm


# ==============================
# DECORATOR FOR FREE USER RESTRICTION
# ==============================

def restrict_free_user(max_views=3):
    """
    Decorator to restrict free users to a maximum number of views
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Check if user is paid/subscribed
            is_paid = False
            
            # Check if user has any active subscription
            subscriptions = Subscription.objects.filter(
                user=request.user,
                status='active',
                expiry_date__gt=timezone.now()
            )
            if subscriptions.exists():
                is_paid = True
            
            # Check if user has any active content access
            if not is_paid:
                accesses = UserContentAccess.objects.filter(
                    user=request.user,
                    status='active'
                )
                if accesses.filter(expiry_date__isnull=True).exists():
                    is_paid = True
                elif accesses.filter(expiry_date__gt=timezone.now()).exists():
                    is_paid = True
            
            # If user is paid, allow unlimited access
            if is_paid:
                return view_func(request, *args, **kwargs)
            
            # For free users, check view count
            attempt_id = kwargs.get('attempt_id') or args[0] if args else None
            
            if attempt_id:
                # Get the attempt
                attempt = get_object_or_404(MockTestAttempt, id=attempt_id, user=request.user)
                
                # Check if this is a free user trying to access detailed analysis
                if 'detailed_analysis' in request.path or 'test_statistics' in request.path:
                    # Get or create view tracking
                    view_key = f'detailed_analysis_views_{request.user.id}'
                    view_count = request.session.get(view_key, 0)
                    
                    # Check if this specific attempt has been viewed before
                    viewed_attempts = request.session.get(f'viewed_attempts_{request.user.id}', [])
                    
                    # If this is a new attempt view
                    if attempt_id not in viewed_attempts:
                        view_count += 1
                        request.session[view_key] = view_count
                        viewed_attempts.append(attempt_id)
                        request.session[f'viewed_attempts_{request.user.id}'] = viewed_attempts
                    
                    # Check if limit exceeded
                    if view_count > max_views:
                        messages.warning(
                            request, 
                            f'You have reached the free limit of {max_views} detailed analysis views. '
                            'Upgrade to paid for unlimited access!'
                        )
                        return redirect('payments:locked_content', content_type='subscription', content_id=0)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ==============================
# HELPER FUNCTIONS
# ==============================

def log_transaction(user, action, content_type=None, content_id=None, details=None):
    """Helper to log transactions"""
    TransactionLog.objects.create(
        user=user,
        action=action,
        content_type=content_type,
        content_id=content_id,
        details=details or {}
    )


def check_content_access_and_redirect(request, content_obj, content_type, redirect_url=None):
    """
    Check if user has access to content, redirect if not
    Returns: (has_access, content_obj)
    """
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to access this content.')
        return False, None
    
    # Check if user has access
    if hasattr(content_obj, 'user_has_access'):
        has_access = content_obj.user_has_access(request.user)
    else:
        # Fallback for objects without user_has_access method
        has_access = True
    
    if not has_access:
        # Check if locked
        is_locked = hasattr(content_obj, 'is_locked') and content_obj.is_locked()
        if is_locked:
            messages.error(request, 'You need to purchase this content to access it.')
            if redirect_url:
                return redirect(redirect_url, content_type=content_type, content_id=content_obj.id)
            return False, None
        else:
            messages.error(request, 'You don\'t have access to this content.')
            return False, None
    
    # Log access
    log_transaction(
        request.user,
        'access_granted',
        content_type,
        content_obj.id,
        {'content_name': str(content_obj)}
    )
    
    return True, content_obj


# ==============================
# HOME
# ==============================

def home(request):
    try:
        # Get categories
        categories = ExamCategory.objects.filter(is_active=True).order_by('name')[:10]
        
        # Get mock tests
        try:
            mock_tests = MockTest.objects.filter(is_active=True).order_by('-created_at')[:6]
        except:
            mock_tests = MockTest.objects.all().order_by('-created_at')[:6]
        
        # Get testimonials
        try:
            testimonials = Testimonial.objects.filter(
                status='approved',
                is_active=True
            ).order_by('-is_featured', '-created_at')[:10]
        except Exception as e:
            print(f"Error loading testimonials: {e}")
            testimonials = []
        
        # Get FAQs
        try:
            faq_fields = [f.name for f in FAQ._meta.get_fields()]
            if 'is_active' in faq_fields:
                faqs_home = FAQ.objects.filter(is_active=True).order_by('order')[:4]
            else:
                faqs_home = FAQ.objects.all().order_by('order')[:4]
        except (ImportError, AttributeError):
            faqs_home = []
        
        # Get user's testimonial
        user_testimonial = None
        if request.user.is_authenticated:
            try:
                user_testimonial = Testimonial.objects.filter(
                    user=request.user
                ).exclude(status='rejected').first()
            except Exception as e:
                print(f"Error getting user testimonial: {e}")
        
        # Check if user is subscribed
        is_subscribed = False
        if request.user.is_authenticated:
            subscriptions = Subscription.objects.filter(
                user=request.user,
                status='active',
                expiry_date__gt=timezone.now()
            )
            is_subscribed = subscriptions.exists()
        
        context = {
            'categories': categories,
            'mock_tests': mock_tests,
            'testimonials': testimonials,
            'faqs_home': faqs_home,
            'user_testimonial': user_testimonial,
            'site_name': 'TestIQ',
            'user': request.user,
            'hero_title': 'Master Your Competitive Exams',
            'hero_desc': 'Practice. Analyze. Improve. Succeed.',
            'total_students': '50K+',
            'total_tests': '1000+',
            'success_rate': '95%',
            'is_subscribed': is_subscribed,
        }
        
        return render(request, "exams/home.html", context)
        
    except Exception as e:
        import traceback
        print("="*50)
        print("ERROR in home view:")
        print(traceback.format_exc())
        print("="*50)
        
        return render(request, "exams/home.html", {
            'categories': [],
            'mock_tests': [],
            'testimonials': [],
            'faqs_home': [],
            'user_testimonial': None,
            'site_name': 'TestIQ',
            'user': request.user,
            'hero_title': 'Master Your Competitive Exams',
            'hero_desc': 'Practice. Analyze. Improve. Succeed.',
            'total_students': '0',
            'total_tests': '0',
            'success_rate': '0%',
            'is_subscribed': False,
        })


def about(request):
    """About page view"""
    return render(request, 'exams/about.html', {
        'site_name': 'TestIQ',
    })


def faq_page(request):
    """Separate FAQ page - shows all active FAQs"""
    faqs = FAQ.objects.filter(
        is_active=True
    ).order_by('order', 'created_at')
    
    categories = {}
    for faq in faqs:
        cat = faq.category or 'General'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(faq)
    
    context = {
        'faqs': faqs,
        'categories': categories,
        'site_name': 'TestIQ',
    }
    return render(request, 'exams/faq.html', context)


def contact_page(request):
    """Contact page view"""
    form = ContactForm()
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            
            if request.user.is_authenticated:
                contact.user = request.user
            
            contact.ip_address = request.META.get('REMOTE_ADDR')
            contact.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            contact.save()
            
            messages.success(request, 'Thank you for contacting us! We\'ll get back to you soon.')
            return redirect('exams:contact_success')
        else:
            messages.error(request, 'Please correct the errors below.')
    
    context = {
        'form': form,
        'site_name': 'TestIQ',
    }
    return render(request, 'exams/contact.html', context)


def contact_success(request):
    """Contact form success page"""
    return render(request, 'exams/contact_success.html')


def privacy_policy(request):
    """Privacy policy page"""
    return render(request, 'exams/privacy_policy.html', {'site_name': 'TestIQ'})


def terms_of_service(request):
    """Terms of service page"""
    return render(request, 'exams/terms_of_service.html', {'site_name': 'TestIQ'})


# ==============================
# CATEGORY
# ==============================

def category_detail(request, slug):
    category = get_object_or_404(ExamCategory, slug=slug, is_active=True)
    
    # Check access for category
    if not category.user_has_access(request.user):
        if category.is_locked():
            messages.warning(request, f'"{category.name}" is locked. Please purchase to access.')
            return redirect('payments:locked_content', content_type='subject', content_id=category.id)
        else:
            messages.error(request, 'You don\'t have access to this category.')
            return redirect('exams:home')
    
    # Get subcategories
    subcategories = SubCategory.objects.filter(category=category, is_active=True)
    
    # Filter subcategories - show only accessible ones
    accessible_subcategories = []
    locked_subcategories = []
    
    for sub in subcategories:
        if sub.user_has_access(request.user):
            accessible_subcategories.append(sub)
        else:
            if sub.is_locked():
                locked_subcategories.append(sub)
            else:
                accessible_subcategories.append(sub)
    
    # Get pricing info
    pricing = category.get_pricing_config()
    
    # Check if user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
    
    context = {
        "category": category,
        "subcategories": accessible_subcategories,
        "locked_subcategories": locked_subcategories,
        "all_subcategories_count": subcategories.count(),
        "pricing": pricing,
        "is_locked": category.is_locked(),
        "user_has_access": category.user_has_access(request.user),
        "is_subscribed": is_subscribed,
        "price": category.get_price(),
    }
    
    return render(request, "exams/subcategory_list.html", context)


# ==============================
# SUBCATEGORY
# ==============================

def subcategory_detail(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id, is_active=True)
    
    # Check access for subcategory
    if not subcategory.user_has_access(request.user):
        if subcategory.is_locked():
            messages.warning(request, f'"{subcategory.name}" is locked. Please purchase to access.')
            return redirect('payments:locked_content', content_type='topic', content_id=subcategory.id)
        else:
            messages.error(request, 'You don\'t have access to this subcategory.')
            return redirect('exams:home')
    
    # Get tests
    tests = MockTest.objects.filter(subcategory=subcategory, is_active=True)
    
    # Filter tests - show only accessible ones
    accessible_tests = []
    locked_tests = []
    
    for test in tests:
        if test.user_has_access(request.user):
            accessible_tests.append(test)
        else:
            if test.is_locked():
                locked_tests.append(test)
            else:
                accessible_tests.append(test)
    
    # Get pricing info
    pricing = subcategory.get_pricing_config()
    
    # Check if user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
    
    context = {
        "subcategory": subcategory,
        "tests": accessible_tests,
        "locked_tests": locked_tests,
        "all_tests_count": tests.count(),
        "pricing": pricing,
        "is_locked": subcategory.is_locked(),
        "user_has_access": subcategory.user_has_access(request.user),
        "is_subscribed": is_subscribed,
        "price": subcategory.get_price(),
        "category": subcategory.category,
    }
    
    return render(request, "exams/mocktest_list.html", context)


# ==============================
# MOCK TEST DETAIL
# ==============================

def mocktest_detail(request, pk):
    mock_test = get_object_or_404(MockTest, id=pk, is_active=True)
    
    # Check access for mock test
    if not mock_test.user_has_access(request.user):
        if mock_test.is_locked():
            messages.warning(request, f'"{mock_test.title}" is locked. Please purchase to access.')
            return redirect('payments:locked_content', content_type='mocktest', content_id=mock_test.id)
        else:
            messages.error(request, 'You don\'t have access to this test.')
            return redirect('exams:home')
    
    questions = Question.objects.filter(mock_test=mock_test)
    pricing = mock_test.get_pricing_config()
    
    # Check if user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
    
    # Check if user has already attempted this test
    existing_attempt = None
    if request.user.is_authenticated:
        existing_attempt = MockTestAttempt.objects.filter(
            user=request.user,
            mock_test=mock_test,
            is_completed=False
        ).first()
    
    context = {
        "mock_test": mock_test,
        "questions": questions,
        "pricing": pricing,
        "is_locked": mock_test.is_locked(),
        "user_has_access": mock_test.user_has_access(request.user),
        "is_subscribed": is_subscribed,
        "price": mock_test.get_price(),
        "existing_attempt": existing_attempt,
        "total_questions": questions.count(),
        "total_marks": sum(q.marks for q in questions),
    }
    
    return render(request, "exams/mocktest_detail.html", context)


# ==============================
# START TEST (CREATE ATTEMPT)
# ==============================

@login_required
def start_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
    
    # Check if user has access to this test
    if not mocktest.user_has_access(request.user):
        if mocktest.is_locked():
            messages.error(request, 'You need to purchase this test to start it.')
            return redirect('payments:locked_content', content_type='mocktest', content_id=mocktest.id)
        else:
            messages.error(request, 'You don\'t have access to this test.')
            return redirect('exams:home')
    
    # Create or get existing attempt
    attempt, created = MockTestAttempt.objects.get_or_create(
        user=request.user,
        mock_test=mocktest,
        is_completed=False,
        defaults={
            "started_at": timezone.now(),
            "language": request.session.get(f'test_{mocktest.id}_language', 'en')
        }
    )
    
    # Check if test is already submitted
    if not created and attempt.is_completed:
        messages.info(request, 'You have already completed this test.')
        return redirect('exams:result_dashboard', attempt_id=attempt.id)
    
    # Log the start
    log_transaction(
        request.user,
        'test_started',
        'mocktest',
        mocktest.id,
        {'test_name': mocktest.title}
    )
    
    return redirect("exams:attempt_test", mocktest_id=mocktest.id)


# ==============================
# ATTEMPT TEST (SERVER TIMER)
# ==============================

@login_required
def attempt_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
    
    # Check access before starting
    if not mocktest.user_has_access(request.user):
        if mocktest.is_locked():
            messages.error(request, 'You need to purchase this test to attempt it.')
            return redirect('payments:locked_content', content_type='mocktest', content_id=mocktest.id)
        else:
            messages.error(request, 'You don\'t have access to this test.')
            return redirect('exams:home')

    attempt, created = MockTestAttempt.objects.get_or_create(
        user=request.user,
        mock_test=mocktest,
        is_completed=False,
        defaults={"started_at": timezone.now()}
    )
    
    # Check if already completed
    if attempt.is_completed:
        messages.info(request, 'You have already completed this test.')
        return redirect('exams:result_dashboard', attempt_id=attempt.id)
    
    language = request.session.get(f'test_{mocktest.id}_language', 'en')
    
    if created and hasattr(attempt, 'language'):
        attempt.language = language
        attempt.save()

    duration = mocktest.duration * 60
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining_seconds = int(duration - elapsed)

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
        "language": language,
        "saved_answers": saved_answers,
        "attempt": attempt,
    })


# ==============================
# SAVE ANSWER (SESSION)
# ==============================

@login_required
def save_answer(request):
    if request.method == "POST":
        mocktest_id = request.POST.get('mocktest_id')
        question_id = request.POST.get('question_id')
        option_id = request.POST.get('option_id')
        
        if not mocktest_id or not question_id:
            return JsonResponse({"status": "error", "message": "Missing parameters"})
        
        try:
            question = get_object_or_404(Question, id=question_id)
            mocktest = get_object_or_404(MockTest, id=mocktest_id)
            
            # Save to session
            answers = request.session.get(f"answers_{mocktest.id}", {})
            
            if option_id == "" or option_id is None:
                answers.pop(str(question_id), None)
            else:
                answers[str(question_id)] = int(option_id)
            
            request.session[f"answers_{mocktest.id}"] = answers
            
            return JsonResponse({
                "status": "ok",
                "saved": True,
                "question_id": question_id,
                "option_id": option_id
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    
    return JsonResponse({"status": "error", "message": "Invalid request"})


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

    saved_answers = request.session.get(f"answers_{mocktest.id}", {})
    selected_option = saved_answers.get(str(question.id))

    # Get all questions for navigation
    all_question_ids = list(questions.values_list('id', flat=True))
    current_index = all_question_ids.index(question.id)
    
    # Get answered status for all questions
    answered_status = {}
    for q in questions:
        answered_status[str(q.id)] = str(q.id) in saved_answers

    return render(request, "exams/ajax_question.html", {
        "question": question,
        "question_number": q_number,
        "total_questions": questions.count(),
        "selected_option": selected_option,
        "question_ids": all_question_ids,
        "current_index": current_index,
        "answered_status": json.dumps(answered_status),
    })


# ==============================
# VIEW RANKINGS
# ==============================

@login_required
def view_rankings(request, attempt_id):
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
    ).select_related('user').annotate(
        total_questions=F('total_marks'),
        score_percentage=(
            F('correct_answers') * 100.0 / F('total_marks')
        )
    ).order_by('-score_percentage', 'submitted_at')
    
    ranked_attempts = []
    current_rank = 1
    prev_score = None
    prev_rank = 1

    for attempt in all_attempts:
        if prev_score != attempt.score_percentage:
            rank = current_rank
        else:
            rank = prev_rank
        
        user_name = attempt.user.get_full_name()
        if not user_name:
            user_name = attempt.user.username
        
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
    
    current_user_rank = None
    for item in ranked_attempts:
        if item['is_current']:
            current_user_rank = item['rank']
            break
    
    total_attempts = len(ranked_attempts)
    
    avg_score = 0
    if total_attempts > 0:
        total_score_sum = sum(item['score'] for item in ranked_attempts)
        avg_score = round(total_score_sum / total_attempts, 1)
    
    highest_score = ranked_attempts[0]['score'] if ranked_attempts else 0
    your_percentile = calculate_percentile(ranked_attempts, current_attempt.id)
    
    paginator = Paginator(ranked_attempts, 20)
    page_number = request.GET.get('page')
    
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
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[:2].upper()
    else:
        return user.username[:2].upper()


def calculate_percentile(ranked_attempts, current_attempt_id):
    if not ranked_attempts:
        return 100
    
    total = len(ranked_attempts)
    
    current_score = None
    for item in ranked_attempts:
        if item['attempt_id'] == current_attempt_id:
            current_score = item['score']
            break
    
    if current_score is None:
        return 100
    
    lower_count = sum(1 for item in ranked_attempts if item['score'] < current_score)
    percentile = (lower_count / total) * 100
    
    return round(percentile, 1)


# ==============================
# DETAILED ANALYSIS WITH FREE USER RESTRICTION
# ==============================

@login_required
@restrict_free_user(max_views=3)
def detailed_analysis(request, attempt_id):
    """
    Detailed analysis showing all questions with filtering by correct/wrong
    Free users are limited to 3 views
    """
    try:
        attempt = get_object_or_404(
            MockTestAttempt, 
            id=attempt_id, 
            user=request.user,
            is_completed=True
        )
        
        selected_language = request.GET.get('lang', attempt.language)
        
        answers = attempt.answers.select_related(
            'question',
            'selected_option',
            'question__subject'
        ).prefetch_related('question__options').all()
        
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
                'selected_language': selected_language,
                'error_message': 'No answers found for this attempt.'
            })
        
        questions_data = []
        correct_count = 0
        wrong_count = 0
        skipped_count = 0
        
        for index, answer in enumerate(answers, start=1):
            question = answer.question
            selected_option = answer.selected_option
            
            options = question.options.all().order_by('order', 'id')
            
            is_correct = False
            correct_option = None
            
            if selected_option:
                is_correct = selected_option.is_correct
                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1
                    
                correct_option = question.options.filter(is_correct=True).first()
            else:
                skipped_count += 1
            
            options_data = []
            for opt_index, option in enumerate(options, start=1):
                if selected_language == 'hi' and hasattr(option, 'text_hi') and option.text_hi:
                    option_text = option.text_hi
                else:
                    option_text = option.text_en if hasattr(option, 'text_en') and option.text_en else f"Option {opt_index}"
                
                option_dict = {
                    'id': option.id,
                    'text': option_text,
                    'is_correct': option.is_correct,
                    'is_selected': selected_option and selected_option.id == option.id,
                    'letter': chr(64 + opt_index)
                }
                options_data.append(option_dict)
            
            question_text = "Question text not available"
            if selected_language == 'hi' and hasattr(question, 'question_hi') and question.question_hi:
                question_text = question.question_hi
            else:
                question_text = question.question_en if hasattr(question, 'question_en') and question.question_en else "Question text not available"
            
            subject_name = question.subject.name if question.subject else 'General'
            difficulty = getattr(question, 'difficulty', 'Medium')
            explanation = getattr(question, 'explanation', 'No explanation available.')
            
            selected_option_text = 'Not Answered'
            if selected_option:
                if selected_language == 'hi' and hasattr(selected_option, 'text_hi') and selected_option.text_hi:
                    selected_option_text = selected_option.text_hi
                else:
                    selected_option_text = selected_option.text_en if hasattr(selected_option, 'text_en') and selected_option.text_en else "Selected option"
            
            correct_option_text = 'No correct option found'
            if correct_option:
                if selected_language == 'hi' and hasattr(correct_option, 'text_hi') and correct_option.text_hi:
                    correct_option_text = correct_option.text_hi
                else:
                    correct_option_text = correct_option.text_en if hasattr(correct_option, 'text_en') and correct_option.text_en else "Correct option"
            
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
                'marks': question.marks,
                'negative_marks': question.get_effective_negative_marks(),
            }
            questions_data.append(question_data)
        
        total_questions = len(questions_data)
        
        accuracy = 0
        if total_questions > 0:
            accuracy = round((correct_count / total_questions * 100), 1)

        if not attempt.has_detailed_data:
            return render(request, 'exams/detailed_analysis_unavailable.html', {
                'attempt': attempt,
                'message': 'Detailed answers are no longer available for free users after 7 days. Upgrade to paid to keep your detailed history!'
            })
        
        subject_stats = {}
        for q in questions_data:
            subject = q['subject']
            if subject not in subject_stats:
                subject_stats[subject] = {
                    'total': 0,
                    'correct': 0,
                    'wrong': 0,
                    'skipped': 0,
                    'score': 0,
                    'max_score': 0
                }
            subject_stats[subject]['total'] += 1
            subject_stats[subject]['max_score'] += q['marks']
            if q['is_correct']:
                subject_stats[subject]['correct'] += 1
                subject_stats[subject]['score'] += q['marks']
            elif q['is_answered']:
                subject_stats[subject]['wrong'] += 1
                subject_stats[subject]['score'] -= q['negative_marks']
            else:
                subject_stats[subject]['skipped'] += 1
        
        for subject, stats in subject_stats.items():
            if stats['total'] > 0:
                stats['percentage'] = round((stats['correct'] / stats['total'] * 100), 1)
                stats['score_percentage'] = round((stats['score'] / stats['max_score'] * 100), 1) if stats['max_score'] > 0 else 0
            else:
                stats['percentage'] = 0
                stats['score_percentage'] = 0
        
        # Get view count for free users
        view_key = f'detailed_analysis_views_{request.user.id}'
        view_count = request.session.get(view_key, 0)
        max_views = 3
        remaining_views = max(0, max_views - view_count)
        
        # Check if user is subscribed
        is_subscribed = False
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
        
        context = {
            'attempt': attempt,
            'questions_data': questions_data,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'skipped_count': skipped_count,
            'accuracy': accuracy,
            'subject_stats': subject_stats,
            'selected_language': selected_language,
            'languages': [
                {'code': 'en', 'name': 'English'},
                {'code': 'hi', 'name': 'हिन्दी (Hindi)'},
            ],
            'view_count': view_count,
            'remaining_views': remaining_views,
            'max_views': max_views,
            'is_paid': is_subscribed or attempt.is_paid_user,
            'is_subscribed': is_subscribed,
            'total_raw_score': attempt.raw_score,
            'total_score': attempt.score_with_negative,
            'total_negative': attempt.negative_marks_applied,
        }
        
        return render(request, 'exams/detailed_analysis.html', context)
    
    except Exception as e:
        import logging
        import traceback
        
        logger = logging.getLogger(__name__)
        logger.error(f"Error in detailed_analysis for attempt {attempt_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        return render(request, 'exams/error.html', {
            'error_message': f'Unable to load detailed analysis: {str(e)}',
            'attempt_id': attempt_id
        })


# ==============================
# TEST STATISTICS WITH FREE USER RESTRICTION
# ==============================

@login_required
@restrict_free_user(max_views=3)
def test_statistics(request, attempt_id):
    """Test statistics page with free user restriction"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        attempt = get_object_or_404(
            MockTestAttempt,
            id=attempt_id,
            user=request.user,
            is_completed=True
        )
        
        answers = attempt.answers.select_related('question', 'selected_option', 'question__subject').all()
        
        total_questions = answers.count()
        correct = attempt.correct_answers
        wrong = attempt.wrong_answers
        skipped = attempt.skipped_answers
        
        raw_score = attempt.raw_score
        score_with_negative = attempt.score_with_negative
        negative_applied = attempt.negative_marks_applied
        
        subject_data = []
        subject_performance = {}
        
        for answer in answers:
            subject_name = answer.question.subject.name if answer.question.subject else "General"
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {
                    'total': 0, 
                    'correct': 0, 
                    'wrong': 0, 
                    'skipped': 0,
                    'raw_score': 0,
                    'score_with_negative': 0,
                    'negative': 0,
                    'total_marks': 0
                }
            
            subject_performance[subject_name]['total'] += 1
            subject_performance[subject_name]['total_marks'] += answer.question.marks
            
            if not answer.selected_option:
                subject_performance[subject_name]['skipped'] += 1
            elif answer.selected_option.is_correct:
                subject_performance[subject_name]['correct'] += 1
                subject_performance[subject_name]['raw_score'] += answer.question.marks
                subject_performance[subject_name]['score_with_negative'] += answer.question.marks
            else:
                subject_performance[subject_name]['wrong'] += 1
                negative = answer.question.get_effective_negative_marks()
                subject_performance[subject_name]['negative'] += negative
                subject_performance[subject_name]['score_with_negative'] -= negative
        
        for subject, stats in subject_performance.items():
            if stats['total'] > 0:
                accuracy = round((stats['score_with_negative'] / stats['total'] * 100), 1)
            else:
                accuracy = 0
                
            raw_accuracy = round((stats['correct'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
            
            subject_data.append({
                'name': subject,
                'total': stats['total'],
                'correct': stats['correct'],
                'wrong': stats['wrong'],
                'skipped': stats['skipped'],
                'raw_score': stats['raw_score'],
                'score_with_negative': round(stats['score_with_negative'], 1),
                'accuracy': accuracy,
                'raw_accuracy': raw_accuracy,
                'negative': round(stats['negative'], 1)
            })
        
        subject_data.sort(key=lambda x: x['score_with_negative'], reverse=True)
        
        difficulty_data = []
        difficulty_counts = {}
        difficulty_order = ['Easy', 'Medium', 'Hard', 'Expert']
        
        for answer in answers:
            difficulty = getattr(answer.question, 'difficulty', 'Medium')
            if difficulty not in difficulty_counts:
                difficulty_counts[difficulty] = {
                    'total': 0, 
                    'correct': 0,
                    'score': 0
                }
            
            difficulty_counts[difficulty]['total'] += 1
            if answer.selected_option and answer.selected_option.is_correct:
                difficulty_counts[difficulty]['correct'] += 1
                difficulty_counts[difficulty]['score'] += answer.question.marks
            elif answer.selected_option and not answer.selected_option.is_correct:
                negative = answer.question.get_effective_negative_marks()
                difficulty_counts[difficulty]['score'] -= negative
        
        for diff_name in difficulty_order:
            if diff_name in difficulty_counts:
                stats = difficulty_counts[diff_name]
                difficulty_data.append({
                    'name': diff_name,
                    'total': stats['total'],
                    'correct': stats['correct'],
                    'score': round(stats['score'], 1)
                })
        
        all_attempts = MockTestAttempt.objects.filter(
            mock_test=attempt.mock_test,
            is_completed=True
        ).select_related('user').order_by('-score_with_negative')
        
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
            total_percentage = sum(att.percentage_with_negative for att in all_attempts)
            global_avg = round(total_percentage / total_attempts, 1)
            top_attempt = all_attempts.first()
            if top_attempt:
                top_score = round(top_attempt.percentage_with_negative, 1)
        
        user_best_scores = {}
        for att in all_attempts:
            user_id = att.user.id
            score = att.score_with_negative
            if user_id not in user_best_scores or score > user_best_scores[user_id]['score']:
                user_best_scores[user_id] = {
                    'attempt': att,
                    'score': score
                }
        
        best_attempts_list = [data['attempt'] for data in user_best_scores.values()]
        best_attempts_list.sort(key=lambda x: x.score_with_negative, reverse=True)
        
        top_scorers = []
        for idx, att in enumerate(best_attempts_list[:10], 1):
            user_name = att.user.get_full_name() or att.user.username
            
            if att.user.first_name:
                first_char = att.user.first_name[0]
            elif att.user.username:
                first_char = att.user.username[0]
            else:
                first_char = 'U'
            
            top_scorers.append({
                'rank': idx,
                'name': user_name,
                'initials': first_char.upper(),
                'score': round(att.percentage_with_negative, 1),
                'correct': att.correct_answers,
                'total': att.total_marks,
                'is_current': att.id == attempt.id
            })
        
        insights = []
        if subject_data:
            strongest = max(subject_data, key=lambda x: x['accuracy'])
            insights.append(f"Strongest: {strongest['name']} ({strongest['accuracy']}%)")
            weakest = min(subject_data, key=lambda x: x['accuracy'])
            if weakest['accuracy'] < 60:
                insights.append(f"Focus on: {weakest['name']} ({weakest['accuracy']}%)")
        
        if attempt.score_with_negative < attempt.raw_score:
            lost_marks = round(attempt.raw_score - attempt.score_with_negative, 1)
            insights.append(f"Lost {lost_marks} marks due to negative marking")
        
        if rank:
            if rank == 1:
                insights.append(f"🏆 Congratulations! You're Rank 1!")
            elif rank <= 3:
                insights.append(f"🏆 Outstanding! You're in Top {rank}!")
            elif rank <= 10:
                insights.append(f"🎯 Great job! You're in Top 10!")
        
        chart_data = {
            'subject_names': [s['name'] for s in subject_data],
            'subject_scores': [s['score_with_negative'] for s in subject_data],
            'difficulty_labels': [d['name'] for d in difficulty_data],
            'difficulty_scores': [d['score'] for d in difficulty_data],
        }
        
        # Get view count for free users
        view_key = f'detailed_analysis_views_{request.user.id}'
        view_count = request.session.get(view_key, 0)
        max_views = 3
        remaining_views = max(0, max_views - view_count)
        
        # Check if user is subscribed
        is_subscribed = False
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
        
        context = {
            'attempt': attempt,
            'total_questions': total_questions,
            'correct': correct,
            'wrong': wrong,
            'skipped': skipped,
            'raw_score': raw_score,
            'score_with_negative': score_with_negative,
            'negative_applied': negative_applied,
            'percentage_raw': attempt.percentage_raw,
            'percentage_with_negative': attempt.percentage_with_negative,
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
            'view_count': view_count,
            'remaining_views': remaining_views,
            'max_views': max_views,
            'is_subscribed': is_subscribed,
            'is_paid': is_subscribed or attempt.is_paid_user,
        }
        
        return render(request, 'exams/test_statistics.html', context)
        
    except Exception as e:
        print(f"ERROR in test_statistics: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'exams/test_statistics.html', {
            'attempt': attempt if 'attempt' in locals() else None,
            'subject_data': [],
            'difficulty_data': [],
            'top_scorers': [],
            'insights': [f"Error loading statistics: {str(e)}"],
            'chart_data_json': json.dumps({'difficulty_labels': [], 'difficulty_scores': []}),
        })


# ==============================
# DASHBOARD
# ==============================

@login_required
def dashboard(request):
    """
    User dashboard showing all test attempts, statistics, and performance charts.
    """
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
    for attempt in attempts:
        if attempt.total_marks and attempt.total_marks > 0:
            attempt.percentage = round((attempt.score_with_negative / attempt.total_marks) * 100, 1)
        else:
            attempt.percentage = 0
    
    try:
        user_testimonial = Testimonial.objects.filter(user=request.user).first()
    except:
        user_testimonial = None

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

    user_answers = UserAnswer.objects.filter(
        attempt__user=request.user,
        attempt__is_completed=True
    ).select_related('question__subject', 'selected_option')

    subject_stats_qs = user_answers.values(
        subject_name=F('question__subject__name')
    ).annotate(
        total=Count('id'),
        correct=Count(Case(
            When(selected_option__is_correct=True, then=1),
            output_field=IntegerField()
        ))
    ).order_by('subject_name')

    subject_labels = []
    subject_scores = []
    for stat in subject_stats_qs:
        subject_labels.append(stat['subject_name'] or 'Uncategorized')
        percentage = (stat['correct'] / stat['total'] * 100) if stat['total'] > 0 else 0
        subject_scores.append(round(percentage, 1))

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

    subject_labels_json = json.dumps(subject_labels)
    subject_scores_json = json.dumps(subject_scores)
    attempts_json = json.dumps(attempts_data)
    
    # Check if user is subscribed
    is_subscribed = False
    subscriptions = Subscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gt=timezone.now()
    )
    is_subscribed = subscriptions.exists()
    
    # Get recent purchases
    recent_purchases = Payment.objects.filter(
        user=request.user,
        status='completed'
    ).order_by('-created_at')[:5]

    context = {
        'attempts': attempts[:10],
        'total_tests': total_tests,
        'avg_score': avg_score,
        'best_score': best_score,
        'subject_stats': subject_stats_qs,
        'user_testimonial': user_testimonial,
        'subject_labels_json': subject_labels_json,
        'subject_scores_json': subject_scores_json,
        'attempts_json': attempts_json,
        'is_subscribed': is_subscribed,
        'recent_purchases': recent_purchases,
    }

    return render(request, 'exams/dashboard.html', context)


# ==============================
# TESTIMONIAL VIEWS
# ==============================

@login_required
def submit_testimonial(request):
    existing = Testimonial.objects.filter(
        user=request.user
    ).exclude(status='rejected').first()
    
    if existing:
        if existing.status == 'pending':
            messages.warning(request, 'Your testimonial is pending admin approval.')
        elif existing.status == 'approved':
            messages.info(request, 'You have already submitted a testimonial.')
        return redirect('exams:dashboard')
    
    if request.method == 'POST':
        form = TestimonialForm(request.POST)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.user = request.user
            testimonial.status = 'pending'
            testimonial.is_active = False
            testimonial.save()
            
            messages.success(
                request, 
                'Thank you for your testimonial! It will be reviewed by our team and published soon.'
            )
            return redirect('exams:dashboard')
    else:
        form = TestimonialForm()
    
    return render(request, 'exams/submit_testimonial.html', {'form': form})


@login_required
def edit_testimonial(request, testimonial_id):
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
    testimonial = get_object_or_404(Testimonial, id=testimonial_id, user=request.user)
    
    if request.method == 'POST':
        testimonial.delete()
        messages.success(request, 'Your testimonial has been deleted.')
        return redirect('exams:dashboard')
    
    return render(request, 'exams/confirm_delete_testimonial.html', {
        'testimonial': testimonial
    })


# ==============================
# PRETEST DETAIL PAGE
# ==============================

@login_required
def pretest_detail(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
    
    # Check if user has access
    has_access = mocktest.user_has_access(request.user)
    
    questions = mocktest.questions.all()
    total_marks = sum(q.marks for q in questions)
    
    first_question = questions.first()
    if first_question:
        question_marks = first_question.marks
    else:
        question_marks = 1
    
    has_negative_marking = mocktest.has_negative_marking
    negative_marks = 0
    
    if has_negative_marking:
        if mocktest.negative_marking_type == 'fixed_per_question':
            negative_marks = mocktest.negative_marking_value
        elif mocktest.negative_marking_type == 'percentage_of_marks':
            negative_marks = (question_marks * mocktest.negative_marking_value) / 100
        elif mocktest.negative_marking_type == 'per_question':
            difficulty_values = set()
            for q in questions:
                if q.override_test_negative and q.negative_marks is not None:
                    difficulty_values.add(q.negative_marks)
                else:
                    difficulty_map = {'Easy': 0.25, 'Medium': 0.33, 'Hard': 0.50}
                    difficulty_values.add(difficulty_map.get(q.difficulty, 0.25))
            
            if len(difficulty_values) == 1:
                negative_marks = list(difficulty_values)[0]
            else:
                negative_marks = f"{min(difficulty_values)} - {max(difficulty_values)}"
        else:
            negative_marks = 0
    
    has_question_override = any(q.override_test_negative and q.negative_marks is not None for q in questions)
    
    existing_attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()
    
    # Check if user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        is_subscribed = subscriptions.exists()
    
    pricing = mocktest.get_pricing_config()
    
    context = {
        'mocktest': mocktest,
        'existing_attempt': existing_attempt,
        'languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'hi', 'name': 'हिन्दी (Hindi)'},
        ],
        'total_marks': total_marks,
        'question_marks': question_marks,
        'negative_marks': negative_marks,
        'has_negative_marking': has_negative_marking,
        'has_question_override': has_question_override,
        'has_access': has_access,
        'pricing': pricing,
        'is_free': mocktest.is_free(),
        'is_locked': mocktest.is_locked(),
        'price': mocktest.get_price(),
        'is_subscribed': is_subscribed,
        'user_has_access': has_access,
    }
    return render(request, 'exams/pretest_detail.html', context)


# ==============================
# VERIFY AND START TEST
# ==============================

@login_required
def start_test_verified(request, mocktest_id):
    if request.method == 'POST':
        mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)
        
        # Check access
        if not mocktest.user_has_access(request.user):
            if mocktest.is_locked():
                messages.error(request, 'You need to purchase this test to attempt it.')
                return redirect('payments:locked_content', content_type='mocktest', content_id=mocktest.id)
            else:
                messages.error(request, 'You don\'t have access to this test.')
                return redirect('exams:home')
        
        terms_accepted = request.POST.get('terms_accepted')
        selected_language = request.POST.get('language')
        
        if not terms_accepted:
            messages.error(request, 'You must accept the terms and conditions to start the test.')
            return redirect('exams:pretest_detail', mocktest_id=mocktest.id)
        
        if not selected_language:
            messages.error(request, 'Please select your preferred language.')
            return redirect('exams:pretest_detail', mocktest_id=mocktest.id)
        
        request.session['test_language'] = selected_language
        request.session[f'test_{mocktest.id}_language'] = selected_language
        
        is_paid = False
        # Check if user is paid/subscribed
        subscriptions = Subscription.objects.filter(
            user=request.user,
            status='active',
            expiry_date__gt=timezone.now()
        )
        if subscriptions.exists():
            is_paid = True
        
        if not is_paid:
            accesses = UserContentAccess.objects.filter(
                user=request.user,
                content_type='mocktest',
                content_id=mocktest.id,
                status='active'
            )
            if accesses.filter(expiry_date__isnull=True).exists() or accesses.filter(expiry_date__gt=timezone.now()).exists():
                is_paid = True
        
        attempt, created = MockTestAttempt.objects.get_or_create(
            user=request.user,
            mock_test=mocktest,
            is_completed=False,
            defaults={
                "started_at": timezone.now(),
                "language": selected_language,
                "is_paid_user": is_paid,
                "has_detailed_data": True
            }
        )
        
        if not created:
            if not attempt.started_at:
                attempt.started_at = timezone.now()
            attempt.language = selected_language
            if is_paid:
                attempt.is_paid_user = True
            attempt.save()
        
        # Log the start
        log_transaction(
            request.user,
            'test_started',
            'mocktest',
            mocktest.id,
            {'test_name': mocktest.title, 'language': selected_language}
        )
        
        return redirect("exams:attempt_test", mocktest_id=mocktest.id)
    
    return redirect('exams:pretest_detail', mocktest_id=mocktest_id)


# ==============================
# SUBMIT TEST
# ==============================

@login_required
def submit_test(request, mocktest_id):
    mocktest = get_object_or_404(MockTest, id=mocktest_id, is_active=True)

    attempt = MockTestAttempt.objects.filter(
        user=request.user,
        mock_test=mocktest,
        is_completed=False
    ).first()

    if not attempt:
        messages.error(request, 'No active attempt found for this test.')
        return redirect("exams:home")

    if attempt.is_completed:
        return redirect("exams:result_dashboard", attempt_id=attempt.id)

    attempt.submitted_at = timezone.now()
    attempt.is_completed = True

    questions = Question.objects.filter(mock_test=mocktest)
    session_answers = request.session.get(f"answers_{mocktest.id}", {})

    correct = 0
    wrong = 0
    skipped = 0
    raw_score = 0
    score_with_negative = 0
    negative_applied = 0

    for question in questions:
        selected_id = session_answers.get(str(question.id))

        if not selected_id or selected_id == "":
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

        if ua.selected_option and ua.selected_option.is_correct:
            correct += 1
            raw_score += question.marks
            score_with_negative += question.marks
        else:
            wrong += 1
            negative = question.get_effective_negative_marks()
            negative_applied += negative
            score_with_negative -= negative

    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped_answers = skipped
    attempt.raw_score = raw_score
    attempt.score_with_negative = max(0, score_with_negative)
    attempt.negative_marks_applied = negative_applied
    attempt.total_marks = sum(q.marks for q in questions)

    attempt.save()

    # Clear session answers
    request.session.pop(f"answers_{mocktest.id}", None)
    
    # Log submission
    log_transaction(
        request.user,
        'test_submitted',
        'mocktest',
        mocktest.id,
        {
            'test_name': mocktest.title,
            'score': attempt.score_with_negative,
            'correct': correct,
            'wrong': wrong,
            'skipped': skipped
        }
    )
    
    messages.success(request, 'Test submitted successfully!')
    return redirect("exams:result_dashboard", attempt_id=attempt.id)


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

    all_attempts = MockTestAttempt.objects.filter(
        mock_test=attempt.mock_test,
        is_completed=True
    ).annotate(
        score_percentage=ExpressionWrapper(
            F('score_with_negative') * 100.0 / F('total_marks'),
            output_field=FloatField()
        )
    ).order_by('-score_percentage')
    
    rank = None
    percentile = None
    
    if all_attempts.exists():
        current_rank = 1
        prev_score = None
        for idx, att in enumerate(all_attempts):
            if prev_score != att.score_percentage:
                current_rank = idx + 1
            
            if att.id == attempt.id:
                rank = current_rank
                break
            
            prev_score = att.score_percentage
        
        total_attempts = all_attempts.count()
        if total_attempts > 0:
            lower_count = all_attempts.filter(score_percentage__lt=attempt.percentage_with_negative).count()
            percentile = round((lower_count / total_attempts) * 100, 1)
    
    subject_stats = []
    if answers.exists() and hasattr(answers.first().question, 'subject'):
        subject_data = answers.values('question__subject__name').annotate(
            total=Count('id'),
            correct_count=Count('id', filter=Q(selected_option__is_correct=True)),
            wrong_count=Count('id', filter=Q(selected_option__is_correct=False) & ~Q(selected_option__isnull=True)),
            skipped_count=Count('id', filter=Q(selected_option__isnull=True))
        ).order_by('question__subject__name')
        
        for data in subject_data:
            if data['question__subject__name']:
                subject_raw = data['correct_count'] * 1
                subject_negative = data['wrong_count'] * 0.25
                subject_score = subject_raw - subject_negative
                
                subject_stats.append({
                    'subject': data['question__subject__name'],
                    'total': data['total'],
                    'correct': data['correct_count'],
                    'wrong': data['wrong_count'],
                    'skipped': data['skipped_count'],
                    'raw_score': subject_raw,
                    'score_with_negative': max(0, subject_score),
                })
    
    recent_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).exclude(id=attempt_id).order_by("-submitted_at")[:5]
    
    # Check if user is subscribed
    is_subscribed = False
    subscriptions = Subscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gt=timezone.now()
    )
    is_subscribed = subscriptions.exists()

    return render(request, "exams/result_dashboard.html", {
        "attempt": attempt,
        "answers": answers,
        "attempts": recent_attempts,
        "total_questions": attempt.total_marks,
        "correct": attempt.correct_answers,
        "wrong": attempt.wrong_answers,
        "skipped": attempt.skipped_answers,
        "raw_score": attempt.raw_score,
        "score_with_negative": attempt.score_with_negative,
        "negative_applied": attempt.negative_marks_applied,
        "total_possible": attempt.total_marks,
        "percentage_raw": attempt.percentage_raw,
        "percentage_with_negative": attempt.percentage_with_negative,
        "rank": rank,
        "percentile": percentile,
        "subject_stats": subject_stats,
        "is_subscribed": is_subscribed,
    })


# ==============================
# DOWNLOAD STATISTICS PDF
# ==============================

@login_required
def download_statistics_pdf(request, attempt_id):
    attempt = get_object_or_404(
        MockTestAttempt,
        id=attempt_id,
        user=request.user,
        is_completed=True
    )
    
    answers = attempt.answers.select_related('question', 'selected_option', 'question__subject').all()
    
    total_questions = answers.count()
    correct = attempt.correct_answers
    wrong = attempt.wrong_answers
    skipped = attempt.skipped_answers
    raw_score = attempt.raw_score
    score_with_negative = attempt.score_with_negative
    negative_applied = attempt.negative_marks_applied
    
    subject_performance = {}
    for answer in answers:
        subject_name = answer.question.subject.name if answer.question.subject else "General"
        if subject_name not in subject_performance:
            subject_performance[subject_name] = {'total': 0, 'correct': 0, 'wrong': 0, 'skipped': 0,
                                                 'raw_score': 0, 'score_with_negative': 0, 'negative': 0}
        stats = subject_performance[subject_name]
        stats['total'] += 1
        if not answer.selected_option:
            stats['skipped'] += 1
        elif answer.selected_option.is_correct:
            stats['correct'] += 1
            stats['raw_score'] += answer.question.marks
            stats['score_with_negative'] += answer.question.marks
        else:
            stats['wrong'] += 1
            negative = answer.question.get_effective_negative_marks()
            stats['negative'] += negative
            stats['score_with_negative'] -= negative
    
    subject_data = []
    for subject, stats in subject_performance.items():
        accuracy = round((stats['score_with_negative'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
        subject_data.append({
            'name': subject,
            'total': stats['total'],
            'correct': stats['correct'],
            'wrong': stats['wrong'],
            'skipped': stats['skipped'],
            'raw_score': stats['raw_score'],
            'score_with_negative': round(stats['score_with_negative'], 1),
            'accuracy': accuracy,
            'negative': round(stats['negative'], 1)
        })
    subject_data.sort(key=lambda x: x['score_with_negative'], reverse=True)
    
    difficulty_counts = {}
    for answer in answers:
        difficulty = getattr(answer.question, 'difficulty', 'Medium')
        if difficulty not in difficulty_counts:
            difficulty_counts[difficulty] = {'total': 0, 'correct': 0, 'score': 0}
        stats = difficulty_counts[difficulty]
        stats['total'] += 1
        if answer.selected_option and answer.selected_option.is_correct:
            stats['correct'] += 1
            stats['score'] += answer.question.marks
        elif answer.selected_option and not answer.selected_option.is_correct:
            negative = answer.question.get_effective_negative_marks()
            stats['score'] -= negative
    
    difficulty_data = [{'name': k, 'total': v['total'], 'correct': v['correct'], 'score': round(v['score'], 1)}
                       for k, v in difficulty_counts.items()]
    
    all_attempts = MockTestAttempt.objects.filter(
        mock_test=attempt.mock_test,
        is_completed=True
    ).order_by('-score_with_negative')
    
    total_attempts = all_attempts.count()
    global_avg = round(sum(att.percentage_with_negative for att in all_attempts) / total_attempts, 1) if total_attempts else 0
    top_score = round(all_attempts.first().percentage_with_negative, 1) if total_attempts else 0
    
    rank = next((idx for idx, att in enumerate(all_attempts, 1) if att.id == attempt.id), None)
    
    insights = []
    if subject_data:
        strongest = subject_data[0]
        weakest = subject_data[-1]
        insights.append(f"Strongest: {strongest['name']} ({strongest['accuracy']}%)")
        if weakest['accuracy'] < 60:
            insights.append(f"Focus on: {weakest['name']} ({weakest['accuracy']}%)")
    if score_with_negative < raw_score:
        insights.append(f"Lost {round(raw_score - score_with_negative, 1)} marks due to negative marking")
    
    context = {
        'attempt': attempt,
        'total_questions': total_questions,
        'correct': correct,
        'wrong': wrong,
        'skipped': skipped,
        'raw_score': raw_score,
        'score_with_negative': score_with_negative,
        'negative_applied': negative_applied,
        'percentage_raw': attempt.percentage_raw,
        'percentage_with_negative': attempt.percentage_with_negative,
        'subject_data': subject_data,
        'difficulty_data': difficulty_data,
        'rank': rank,
        'total_attempts': total_attempts,
        'global_avg': global_avg,
        'top_score': top_score,
        'insights': insights,
    }
    
    html_string = render_to_string('exams/statistics_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{attempt.mock_test.title}_statistics.pdf"'
    
    try:
        from weasyprint import HTML
        HTML(string=html_string).write_pdf(response)
    except ImportError:
        response.write(f"PDF generation requires weasyprint. HTML content: {html_string[:500]}...")
    
    return response


# ==============================
# GET TEST CONTENT
# ==============================

def get_test_content(request, test_id):
    try:
        test = get_object_or_404(MockTest, id=test_id, is_active=True)
        language = request.GET.get('lang', 'en')
        
        from .models import MockTestContentSection
        content_sections = MockTestContentSection.objects.filter(
            mock_test=test,
            is_active=True
        ).order_by('order')
        
        sections_data = []
        for section in content_sections:
            sections_data.append({
                'id': section.id,
                'section_title': section.get_title(language),
                'content': section.get_content(language),
                'order': section.order,
                'image': section.image.url if section.image else None,
                'image_alt': section.get_image_alt(language),
                'table_data': section.table_data,
                'list_items': section.list_items,
            })
        
        return render(request, 'exams/test_detail_modal.html', {
            'test': test,
            'content_sections': sections_data,
            'language': language,
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_test_content: {str(e)}")
        
        return render(request, 'exams/test_detail_modal.html', {
            'test': None,
            'content_sections': [],
            'error': str(e),
            'language': request.GET.get('lang', 'en'),
        })


# ==============================
# LEADERBOARD
# ==============================

@login_required
def leaderboard(request):
    filter_type = request.GET.get('filter', 'overall')
    time_period = request.GET.get('period', 'all')
    
    users = User.objects.filter(
        mock_attempts__is_completed=True
    ).distinct()
    
    if time_period == 'week':
        date_filter = Q(mock_attempts__submitted_at__gte=timezone.now() - timedelta(days=7))
    elif time_period == 'month':
        date_filter = Q(mock_attempts__submitted_at__gte=timezone.now() - timedelta(days=30))
    else:
        date_filter = Q()
    
    users = users.annotate(
        total_tests=Count('mock_attempts', filter=Q(mock_attempts__is_completed=True) & date_filter),
        avg_raw_score=Avg('mock_attempts__raw_score', 
                         filter=Q(mock_attempts__is_completed=True) & date_filter),
        avg_score_with_negative=Avg('mock_attempts__score_with_negative', 
                                   filter=Q(mock_attempts__is_completed=True) & date_filter),
        total_correct=Sum('mock_attempts__correct_answers', 
                         filter=Q(mock_attempts__is_completed=True) & date_filter),
        total_wrong=Sum('mock_attempts__wrong_answers', 
                       filter=Q(mock_attempts__is_completed=True) & date_filter),
        total_skipped=Sum('mock_attempts__skipped_answers', 
                         filter=Q(mock_attempts__is_completed=True) & date_filter),
        best_raw_score=Max('mock_attempts__raw_score', 
                          filter=Q(mock_attempts__is_completed=True) & date_filter),
        best_score_with_negative=Max('mock_attempts__score_with_negative', 
                                    filter=Q(mock_attempts__is_completed=True) & date_filter),
        total_marks=Sum('mock_attempts__total_marks', 
                       filter=Q(mock_attempts__is_completed=True) & date_filter),
    ).filter(total_tests__gt=0)
    
    if filter_type == 'accuracy':
        users = users.order_by('-accuracy')
    elif filter_type == 'tests':
        users = users.order_by('-total_tests')
    else:
        users = users.order_by('-avg_score_with_negative')
    
    leaderboard_data = []
    current_user_rank = None
    rank = 1
    prev_score = None
    
    for user in users:
        total_answered = (user.total_correct or 0) + (user.total_wrong or 0)
        accuracy = round((user.total_correct / total_answered * 100), 1) if total_answered > 0 else 0
        
        avg_percentage = 0
        if user.total_marks and user.total_marks > 0:
            avg_percentage = round((user.avg_score_with_negative / user.total_marks) * 100, 1)
        
        current_score = avg_percentage if filter_type == 'overall' else accuracy
        if prev_score is not None and current_score != prev_score:
            rank = len(leaderboard_data) + 1
        
        initials = get_user_initials(user)
        
        user_data = {
            'rank': rank,
            'user_id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'initials': initials,
            'total_tests': user.total_tests,
            'avg_score': avg_percentage,
            'best_score': round((user.best_score_with_negative / user.total_marks * 100) if user.total_marks and user.best_score_with_negative else 0, 1),
            'accuracy': accuracy,
            'total_correct': user.total_correct or 0,
            'total_wrong': user.total_wrong or 0,
            'total_skipped': user.total_skipped or 0,
            'is_current_user': user.id == request.user.id,
        }
        
        leaderboard_data.append(user_data)
        
        if user.id == request.user.id:
            current_user_rank = rank
        
        prev_score = current_score
        rank += 1
    
    paginator = Paginator(leaderboard_data, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total_users': len(leaderboard_data),
        'avg_score': round(sum(u['avg_score'] for u in leaderboard_data) / len(leaderboard_data), 1) if leaderboard_data else 0,
        'avg_accuracy': round(sum(u['accuracy'] for u in leaderboard_data) / len(leaderboard_data), 1) if leaderboard_data else 0,
        'total_tests': sum(u['total_tests'] for u in leaderboard_data),
        'top_score': leaderboard_data[0]['avg_score'] if leaderboard_data else 0,
    }
    
    chart_data = {
        'labels': [u['full_name'][:15] for u in leaderboard_data[:10]],
        'scores': [u['avg_score'] for u in leaderboard_data[:10]],
        'accuracy': [u['accuracy'] for u in leaderboard_data[:10]],
    }
    
    context = {
        'leaderboard_data': page_obj,
        'current_user_rank': current_user_rank,
        'stats': stats,
        'filter_type': filter_type,
        'time_period': time_period,
        'chart_data_json': json.dumps(chart_data),
    }
    
    return render(request, 'exams/leaderboard.html', context)


# ==============================
# ADVANCED ANALYTICS
# ==============================

@login_required
def advanced_analytics(request):
    """
    EXTREME LEVEL ADVANCED ANALYTICS DASHBOARD
    """
    
    # Data Collection
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related(
        'mock_test', 
        'mock_test__subcategory'
    ).prefetch_related(
        'answers',
        'answers__question',
        'answers__selected_option'
    ).order_by('-submitted_at')
    
    answers = UserAnswer.objects.filter(
        attempt__user=request.user,
        attempt__is_completed=True
    ).select_related(
        'question', 
        'selected_option',
        'question__subject',
        'question__mock_test'
    )
    
    total_attempts = attempts.count()
    
    # Streak
    streak = 0
    if attempts.exists():
        attempt_dates = set()
        for attempt in attempts:
            if attempt.submitted_at:
                attempt_dates.add(attempt.submitted_at.date())
        
        today = date.today()
        current_date = today
        while current_date in attempt_dates:
            streak += 1
            current_date -= timedelta(days=1)
    
    # Overall Performance
    total_questions_attempted = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = answers.filter(selected_option__isnull=False, is_correct=False).count()
    skipped_answers = answers.filter(selected_option__isnull=True).count()
    
    overall_accuracy = round(
        (correct_answers / total_questions_attempted * 100) if total_questions_attempted > 0 else 0,
        1
    )
    
    avg_score = 0
    avg_raw_score = 0
    total_negative_marks = 0
    
    if total_attempts > 0:
        total_percentage = 0
        total_raw = 0
        total_negative = 0
        count_with_marks = 0
        
        for attempt in attempts:
            if attempt.total_marks and attempt.total_marks > 0:
                total_percentage += attempt.percentage_with_negative
                total_raw += attempt.percentage_raw
                total_negative += attempt.negative_marks_applied
                count_with_marks += 1
        
        avg_score = round(total_percentage / count_with_marks, 1) if count_with_marks > 0 else 0
        avg_raw_score = round(total_raw / count_with_marks, 1) if count_with_marks > 0 else 0
        total_negative_marks = round(total_negative, 1)
    
    # Best and Worst
    best_attempt = None
    worst_attempt = None
    best_score = 0
    worst_score = 100
    
    if attempts.exists():
        for attempt in attempts:
            if attempt.total_marks and attempt.total_marks > 0:
                score = attempt.percentage_with_negative
                if score > best_score:
                    best_score = score
                    best_attempt = attempt
                if score < worst_score:
                    worst_score = score
                    worst_attempt = attempt
    
    # Subject-wise analysis
    subject_performance = {}
    for answer in answers:
        question = answer.question
        subject_name = 'General'
        if hasattr(question, 'subject') and question.subject:
            subject_name = question.subject.name if hasattr(question.subject, 'name') else str(question.subject)
        
        if subject_name not in subject_performance:
            subject_performance[subject_name] = {
                'name': subject_name,
                'total': 0,
                'correct': 0,
                'wrong': 0,
                'skipped': 0,
                'raw_score': 0,
                'score_with_negative': 0,
                'total_marks': 0,
            }
        
        subject_performance[subject_name]['total'] += 1
        subject_performance[subject_name]['total_marks'] += question.marks
        
        if not answer.selected_option:
            subject_performance[subject_name]['skipped'] += 1
        elif answer.is_correct:
            subject_performance[subject_name]['correct'] += 1
            subject_performance[subject_name]['raw_score'] += question.marks
            subject_performance[subject_name]['score_with_negative'] += question.marks
        else:
            subject_performance[subject_name]['wrong'] += 1
            negative = question.get_effective_negative_marks()
            subject_performance[subject_name]['score_with_negative'] -= negative
    
    subject_data = []
    for subject, data in subject_performance.items():
        if data['total'] > 0:
            accuracy = round((data['correct'] / data['total']) * 100, 1)
            attempted = data['correct'] + data['wrong']
            attempted_accuracy = round(
                (data['correct'] / attempted * 100) if attempted > 0 else 0,
                1
            )
            subject_data.append({
                'name': subject,
                'total': data['total'],
                'correct': data['correct'],
                'wrong': data['wrong'],
                'skipped': data['skipped'],
                'accuracy': accuracy,
                'attempted_accuracy': attempted_accuracy,
                'raw_score': round(data['raw_score'], 1),
                'score_with_negative': round(data['score_with_negative'], 1),
                'total_marks': data['total_marks'],
                'percentage': round(
                    (data['score_with_negative'] / data['total_marks'] * 100) if data['total_marks'] > 0 else 0,
                    1
                )
            })
    
    subject_data.sort(key=lambda x: x['accuracy'], reverse=True)
    
    # Difficulty analysis
    difficulty_analysis = {}
    for answer in answers:
        question = answer.question
        difficulty = getattr(question, 'difficulty', 'Medium')
        
        if difficulty not in difficulty_analysis:
            difficulty_analysis[difficulty] = {
                'total': 0,
                'correct': 0,
                'wrong': 0,
                'skipped': 0
            }
        
        difficulty_analysis[difficulty]['total'] += 1
        if not answer.selected_option:
            difficulty_analysis[difficulty]['skipped'] += 1
        elif answer.is_correct:
            difficulty_analysis[difficulty]['correct'] += 1
        else:
            difficulty_analysis[difficulty]['wrong'] += 1
    
    difficulty_data = []
    for diff, data in difficulty_analysis.items():
        difficulty_data.append({
            'name': diff,
            'total': data['total'],
            'correct': data['correct'],
            'wrong': data['wrong'],
            'skipped': data['skipped'],
            'accuracy': round((data['correct'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
        })
    
    # Performance Trend
    attempts_chrono = list(attempts.order_by('submitted_at'))
    trend_data = []
    moving_average = []
    scores = []
    
    for i, attempt in enumerate(attempts_chrono):
        if attempt.submitted_at:
            score = attempt.percentage_with_negative
            scores.append(score)
            trend_data.append({
                'date': attempt.submitted_at.strftime('%Y-%m-%d'),
                'score': round(score, 1),
                'test_name': attempt.mock_test.title[:30] if attempt.mock_test else 'Test'
            })
            
            if i >= 2:
                avg = sum(scores[-3:]) / 3
                moving_average.append(round(avg, 1))
            else:
                moving_average.append(round(score, 1))
    
    for i, data in enumerate(trend_data):
        data['moving_avg'] = moving_average[i] if i < len(moving_average) else data['score']
    
    # Predictive Score
    predicted_next_score = 0
    performance_trend = 'stable'
    
    if len(scores) >= 3:
        n = len(scores)
        x = list(range(n))
        y = scores
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator > 0:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
            
            predicted_next_score = round(slope * (n + 1) + intercept, 1)
            predicted_next_score = max(0, min(100, predicted_next_score))
            
            if slope > 2:
                performance_trend = 'improving'
            elif slope < -2:
                performance_trend = 'declining'
            else:
                performance_trend = 'stable'
    
    # Strongest & Weakest
    sorted_subjects = sorted(subject_data, key=lambda x: x['accuracy'], reverse=True)
    strongest_subjects = sorted_subjects[:3] if sorted_subjects else []
    weakest_subjects = sorted_subjects[-3:] if sorted_subjects else []
    
    # Achievements
    achievements = []
    
    if streak > 0:
        achievements.append({
            'icon': '🔥',
            'title': f'{streak} Day Streak',
            'description': f'You\'ve practiced for {streak} consecutive days!',
            'color': 'orange'
        })
    
    if any(attempt.percentage_with_negative >= 90 for attempt in attempts if attempt.total_marks and attempt.total_marks > 0):
        achievements.append({
            'icon': '👑',
            'title': 'Mastery Level',
            'description': 'You\'ve scored 90%+ in at least one test!',
            'color': 'yellow'
        })
    
    if any(attempt.percentage_with_negative >= 80 for attempt in attempts if attempt.total_marks and attempt.total_marks > 0):
        achievements.append({
            'icon': '🌟',
            'title': 'Star Performer',
            'description': 'You\'ve scored 80%+ in at least one test!',
            'color': 'indigo'
        })
    
    if total_attempts >= 10:
        achievements.append({
            'icon': '📚',
            'title': 'Practice Champion',
            'description': f'You\'ve completed {total_attempts} tests!',
            'color': 'green'
        })
    
    if total_attempts >= 5:
        achievements.append({
            'icon': '💪',
            'title': 'Dedicated Learner',
            'description': f'You\'ve completed {total_attempts} tests!',
            'color': 'blue'
        })
    
    # Recommendations
    recommendations = []
    
    if weakest_subjects:
        weak_subject_names = [s['name'] for s in weakest_subjects if s['accuracy'] < 60]
        if weak_subject_names:
            recommendations.append({
                'type': 'weak_area',
                'title': '📖 Focus on Weak Subjects',
                'description': f'Your weak areas are: {", ".join(weak_subject_names)}. Practice more questions in these subjects.',
                'action': 'View Practice Material',
                'action_url': '#'
            })
    
    hard_accuracy = next((d['accuracy'] for d in difficulty_data if d['name'] == 'Hard'), 100)
    if hard_accuracy < 50 and difficulty_data:
        recommendations.append({
            'type': 'difficulty',
            'title': '🎯 Master Hard Questions',
            'description': 'Your accuracy on hard questions is low. Focus on practicing harder problems.',
            'action': 'Start Hard Practice',
            'action_url': '#'
        })
    
    if total_attempts > 0 and streak < 3:
        recommendations.append({
            'type': 'consistency',
            'title': '📅 Build Consistency',
            'description': 'Try to practice daily to build a learning habit.',
            'action': 'Set Daily Goal',
            'action_url': '#'
        })
    
    # Insights
    insights = []
    
    if overall_accuracy >= 80:
        insights.append({
            'type': 'positive',
            'icon': '🌟',
            'title': 'Excellent Performance!',
            'description': f'Your overall accuracy of {overall_accuracy}% is outstanding. Keep up the great work!'
        })
    elif overall_accuracy >= 60:
        insights.append({
            'type': 'positive',
            'icon': '💪',
            'title': 'Good Performance!',
            'description': f'Your accuracy of {overall_accuracy}% is solid. You\'re on the right track!'
        })
    else:
        insights.append({
            'type': 'warning',
            'icon': '📚',
            'title': 'Room for Improvement',
            'description': 'Focus on understanding concepts and practicing more. You can do it!'
        })
    
    if performance_trend == 'improving':
        insights.append({
            'type': 'positive',
            'icon': '📈',
            'title': 'Improving Trend!',
            'description': 'Your performance is consistently improving. Keep the momentum going!'
        })
    elif performance_trend == 'declining':
        insights.append({
            'type': 'warning',
            'icon': '📉',
            'title': 'Declining Trend',
            'description': 'Your performance seems to be declining. Time to review your strategy!'
        })
    else:
        insights.append({
            'type': 'neutral',
            'icon': '➡️',
            'title': 'Stable Performance',
            'description': 'Your performance is consistent. Try to push for improvement!'
        })
    
    if strongest_subjects:
        insight = strongest_subjects[0]
        if insight['accuracy'] > 70:
            insights.append({
                'type': 'positive',
                'icon': '🎯',
                'title': f'Strong Subject: {insight["name"]}',
                'description': f'You excel in {insight["name"]} with {insight["accuracy"]}% accuracy!'
            })
    
    if predicted_next_score > 0:
        insights.append({
            'type': 'neutral',
            'icon': '🔮',
            'title': 'Predicted Next Score',
            'description': f'Based on your trend, your next test score is predicted to be around {predicted_next_score}%'
        })
    
    # Chart Data
    chart_data = {
        'subject_labels': [s['name'] for s in subject_data],
        'subject_accuracy': [s['accuracy'] for s in subject_data],
        'subject_attempted': [s['attempted_accuracy'] for s in subject_data],
        'difficulty_labels': [d['name'] for d in difficulty_data],
        'difficulty_accuracy': [d['accuracy'] for d in difficulty_data],
        'difficulty_correct': [d['correct'] for d in difficulty_data],
        'difficulty_wrong': [d['wrong'] for d in difficulty_data],
        'trend_dates': [d['date'] for d in trend_data],
        'trend_scores': [d['score'] for d in trend_data],
        'trend_moving_avg': [d['moving_avg'] for d in trend_data],
        'score_distribution': {
            '0-20': 0,
            '21-40': 0,
            '41-60': 0,
            '61-80': 0,
            '81-100': 0
        }
    }
    
    for attempt in attempts:
        if attempt.total_marks and attempt.total_marks > 0:
            score = attempt.percentage_with_negative
            if score <= 20:
                chart_data['score_distribution']['0-20'] += 1
            elif score <= 40:
                chart_data['score_distribution']['21-40'] += 1
            elif score <= 60:
                chart_data['score_distribution']['41-60'] += 1
            elif score <= 80:
                chart_data['score_distribution']['61-80'] += 1
            else:
                chart_data['score_distribution']['81-100'] += 1
    
    # ZPD Questions
    zpd_questions = []
    if answers.exists():
        wrong_question_ids = answers.filter(
            Q(selected_option__isnull=True) | Q(is_correct=False)
        ).values_list('question_id', flat=True).distinct()[:5]
        
        if wrong_question_ids:
            zpd_questions = Question.objects.filter(id__in=wrong_question_ids)[:5]
    
    # Check if user is subscribed
    is_subscribed = False
    subscriptions = Subscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gt=timezone.now()
    )
    is_subscribed = subscriptions.exists()
    
    context = {
        'total_tests': total_attempts,
        'total_questions': total_questions_attempted,
        'avg_score': avg_score,
        'avg_raw_score': avg_raw_score,
        'accuracy': overall_accuracy,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'skipped_answers': skipped_answers,
        'streak': streak,
        'total_negative_marks': total_negative_marks,
        'best_attempt': best_attempt,
        'worst_attempt': worst_attempt,
        'best_score': round(best_score, 1) if best_attempt else 0,
        'worst_score': round(worst_score, 1) if worst_attempt else 0,
        'subject_data': subject_data,
        'strongest_subjects': strongest_subjects,
        'weakest_subjects': weakest_subjects,
        'difficulty_data': difficulty_data,
        'trend_data': trend_data,
        'performance_trend': performance_trend,
        'predicted_next_score': predicted_next_score,
        'predictions_available': len(scores) >= 3,
        'achievements': achievements,
        'has_achievements': len(achievements) > 0,
        'recommendations': recommendations,
        'has_recommendations': len(recommendations) > 0,
        'insights': insights,
        'chart_data_json': json.dumps(chart_data),
        'subject_data_json': json.dumps(subject_data),
        'difficulty_data_json': json.dumps(difficulty_data),
        'trend_data_json': json.dumps(trend_data),
        'score_distribution_json': json.dumps(chart_data['score_distribution']),
        'zpd_questions': zpd_questions,
        'has_attempts': total_attempts > 0,
        'created_date': request.user.date_joined,
        'days_active': (timezone.now().date() - request.user.date_joined.date()).days if request.user.date_joined else 0,
        'analytics_version': '3.0',
        'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'is_subscribed': is_subscribed,
        'is_paid': is_subscribed or any(a.is_paid_user for a in attempts),
    }
    
    return render(request, 'exams/advanced_analytics.html', context)


# ==============================
# ALL ATTEMPTS
# ==============================

@login_required
def all_attempts(request):
    attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
    for attempt in attempts:
        if attempt.total_marks and attempt.total_marks > 0:
            attempt.percentage = round((attempt.score_with_negative / attempt.total_marks) * 100, 1)
        else:
            attempt.percentage = 0
    
    paginator = Paginator(attempts, 10)
    page = request.GET.get('page')
    
    try:
        attempts_page = paginator.page(page)
    except PageNotAnInteger:
        attempts_page = paginator.page(1)
    except EmptyPage:
        attempts_page = paginator.page(paginator.num_pages)
    
    total_attempts = attempts.count()
    
    avg_score = 0
    if total_attempts > 0:
        total_percentage = sum(attempt.percentage for attempt in attempts)
        avg_score = round(total_percentage / total_attempts, 1)
    
    best_score = 0
    if total_attempts > 0:
        best_score = max(attempt.percentage for attempt in attempts)
    
    # Check if user is subscribed
    is_subscribed = False
    subscriptions = Subscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gt=timezone.now()
    )
    is_subscribed = subscriptions.exists()
    
    context = {
        'attempts': attempts_page,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'best_score': best_score,
        'is_subscribed': is_subscribed,
    }
    return render(request, 'exams/all_attempts.html', context)


@login_required
def all_attempts_unified(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    exam_attempts = MockTestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('mock_test', 'mock_test__subcategory').order_by('-submitted_at')
    
    combined_attempts = []
    
    for attempt in exam_attempts:
        if attempt.total_marks and attempt.total_marks > 0:
            percentage = round((attempt.score_with_negative / attempt.total_marks) * 100, 1)
        else:
            percentage = 0
        
        combined_attempts.append({
            'id': attempt.id,
            'title': attempt.mock_test.title,
            'type': 'exam',
            'app_name': 'Main Exam',
            'submitted_at': attempt.submitted_at,
            'percentage': percentage,
            'total_marks': attempt.total_marks,
            'correct_answers': attempt.correct_answers,
            'wrong_answers': attempt.wrong_answers,
            'skipped_answers': attempt.skipped_answers,
            'score_with_negative': attempt.score_with_negative,
            'raw_score': attempt.raw_score,
            'mock_test_id': attempt.mock_test.id,
            'attempt_obj': attempt,
            'result_url': 'exams:result_dashboard',
            'analysis_url': 'exams:detailed_analysis',
            'detail_url': 'exams:result_dashboard',
        })
    
    total_attempts = len(combined_attempts)
    
    avg_score = 0
    if total_attempts > 0:
        total_percentage = sum(a['percentage'] for a in combined_attempts)
        avg_score = round(total_percentage / total_attempts, 1)
    
    best_score = 0
    if total_attempts > 0:
        best_score = max(a['percentage'] for a in combined_attempts)
    
    paginator = Paginator(combined_attempts, 10)
    page = request.GET.get('page')
    
    try:
        attempts_page = paginator.page(page)
    except PageNotAnInteger:
        attempts_page = paginator.page(1)
    except EmptyPage:
        attempts_page = paginator.page(paginator.num_pages)
    
    # Check if user is subscribed
    is_subscribed = False
    subscriptions = Subscription.objects.filter(
        user=request.user,
        status='active',
        expiry_date__gt=timezone.now()
    )
    is_subscribed = subscriptions.exists()
    
    context = {
        'attempts': attempts_page,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'best_score': best_score,
        'is_unified': True,
        'is_subscribed': is_subscribed,
    }
    
    return render(request, 'exams/all_attempts.html', context)