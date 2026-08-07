from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from django.template.loader import get_template
from django.utils import timezone
from io import BytesIO
from .models import Subject, Topic, Part, Question, QuestionCategory
from .forms import AdvancedQuestionFilterForm


# ============================================
# PDF GENERATION FUNCTION
# ============================================

def render_to_pdf(template_src, context_dict={}):
    """Convert HTML to PDF using xhtml2pdf"""
    try:
        from xhtml2pdf import pisa
        
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        
        pdf = pisa.pisaDocument(
            BytesIO(html.encode("UTF-8")),
            result,
            encoding='UTF-8'
        )
        
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return None
    except ImportError:
        # Fallback - if xhtml2pdf not installed
        return None


# ============================================
# PDF DOWNLOAD VIEWS
# ============================================

def download_topic_pdf(request, subject_slug, topic_slug):
    """Download all parts and questions of a topic as PDF"""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    parts = topic.parts.filter(is_active=True).annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    )
    
    # Get all questions from all parts
    all_questions = Question.objects.filter(
        part__topic=topic,
        is_active=True
    ).order_by('part__order', 'order')
    
    # Group questions by part
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
    
    # Fallback if PDF generation fails
    return HttpResponse("Error generating PDF. Please install xhtml2pdf: pip install xhtml2pdf", status=500)


def download_part_pdf(request, subject_slug, topic_slug, part_slug):
    """Download all questions of a single part as PDF"""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    part = get_object_or_404(Part, slug=part_slug, topic=topic, is_active=True)
    
    # Get all questions (no pagination for PDF)
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
# ORIGINAL VIEWS
# ============================================

def subject_list(request):
    """Display all subjects with topics count"""
    subjects = Subject.objects.filter(is_active=True).annotate(
        topics_count=Count('topics', filter=Q(topics__is_active=True))
    )
    
    context = {
        'subjects': subjects,
        'title': 'Subjects',
    }
    return render(request, 'qa/subject_list.html', context)


def topic_list(request, subject_slug):
    """Display topics under a subject"""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topics = subject.topics.filter(is_active=True).annotate(
        parts_count=Count('parts', filter=Q(parts__is_active=True))
    )
    
    # Get comprehensive content for this subject
    comprehensive_content = subject.comprehensive_contents.filter(is_active=True)
    
    context = {
        'subject': subject,
        'topics': topics,
        'comprehensive_content': comprehensive_content,
    }
    return render(request, 'qa/topic_list.html', context)


def part_list(request, subject_slug, topic_slug):
    """Display parts under a topic with filter functionality"""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    parts = topic.parts.filter(is_active=True).annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    )
    
    comprehensive_content = topic.comprehensive_contents.filter(is_active=True)
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
    
    context = {
        'subject': subject,
        'topic': topic,
        'parts': parts,
        'comprehensive_content': comprehensive_content,
        'all_categories': all_categories,
        'subjects': subjects,
        'filtered_count': filtered_count,
        'filtered_questions': filtered_questions,
    }
    return render(request, 'qa/part_list.html', context)


def part_detail(request, subject_slug, topic_slug, part_slug):
    """Display questions for a part with pagination"""
    subject = get_object_or_404(Subject, slug=subject_slug, is_active=True)
    topic = get_object_or_404(Topic, slug=topic_slug, subject=subject, is_active=True)
    part = get_object_or_404(Part, slug=part_slug, topic=topic, is_active=True)
    
    questions_list = part.questions.filter(is_active=True).order_by('order', 'created_at')
    
    paginator = Paginator(questions_list, 10)
    page = request.GET.get('page')
    
    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)
    
    # Get comprehensive content for this part
    comprehensive_content = part.comprehensive_contents.filter(is_active=True)
    
    # Increment view count
    part.views = part.views + 1
    part.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        context = {'questions': questions}
        return render(request, 'qa/partials/question_items.html', context)
    
    context = {
        'subject': subject,
        'topic': topic,
        'part': part,
        'questions': questions,
        'comprehensive_content': comprehensive_content,
    }
    return render(request, 'qa/part_detail.html', context)


def search_questions(request):
    """Search questions across all subjects"""
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


def get_topics_api(request, subject_id):
    """API endpoint to get topics for a subject (AJAX)"""
    try:
        subject = Subject.objects.get(id=subject_id, is_active=True)
        topics = subject.topics.filter(is_active=True).annotate(
            parts_count=Count('parts', filter=Q(parts__is_active=True))
        ).order_by('order', 'name')
        
        topics_data = [
            {
                'id': topic.id,
                'name': topic.name,
                'slug': topic.slug,
                'parts_count': topic.parts_count,
            }
            for topic in topics
        ]
        
        return JsonResponse({
            'success': True,
            'subject_name': subject.name,
            'subject_slug': subject.slug,
            'topics': topics_data,
        })
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Subject not found'
        }, status=404)


# ============================================
# ADVANCED FILTER VIEWS
# ============================================

def advanced_question_filter(request):
    """Advanced filter page for questions"""
    form = AdvancedQuestionFilterForm(request.GET or None)
    questions = Question.objects.filter(is_active=True).select_related('part__topic__subject').prefetch_related('categories')
    
    # Apply filters
    if form.is_valid():
        # Date Range Filter (using published_date)
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if date_from:
            questions = questions.filter(published_date__date__gte=date_from)
        if date_to:
            questions = questions.filter(published_date__date__lte=date_to)
        
        # Category Filter (Multiple)
        categories = form.cleaned_data.get('categories')
        if categories:
            questions = questions.filter(categories__in=categories).distinct()
        
        # Subject Filter
        subject = form.cleaned_data.get('subject')
        if subject:
            questions = questions.filter(part__topic__subject=subject)
        
        # Topic Filter
        topic = form.cleaned_data.get('topic')
        if topic:
            questions = questions.filter(part__topic=topic)
        
        # Part Filter
        part = form.cleaned_data.get('part')
        if part:
            questions = questions.filter(part=part)
        
        # Question Type Filter
        question_type = form.cleaned_data.get('question_type')
        if question_type:
            questions = questions.filter(question_type=question_type)
        
        # Difficulty Filter
        difficulty = form.cleaned_data.get('difficulty')
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        
        # Tags Filter
        tags = form.cleaned_data.get('tags')
        if tags:
            tag_filter = Q()
            for tag in tags:
                tag_filter |= Q(tags__icontains=tag)
            questions = questions.filter(tag_filter).distinct()
        
        # Search Filter
        search = form.cleaned_data.get('search')
        if search:
            questions = questions.filter(
                Q(question__icontains=search) |
                Q(question_hi__icontains=search) |
                Q(answer__icontains=search) |
                Q(answer_hi__icontains=search)
            ).distinct()
        
        # Featured Only
        featured_only = form.cleaned_data.get('featured_only')
        if featured_only:
            questions = questions.filter(is_featured=True)
    
    # Order by published date (newest first)
    questions = questions.order_by('-published_date', '-created_at')
    
    # Pagination
    paginator = Paginator(questions, 20)
    page = request.GET.get('page')
    
    try:
        questions_page = paginator.page(page)
    except PageNotAnInteger:
        questions_page = paginator.page(1)
    except EmptyPage:
        questions_page = paginator.page(paginator.num_pages)
    
    # Get all categories for display
    all_categories = QuestionCategory.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'questions': questions_page,
        'all_categories': all_categories,
        'total_count': questions.count(),
        'title': 'Advanced Question Filter',
    }
    
    return render(request, 'qa/advanced_filter.html', context)


def get_topics_by_subject_api(request, subject_id):
    """API to get topics for a subject (for dynamic filtering)"""
    try:
        subject = Subject.objects.get(id=subject_id, is_active=True)
        topics = subject.topics.filter(is_active=True).values('id', 'name', 'slug')
        return JsonResponse({
            'success': True,
            'topics': list(topics)
        })
    except Subject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Subject not found'
        }, status=404)


def get_parts_by_topic_api(request, topic_id):
    """API to get parts for a topic (for dynamic filtering)"""
    try:
        topic = Topic.objects.get(id=topic_id, is_active=True)
        parts = topic.parts.filter(is_active=True).values('id', 'name', 'slug')
        return JsonResponse({
            'success': True,
            'parts': list(parts)
        })
    except Topic.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Topic not found'
        }, status=404)