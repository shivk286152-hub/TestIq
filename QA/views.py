# QA/views.py - COMPLETE WORKING VERSION

import re
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from django.template.loader import get_template
from django.utils import timezone
from django.contrib import messages
from io import BytesIO
from decimal import Decimal

from .models import Subject, Topic, Part, Question, QuestionCategory
from .forms import AdvancedQuestionFilterForm

logger = logging.getLogger(__name__)

# ============================================
# PAYMENTS IMPORTS
# ============================================

try:
    from payments.models import (
        PricingConfig,
        UserSubscription,
        UserContentAccess,
        ContentAccessLog,
        TransactionLog
    )
    PAYMENTS_AVAILABLE = True
except ImportError:
    PAYMENTS_AVAILABLE = False


def get_user_subscription_status(user):
    """Check if user has active subscription"""
    if not user.is_authenticated or not PAYMENTS_AVAILABLE:
        return False
    try:
        return UserSubscription.objects.filter(
            user=user, status='active', expiry_date__gt=timezone.now()
        ).exists()
    except:
        return False


# ============================================
# PDF GENERATION
# ============================================

def render_to_pdf(template_src, context_dict={}):
    try:
        from xhtml2pdf import pisa
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return None
    except ImportError:
        return None


def clean_comprehensive_content(content_list):
    cleaned_contents = []
    for content in content_list:
        if content.content:
            content.content = re.sub(r"{%\s*[^%]+?%}", "", content.content)
            content.content = re.sub(r"{{\s*[^}]+?}}", "", content.content)
            content.content = re.sub(r"\s+", " ", content.content).strip()
        if content.content_hi:
            content.content_hi = re.sub(r"{%\s*[^%]+?%}", "", content.content_hi)
            content.content_hi = re.sub(r"{{\s*[^}]+?}}", "", content.content_hi)
            content.content_hi = re.sub(r"\s+", " ", content.content_hi).strip()
        cleaned_contents.append(content)
    return cleaned_contents


# ============================================
# ✅ 1. SUBJECT LIST
# ============================================

def subject_list(request):
    subjects = Subject.objects.filter(is_active=True).annotate(
        topics_count=Count('topics', filter=Q(topics__is_active=True))
    )
    
    subjects_with_access = []
    for subject in subjects:
        subjects_with_access.append({
            'subject': subject,
            'topics_count': subject.topics_count,
            'can_access': subject.user_has_access(request.user),
            'is_free': subject.is_free(),
            'is_locked': subject.is_locked(),
            'price': subject.get_price(),
        })
    
    context = {
        'subjects': subjects_with_access,
        'title': 'Subjects',
        'is_subscribed': get_user_subscription_status(request.user),
    }
    return render(request, 'qa/subject_list.html', context)


# ============================================
# ✅ 2. TOPIC LIST
# ============================================
# QA/views.py - topic_list (FIXED)

def topic_list(request, subject_slug):
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    
    # ✅ Check if subject is locked
    if subject.is_locked() and not subject.user_has_access(request.user):
        messages.warning(request, f'"{subject.name}" is locked. Please purchase to access.')
        return redirect('payments:locked_content', content_type='qa_subject', content_id=subject.id)
    
    topics = subject.topics.filter(is_active=True).annotate(
        parts_count=Count('parts', filter=Q(parts__is_active=True))
    )
    
    topics_with_access = []
    for topic in topics:
        is_locked = topic.is_locked()
        can_access = topic.user_has_access(request.user)
        
        topics_with_access.append({
            'topic': topic,
            'parts_count': topic.parts_count,
            'can_access': can_access,
            'is_free': not is_locked,
            'is_locked': is_locked,
            'price': topic.get_price(),
        })
        
        # ✅ If topic is locked and user doesn't have access, show lock badge
        if is_locked and not can_access:
            # Add lock status to display
            pass
    
    comprehensive_content = subject.comprehensive_contents.filter(is_active=True)
    comprehensive_content = clean_comprehensive_content(comprehensive_content)
    
    context = {
        'subject': subject,
        'topics': topics_with_access,
        'comprehensive_content': comprehensive_content,
        'is_subscribed': get_user_subscription_status(request.user),
        'is_locked': subject.is_locked(),
        'price': subject.get_price(),
        'can_access_subject': subject.user_has_access(request.user),
    }
    return render(request, 'qa/topic_list.html', context)

# ============================================
# ✅ 3. PART LIST
# ============================================

# QA/views.py - part_list function (COMPLETE FIXED VERSION)

def part_list(request, subject_slug, topic_slug):
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    
    # ✅ CHECK: Agar topic locked hai aur user ke paas access nahi hai
    if topic.is_locked() and not topic.user_has_access(request.user):
        messages.warning(request, f'"{topic.name}" is locked. Please purchase to access.')
        return redirect('payments:locked_content', content_type='qa_topic', content_id=topic.id)
    
    parts = topic.parts.filter(is_active=True).annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    )
    
    # Fix slugs if missing
    from django.utils.text import slugify
    for part in parts:
        if not part.slug:
            part.slug = slugify(part.name)
            counter = 1
            original_slug = part.slug
            while Part.objects.filter(slug=part.slug).exclude(id=part.id).exists():
                part.slug = f"{original_slug}-{counter}"
                counter += 1
            part.save()
    
    parts_with_access = []
    for part in parts:
        parts_with_access.append({
            'part': part,
            'questions_count': part.questions_count,
            'can_access': part.user_has_access(request.user),
            'is_free': part.is_free(),
            'is_locked': part.is_locked(),
            'price': part.get_price(),
            'part_slug': part.slug,  # ✅ ADD THIS
            'part_id': part.id,       # ✅ ADD THIS
        })
    
    # Comprehensive content
    all_comprehensive = topic.comprehensive_contents.filter(is_active=True)
    comprehensive_content = []
    for content in all_comprehensive:
        has_template_tags = False
        if content.content and (re.search(r'{%\s*[^%]+?%}', content.content) or re.search(r'{{\s*[^}]+?}}', content.content)):
            has_template_tags = True
        if content.content_hi and not has_template_tags and (re.search(r'{%\s*[^%]+?%}', content.content_hi) or re.search(r'{{\s*[^}]+?}}', content.content_hi)):
            has_template_tags = True
        if not has_template_tags:
            comprehensive_content.append(content)
    
    all_categories = QuestionCategory.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True)
    
    filtered_questions = None
    filtered_count = None
    
    if request.GET:
        questions = Question.objects.filter(part__topic=topic, is_active=True)
        if request.GET.get('date_from'):
            questions = questions.filter(published_date__date__gte=request.GET.get('date_from'))
        if request.GET.get('date_to'):
            questions = questions.filter(published_date__date__lte=request.GET.get('date_to'))
        if request.GET.getlist('categories'):
            questions = questions.filter(categories__in=request.GET.getlist('categories')).distinct()
        if request.GET.get('difficulty'):
            questions = questions.filter(difficulty=request.GET.get('difficulty'))
        if request.GET.get('question_type'):
            questions = questions.filter(question_type=request.GET.get('question_type'))
        if request.GET.get('tags'):
            tags = request.GET.get('tags').split(',')
            tag_filter = Q()
            for tag in tags:
                tag_filter |= Q(tags__icontains=tag.strip())
            questions = questions.filter(tag_filter).distinct()
        if request.GET.get('search'):
            search = request.GET.get('search')
            questions = questions.filter(
                Q(question__icontains=search) |
                Q(question_hi__icontains=search) |
                Q(answer__icontains=search) |
                Q(answer_hi__icontains=search)
            ).distinct()
        if request.GET.get('featured_only'):
            questions = questions.filter(is_featured=True)
        filtered_count = questions.count()
        filtered_questions = questions[:50]
    
    # ✅ GET SUBSCRIPTION STATUS
    is_subscribed = get_user_subscription_status(request.user)
    
    context = {
        'subject': subject,
        'topic': topic,
        'parts': parts_with_access,
        'comprehensive_content': comprehensive_content,
        'all_categories': all_categories,
        'subjects': subjects,
        'filtered_count': filtered_count,
        'filtered_questions': filtered_questions,
        'is_subscribed': is_subscribed,
        'is_locked': topic.is_locked(),
        'price': topic.get_price(),
        'can_access_topic': topic.user_has_access(request.user),
        # ✅ ADD THESE FOR TEMPLATE
        'subject_slug': subject.slug,
        'topic_slug': topic.slug,
        'total_parts': parts.count(),
        'total_questions': Question.objects.filter(part__topic=topic, is_active=True).count(),
    }
    return render(request, 'qa/part_list.html', context)

# ============================================
# ✅ 4. PART DETAIL - FIXED WITH QUESTIONS
# ============================================
# QA/views.py - part_detail function (COMPLETE FIXED VERSION)

def part_detail(request, subject_slug, topic_slug, part_slug):
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    part = get_object_or_404(Part, slug=part_slug, topic=topic, is_active=True)
    
    # ✅ CHECK: Agar part locked hai aur user ke paas access nahi hai
    if part.is_locked() and not part.user_has_access(request.user):
        messages.warning(request, f'"{part.name}" is locked. Please purchase to access.')
        return redirect('payments:locked_content', content_type='qa_part', content_id=part.id)
    
    # ✅ GET ALL QUESTIONS
    questions_list = part.questions.filter(is_active=True).order_by('order', 'created_at')
    
    # ✅ IF NO QUESTIONS, SHOW MESSAGE
    if not questions_list.exists():
        messages.info(request, 'No questions available for this part yet.')
    
    # ✅ PAGINATION
    paginator = Paginator(questions_list, 10)
    page = request.GET.get('page')
    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)
    
    comprehensive_content = part.comprehensive_contents.filter(is_active=True)
    comprehensive_content = clean_comprehensive_content(comprehensive_content)
    
    rendered_content = part.render_content()
    rendered_content_hi = part.render_content(language='hi') if part.content_hi else None
    
    # ✅ Log access
    if PAYMENTS_AVAILABLE:
        try:
            ContentAccessLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                content_type='qa_part',
                content_id=part.id,
                content_name=part.name,
                content_app='qa',
                access_type='free' if part.is_free() else 'paid',
                reason='Access granted',
                ip_address=request.META.get('REMOTE_ADDR'),
                session_key=request.session.session_key or '',
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except:
            pass
    
    part.views += 1
    part.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        context = {'questions': questions}
        return render(request, 'qa/partials/question_items.html', context)
    
    # ✅ GET SUBSCRIPTION STATUS
    is_subscribed = get_user_subscription_status(request.user)
    
    # ✅ CONTEXT WITH ALL DATA
    context = {
        'subject': subject,
        'topic': topic,
        'part': part,
        'questions': questions,
        'comprehensive_content': comprehensive_content,
        'rendered_content': rendered_content,
        'rendered_content_hi': rendered_content_hi,
        'is_locked': False,
        'is_free': part.is_free(),
        'can_access': True,
        'is_subscribed': is_subscribed,
        'price': part.get_price(),
        'total_questions': questions_list.count(),
        # ✅ ADD THESE FOR TEMPLATE
        'subject_slug': subject.slug,
        'topic_slug': topic.slug,
        'part_slug': part.slug,
        'question_count': questions_list.count(),
    }
    return render(request, 'qa/part_detail.html', context)


# ============================================
# ✅ 5. TOPIC DETAIL
# ============================================

def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug, is_active=True)
    subject = topic.subject
    
    # ✅ CHECK: Agar topic locked hai aur user ke paas access nahi hai
    if topic.is_locked() and not topic.user_has_access(request.user):
        messages.warning(request, f'"{topic.name}" is locked. Please purchase to access.')
        return redirect('payments:locked_content', content_type='qa_topic', content_id=topic.id)
    
    parts = topic.parts.filter(is_active=True).annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    )
    
    all_questions = Question.objects.filter(
        part__topic=topic,
        is_active=True
    ).select_related('part').order_by('part__order', 'order')
    
    parts_with_questions = []
    for part in parts:
        questions = part.questions.filter(is_active=True).order_by('order', 'created_at')
        parts_with_questions.append({
            'part': part,
            'questions': questions,
            'count': questions.count(),
            'is_free': part.is_free(),
            'can_access': part.user_has_access(request.user),
            'is_locked': part.is_locked(),
            'price': part.get_price(),
        })
    
    context = {
        'topic': topic,
        'subject': subject,
        'parts': parts_with_questions,
        'total_parts': parts.count(),
        'total_questions': all_questions.count(),
        'site_name': 'QA Platform',
        'is_topic_free': topic.is_free(),
        'can_access_topic': topic.user_has_access(request.user),
        'is_subscribed': get_user_subscription_status(request.user),
        'price': topic.get_price(),
    }
    
    return render(request, 'qa/topic_detail.html', context)


# ============================================
# ✅ 6. PDF DOWNLOAD
# ============================================

def download_topic_pdf(request, subject_slug, topic_slug):
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    
    if topic.is_locked() and not topic.user_has_access(request.user):
        messages.error(request, "You need to purchase this content to download PDF.")
        return redirect('payments:locked_content', content_type='qa_topic', content_id=topic.id)
    
    parts = topic.parts.filter(is_active=True).annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    )
    
    all_questions = Question.objects.filter(
        part__topic=topic,
        is_active=True
    ).order_by('part__order', 'order')
    
    parts_with_questions = []
    for part in parts:
        questions = part.questions.filter(is_active=True).order_by('order', 'created_at')
        parts_with_questions.append({
            'part': part,
            'questions': questions,
            'count': questions.count()
        })
    
    context = {
        'subject': subject,
        'topic': topic,
        'parts': parts_with_questions,
        'total_questions': all_questions.count(),
        'total_parts': parts.count(),
        'site_name': 'QA Platform',
    }
    
    pdf = render_to_pdf('qa/topic_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"{topic.slug}_complete_notes.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error generating PDF. Please install xhtml2pdf: pip install xhtml2pdf", status=500)


def download_part_pdf(request, subject_slug, topic_slug, part_slug):
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    part = get_object_or_404(Part, slug=part_slug, topic=topic, is_active=True)
    
    if part.is_locked() and not part.user_has_access(request.user):
        messages.error(request, "You need to purchase this content to download PDF.")
        return redirect('payments:locked_content', content_type='qa_part', content_id=part.id)
    
    questions = part.questions.filter(is_active=True).order_by('order', 'created_at')
    
    context = {
        'subject': subject,
        'topic': topic,
        'part': part,
        'questions': questions,
        'total_questions': questions.count(),
        'site_name': 'QA Platform',
    }
    
    pdf = render_to_pdf('qa/part_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"{part.slug}_questions.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)


# ============================================
# ✅ 7. SEARCH
# ============================================

def search_questions(request):
    query = request.GET.get('q', '')
    questions = []
    if query:
        questions = Question.objects.filter(
            Q(question__icontains=query) | 
            Q(question_hi__icontains=query) |
            Q(answer__icontains=query) |
            Q(answer_hi__icontains=query)
        )[:50]
    
    context = {
        'query': query,
        'questions': questions,
    }
    return render(request, 'qa/search_results.html', context)


# ============================================
# ✅ 8. API ENDPOINTS
# ============================================

def get_topics_api(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id, is_active=True)
        topics = subject.topics.filter(is_active=True).annotate(
            parts_count=Count('parts', filter=Q(parts__is_active=True))
        ).order_by('order', 'name')
        
        topics_data = []
        for topic in topics:
            topics_data.append({
                'id': topic.id,
                'name': topic.name,
                'slug': topic.slug,
                'parts_count': topic.parts_count,
                'is_free': topic.is_free(),
                'can_access': topic.user_has_access(request.user),
                'is_locked': topic.is_locked(),
                'price': float(topic.get_price()),
            })
        
        return JsonResponse({
            'success': True,
            'subject_name': subject.name,
            'subject_slug': subject.slug,
            'topics': topics_data,
        })
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found'}, status=404)


def get_topics_by_subject_api(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id, is_active=True)
        topics = subject.topics.filter(is_active=True).values('id', 'name', 'slug')
        return JsonResponse({'success': True, 'topics': list(topics)})
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found'}, status=404)


def get_parts_by_topic_api(request, topic_id):
    try:
        topic = Topic.objects.get(id=topic_id, is_active=True)
        parts = topic.parts.filter(is_active=True).values('id', 'name', 'slug')
        return JsonResponse({'success': True, 'parts': list(parts)})
    except Topic.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Topic not found'}, status=404)


def content_status_api(request, content_type, content_id):
    try:
        content_type_map = {
            'qa_subject': Subject,
            'qa_topic': Topic,
            'qa_part': Part,
        }
        model = content_type_map.get(content_type)
        if not model:
            return JsonResponse({'error': 'Invalid content type'}, status=400)
        
        content_obj = get_object_or_404(model, id=content_id)
        
        return JsonResponse({
            'is_free': content_obj.is_free(),
            'price': float(content_obj.get_price()),
            'can_access': content_obj.user_has_access(request.user),
            'is_locked': content_obj.is_locked(),
            'requires_login': not request.user.is_authenticated,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# ✅ 9. ADVANCED FILTER
# ============================================

def advanced_question_filter(request):
    form = AdvancedQuestionFilterForm(request.GET or None)
    questions = Question.objects.filter(is_active=True).select_related('part__topic__subject').prefetch_related('categories')
    
    if form.is_valid():
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        if date_from:
            questions = questions.filter(published_date__date__gte=date_from)
        if date_to:
            questions = questions.filter(published_date__date__lte=date_to)
        
        categories = form.cleaned_data.get('categories')
        if categories:
            questions = questions.filter(categories__in=categories).distinct()
        
        subject = form.cleaned_data.get('subject')
        if subject:
            questions = questions.filter(part__topic__subject=subject)
        
        topic = form.cleaned_data.get('topic')
        if topic:
            questions = questions.filter(part__topic=topic)
        
        part = form.cleaned_data.get('part')
        if part:
            questions = questions.filter(part=part)
        
        question_type = form.cleaned_data.get('question_type')
        if question_type:
            questions = questions.filter(question_type=question_type)
        
        difficulty = form.cleaned_data.get('difficulty')
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        
        tags = form.cleaned_data.get('tags')
        if tags:
            tag_filter = Q()
            for tag in tags:
                tag_filter |= Q(tags__icontains=tag)
            questions = questions.filter(tag_filter).distinct()
        
        search = form.cleaned_data.get('search')
        if search:
            questions = questions.filter(
                Q(question__icontains=search) |
                Q(question_hi__icontains=search) |
                Q(answer__icontains=search) |
                Q(answer_hi__icontains=search)
            ).distinct()
        
        featured_only = form.cleaned_data.get('featured_only')
        if featured_only:
            questions = questions.filter(is_featured=True)
    
    questions = questions.order_by('-published_date', '-created_at')
    
    paginator = Paginator(questions, 20)
    page = request.GET.get('page')
    try:
        questions_page = paginator.page(page)
    except PageNotAnInteger:
        questions_page = paginator.page(1)
    except EmptyPage:
        questions_page = paginator.page(paginator.num_pages)
    
    all_categories = QuestionCategory.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'questions': questions_page,
        'all_categories': all_categories,
        'total_count': questions.count(),
        'title': 'Advanced Question Filter',
    }
    
    return render(request, 'qa/advanced_filter.html', context)