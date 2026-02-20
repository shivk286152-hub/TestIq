from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count
from datetime import datetime
from django.utils import timezone
from datetime import timedelta
from collections import Counter
from .models import CurrentAffairs, CurrentAffairsCategory
import random
from django.db.models import Count, Q
from django.http import JsonResponse
from django.template.loader import render_to_string

def current_affairs_list(request):
    """Main current affairs listing page"""
    
    # Get only published articles
    all_news = CurrentAffairs.objects.filter(status='published')
    
    # ===== TOP NEWS SECTION (Random 3) =====
    latest_news = list(all_news.order_by('-news_date')[:20])
    top_news = []
    if len(latest_news) >= 3:
        top_news = random.sample(latest_news, 3)
    else:
        top_news = latest_news
    
    # ===== FILTERS =====
    selected_category = request.GET.get('category')
    selected_category_display = None
    if selected_category:
        all_news = all_news.filter(category__slug=selected_category)
        try:
            category_obj = CurrentAffairsCategory.objects.get(slug=selected_category)
            selected_category_display = category_obj.name
        except CurrentAffairsCategory.DoesNotExist:
            pass
    
    selected_month = request.GET.get('month')
    if selected_month:
        try:
            month_date = datetime.strptime(selected_month, "%B %Y")
            all_news = all_news.filter(
                news_date__year=month_date.year,
                news_date__month=month_date.month
            )
        except ValueError:
            pass
    
    selected_date = request.GET.get('date')
    if selected_date:
        today = timezone.now().date()
        
        if selected_date == 'today':
            all_news = all_news.filter(news_date=today)
            selected_date = today.strftime("%Y-%m-%d")
        elif selected_date == 'yesterday':
            yesterday = today - timedelta(days=1)
            all_news = all_news.filter(news_date=yesterday)
            selected_date = yesterday.strftime("%Y-%m-%d")
        elif selected_date == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            all_news = all_news.filter(news_date__gte=start_of_week)
        elif selected_date == 'last_7_days':
            seven_days_ago = today - timedelta(days=7)
            all_news = all_news.filter(news_date__gte=seven_days_ago)
        else:
            try:
                filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                all_news = all_news.filter(news_date=filter_date)
            except (ValueError, TypeError):
                pass
    
    # ===== TRENDING TAGS =====
    all_tags = []
    news_for_tags = all_news[:100]
    for news in news_for_tags:
        if news.tags:
            tags = [tag.strip() for tag in news.tags.split(',') if tag.strip()]
            all_tags.extend(tags)
    
    tag_counter = Counter(all_tags)
    trending_tags = [tag for tag, count in tag_counter.most_common(10)]
    
    # ===== RECENT DATES =====
    today = timezone.now().date()
    recent_dates = []
    
    distinct_dates = all_news.filter(
        news_date__gte=today - timedelta(days=30)
    ).values_list('news_date', flat=True).distinct().order_by('-news_date')[:7]
    
    for date in distinct_dates:
        recent_dates.append(date)
    
    if len(recent_dates) < 7:
        for i in range(7):
            date = today - timedelta(days=i)
            if date not in recent_dates:
                recent_dates.append(date)
        recent_dates = sorted(recent_dates, reverse=True)[:7]
    
    # ===== PAGINATION =====
    paginator = Paginator(all_news, 3)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # ===== CHECK IF AJAX REQUEST =====
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Render only the news items and pagination for AJAX
        news_html = render_to_string('current_affairs/partials/news_items.html', {
            'page_obj': page_obj,
            'selected_category': selected_category,
            'selected_category_display': selected_category_display,
            'selected_month': selected_month,
            'selected_date': selected_date,
        }, request=request)
        
        pagination_html = render_to_string('current_affairs/partials/pagination.html', {
            'page_obj': page_obj,
            'selected_category': selected_category,
            'selected_month': selected_month,
            'selected_date': selected_date,
        }, request=request)
        
        return JsonResponse({
            'news_html': news_html,
            'pagination_html': pagination_html,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        })
    
    # ===== MONTHS LIST =====
    months_list = all_news.dates('news_date', 'month', order='DESC')
    formatted_months = []
    for month in months_list:
        formatted_months.append({
            'date': month,
            'display': month.strftime("%B %Y"),
            'count': all_news.filter(
                news_date__year=month.year,
                news_date__month=month.month
            ).count()
        })
    
    # ===== CATEGORIES WITH COUNTS =====
    categories = CurrentAffairsCategory.objects.filter(
        is_active=True,
        articles__status='published'
    ).annotate(
        news_count=Count('articles')
    ).filter(news_count__gt=0)
    
    # ===== EMPTY STATE HELPERS =====
    show_empty_toast = all_news.count() == 0 and (selected_date or selected_month or selected_category)
    
    previous_date = None
    next_date = None
    if selected_date and selected_date not in ['today', 'yesterday', 'this_week', 'last_7_days']:
        try:
            current_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            previous_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
            next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    
    current_month = today.strftime("%B %Y")
    
    context = {
        'top_news': top_news,
        'page_obj': page_obj,
        'months': formatted_months,
        'categories': categories,
        'selected_category': selected_category,
        'selected_category_display': selected_category_display,
        'selected_month': selected_month,
        'selected_date': selected_date,
        'trending_tags': trending_tags,
        'recent_dates': recent_dates,
        'show_empty_toast': show_empty_toast,
        'previous_date': previous_date,
        'next_date': next_date,
        'current_month': current_month,
    }
    
    return render(request, 'current_affairs/list.html', context)

def current_affairs_detail(request, slug):
    """Single news detail page"""
    news = get_object_or_404(CurrentAffairs, slug=slug, status='published')
    
    # Increment view count
    news.views_count += 1
    news.save(update_fields=['views_count'])
    
    # Get related news
    related_news = CurrentAffairs.objects.filter(
        status='published'
    ).exclude(
        id=news.id
    ).filter(
        Q(category=news.category) |
        Q(news_date__year=news.news_date.year,
          news_date__month=news.news_date.month)
    ).distinct()[:3]
    
    context = {
        'news': news,
        'related_news': related_news,
    }
    return render(request, 'current_affairs/detail.html', context)