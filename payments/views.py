# payments/views.py - Complete Fixed Version

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from decimal import Decimal
import logging

from .models import (
    PricingConfig,
    SubscriptionPlan,
    UserSubscription,
    UserContentAccess,
    Payment,
    TransactionLog
)

logger = logging.getLogger(__name__)


# ============================================
# ✅ HELPER: GET CONTENT OBJECT
# ============================================

def get_content_object(content_type, content_id):
    """Get content object from any app"""
    # ✅ QA APP - Support both short and full content types
    if content_type in ['qa_subject', 'subject']:
        try:
            from QA.models import Subject
            return Subject.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    if content_type in ['qa_topic', 'topic']:
        try:
            from QA.models import Topic
            return Topic.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    if content_type in ['qa_part', 'part']:
        try:
            from QA.models import Part
            return Part.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    # ✅ EXAMS APP
    if content_type in ['exam_category', 'category']:
        try:
            from exams.models import ExamCategory
            return ExamCategory.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    if content_type in ['exam_subcategory', 'subcategory']:
        try:
            from exams.models import SubCategory
            return SubCategory.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    if content_type in ['exam_mocktest', 'mocktest']:
        try:
            from exams.models import MockTest
            return MockTest.objects.get(id=content_id, is_active=True)
        except:
            pass
    
    return None


# ============================================
# ✅ HELPER: GET CONTENT NAME
# ============================================

def get_content_name(content_obj):
    """Get name from content object"""
    if hasattr(content_obj, 'name'):
        return content_obj.name
    elif hasattr(content_obj, 'title'):
        return content_obj.title
    else:
        return str(content_obj)


# ============================================
# ✅ HELPER: GET CONTENT TYPE DISPLAY
# ============================================

def get_content_type_display(content_type):
    """Get display name for content type"""
    mapping = {
        'qa_subject': 'Subject',
        'qa_topic': 'Topic',
        'qa_part': 'Part',
        'subject': 'Subject',
        'topic': 'Topic',
        'part': 'Part',
        'exam_category': 'Category',
        'exam_subcategory': 'Subcategory',
        'exam_mocktest': 'Mock Test',
        'category': 'Category',
        'subcategory': 'Subcategory',
        'mocktest': 'Mock Test',
    }
    return mapping.get(content_type, 'Content')


# ============================================
# ✅ HELPER: GET CONTENT APP
# ============================================

def get_content_app(content_type):
    """Get app name from content type"""
    if content_type.startswith('exam_') or content_type in ['category', 'subcategory', 'mocktest']:
        return 'exams'
    return 'qa'


# ============================================
# ✅ HELPER: GET REDIRECT URL
# ============================================

def get_redirect_url(content_type, content_id):
    """Get redirect URL based on content type"""
    try:
        # ✅ QA APP
        if content_type in ['qa_subject', 'subject']:
            from QA.models import Subject
            obj = Subject.objects.get(id=content_id, is_active=True)
            return reverse('qa:topic_list', kwargs={'subject_slug': obj.slug})
        
        if content_type in ['qa_topic', 'topic']:
            from QA.models import Topic
            obj = Topic.objects.get(id=content_id, is_active=True)
            return reverse('qa:part_list', kwargs={
                'subject_slug': obj.subject.slug,
                'topic_slug': obj.slug
            })
        
        if content_type in ['qa_part', 'part']:
            from QA.models import Part
            obj = Part.objects.get(id=content_id, is_active=True)
            return reverse('qa:part_detail', kwargs={
                'subject_slug': obj.topic.subject.slug,
                'topic_slug': obj.topic.slug,
                'part_slug': obj.slug
            })
        
        # ✅ EXAMS APP
        if content_type in ['exam_category', 'category']:
            from exams.models import ExamCategory
            obj = ExamCategory.objects.get(id=content_id, is_active=True)
            return reverse('exams:category_detail', kwargs={'slug': obj.slug})
        
        if content_type in ['exam_subcategory', 'subcategory']:
            from exams.models import SubCategory
            obj = SubCategory.objects.get(id=content_id, is_active=True)
            return reverse('exams:subcategory_detail', kwargs={'subcategory_id': obj.id})
        
        if content_type in ['exam_mocktest', 'mocktest']:
            return reverse('exams:pretest_detail', kwargs={'mocktest_id': content_id})
        
    except Exception as e:
        logger.error(f"Redirect URL error: {e}")
    
    return None


# ============================================
# ✅ HELPER: REDIRECT TO CONTENT
# ============================================

def redirect_to_content(content_type, content_id):
    """Redirect to the actual content page after purchase"""
    try:
        # ✅ QA APP
        if content_type in ['qa_subject', 'subject']:
            from QA.models import Subject
            obj = Subject.objects.get(id=content_id, is_active=True)
            return redirect('qa:topic_list', subject_slug=obj.slug)
        
        if content_type in ['qa_topic', 'topic']:
            from QA.models import Topic
            obj = Topic.objects.get(id=content_id, is_active=True)
            return redirect('qa:part_list', 
                          subject_slug=obj.subject.slug, 
                          topic_slug=obj.slug)
        
        if content_type in ['qa_part', 'part']:
            from QA.models import Part
            obj = Part.objects.get(id=content_id, is_active=True)
            return redirect('qa:part_detail', 
                          subject_slug=obj.topic.subject.slug, 
                          topic_slug=obj.topic.slug, 
                          part_slug=obj.slug)
        
        # ✅ EXAMS APP
        if content_type in ['exam_category', 'category']:
            from exams.models import ExamCategory
            obj = ExamCategory.objects.get(id=content_id, is_active=True)
            return redirect('exams:category_detail', slug=obj.slug)
        
        if content_type in ['exam_subcategory', 'subcategory']:
            from exams.models import SubCategory
            obj = SubCategory.objects.get(id=content_id, is_active=True)
            return redirect('exams:subcategory_detail', subcategory_id=obj.id)
        
        if content_type in ['exam_mocktest', 'mocktest']:
            return redirect('exams:pretest_detail', mocktest_id=content_id)
        
    except Exception as e:
        logger.error(f"Redirect error: {e}")
    
    # ✅ Fallback
    if content_type.startswith('qa_') or content_type in ['subject', 'topic', 'part']:
        return redirect('qa:subject_list')
    return redirect('exams:home')


# ============================================
# ✅ REDIRECT TO LOCKED (for short URLs)
# ============================================

def redirect_to_locked(request, content_type, content_id):
    """Redirect short URLs to full URLs with correct content type"""
    # Map short content types to full content types
    mapping = {
        'subject': 'qa_subject',
        'topic': 'qa_topic',
        'part': 'qa_part',
        'category': 'exam_category',
        'subcategory': 'exam_subcategory',
        'mocktest': 'exam_mocktest',
    }
    
    full_content_type = mapping.get(content_type, content_type)
    
    # Directly call locked_content with the mapped content type
    return locked_content(request, full_content_type, content_id)


# ============================================
# ✅ 1. LOCKED CONTENT VIEW
# ============================================

def locked_content(request, content_type, content_id):
    """Show locked content page"""
    content_obj = get_content_object(content_type, content_id)
    content_app = get_content_app(content_type)
    
    if content_obj:
        content_name = get_content_name(content_obj)
    else:
        content_name = f"Content #{content_id}"
    
    # ✅ Get pricing
    pricing = PricingConfig.objects.filter(
        content_type=content_type,
        content_id=content_id,
        is_active=True
    ).first()
    
    if not pricing:
        # Try with mapped content type
        mapped_type = {
            'subject': 'qa_subject',
            'topic': 'qa_topic',
            'part': 'qa_part',
            'category': 'exam_category',
            'subcategory': 'exam_subcategory',
            'mocktest': 'exam_mocktest',
        }.get(content_type, content_type)
        
        pricing = PricingConfig.objects.filter(
            content_type=mapped_type,
            content_id=content_id,
            is_active=True
        ).first()
        
        if not pricing:
            pricing = PricingConfig.objects.create(
                content_type=mapped_type,
                content_id=content_id,
                content_app=content_app,
                content_name=content_name,
                price=Decimal('99.00'),
                is_locked=True,
                is_active=True
            )
    
    # ✅ Check user access
    has_access = False
    is_subscribed = False
    
    if request.user.is_authenticated:
        is_subscribed = UserSubscription.objects.filter(
            user=request.user, status='active', expiry_date__gt=timezone.now()
        ).exists()
        
        if is_subscribed:
            has_access = True
        else:
            # Check with both content types
            content_types_to_check = [content_type]
            if content_type in ['subject', 'topic', 'part']:
                content_types_to_check.append('qa_' + content_type)
            elif content_type in ['category', 'subcategory', 'mocktest']:
                content_types_to_check.append('exam_' + content_type)
            
            for ct in content_types_to_check:
                if UserContentAccess.objects.filter(
                    user=request.user,
                    content_type=ct,
                    content_id=content_id,
                    content_app=content_app,
                    status='active'
                ).exists():
                    has_access = True
                    break
    
    # ✅ If content is not locked, free access
    if not pricing.is_locked:
        has_access = True
    
    # ✅ If user has access, redirect to content page
    if has_access:
        messages.info(request, f'You already have access to "{content_name}"!')
        redirect_url = get_redirect_url(content_type, content_id)
        if redirect_url:
            return redirect(redirect_url)
        else:
            # Fallback
            if content_app == 'qa':
                return redirect('qa:subject_list')
            else:
                return redirect('exams:home')
    
    # ✅ Get subscription plans
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    # ✅ Content type display
    content_type_display = get_content_type_display(content_type)
    
    # ✅ Get redirect URL for the "View Content" button
    redirect_url = get_redirect_url(content_type, content_id)
    
    context = {
        'content_type': content_type,
        'content_id': content_id,
        'content_name': content_name,
        'content_type_display': content_type_display,
        'price': pricing.price,
        'has_access': has_access,
        'is_subscribed': is_subscribed,
        'plans': plans,
        'user': request.user,
        'redirect_url': redirect_url,
        'is_locked': pricing.is_locked,
    }
    
    return render(request, 'payments/locked_content.html', context)


# ============================================
# ✅ 2. PURCHASE CONTENT VIEW
# ============================================

@login_required
def purchase_content(request, content_type, content_id):
    """Purchase content"""
    # Map content type if needed
    mapped_type = {
        'subject': 'qa_subject',
        'topic': 'qa_topic',
        'part': 'qa_part',
        'category': 'exam_category',
        'subcategory': 'exam_subcategory',
        'mocktest': 'exam_mocktest',
    }.get(content_type, content_type)
    
    pricing = get_object_or_404(
        PricingConfig,
        content_type=mapped_type,
        content_id=content_id,
        is_active=True
    )
    
    content_app = pricing.content_app or get_content_app(content_type)
    content_name = pricing.content_name or f"Content #{content_id}"
    
    # ✅ Check if already has access
    if UserContentAccess.objects.filter(
        user=request.user,
        content_type=mapped_type,
        content_id=content_id,
        content_app=content_app,
        status='active'
    ).exists():
        messages.info(request, 'You already have access!')
        return redirect_to_content(content_type, content_id)
    
    # ✅ Check if user has subscription
    if UserSubscription.objects.filter(
        user=request.user, status='active', expiry_date__gt=timezone.now()
    ).exists():
        UserContentAccess.objects.get_or_create(
            user=request.user,
            content_type=mapped_type,
            content_id=content_id,
            content_app=content_app,
            defaults={'access_type': 'subscription', 'status': 'active'}
        )
        messages.success(request, 'Access granted via subscription!')
        return redirect_to_content(content_type, content_id)
    
    if request.method == 'POST':
        # ✅ Create payment record
        payment = Payment.objects.create(
            user=request.user,
            order_id=f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{request.user.id}",
            amount=pricing.price,
            total_amount=pricing.price,
            payment_method='demo',
            status='completed',
            completed_at=timezone.now(),
            items=[{
                'content_type': mapped_type,
                'content_id': content_id,
                'content_app': content_app,
                'content_name': content_name,
                'price': str(pricing.price),
            }]
        )
        
        # ✅ Grant access
        UserContentAccess.objects.create(
            user=request.user,
            content_type=mapped_type,
            content_id=content_id,
            content_app=content_app,
            access_type='purchase',
            status='active'
        )
        
        messages.success(request, f'Successfully purchased "{content_name}"!')
        return redirect_to_content(content_type, content_id)
    
    context = {
        'content_type': content_type,
        'content_id': content_id,
        'content_name': content_name,
        'price': pricing.price,
    }
    
    return render(request, 'payments/purchase.html', context)


# ============================================
# ✅ 3. SUBSCRIPTION PLANS VIEW
# ============================================

@login_required
def subscription_plans(request):
    """Show subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    current_sub = UserSubscription.objects.filter(
        user=request.user, status='active', expiry_date__gt=timezone.now()
    ).first()
    
    context = {
        'plans': plans,
        'current_subscription': current_sub,
        'is_subscribed': current_sub is not None,
    }
    return render(request, 'payments/subscription_plans.html', context)


# ============================================
# ✅ 4. CREATE SUBSCRIPTION VIEW
# ============================================

@login_required
def create_subscription(request, plan_id):
    """Create subscription"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    if request.method == 'POST':
        # Deactivate old subscriptions
        UserSubscription.objects.filter(user=request.user, status='active').update(status='expired')
        
        # Create new subscription
        expiry_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
        UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            expiry_date=expiry_date,
            status='active'
        )
        
        # ✅ Grant access to ALL locked content
        locked_contents = PricingConfig.objects.filter(is_locked=True, is_active=True)
        for content in locked_contents:
            UserContentAccess.objects.get_or_create(
                user=request.user,
                content_type=content.content_type,
                content_id=content.content_id,
                content_app=content.content_app,
                defaults={'access_type': 'subscription', 'status': 'active'}
            )
        
        messages.success(request, f'Successfully subscribed to {plan.name}!')
        return redirect('payments:subscription_status')
    
    context = {'plan': plan}
    return render(request, 'payments/create_subscription.html', context)


# ============================================
# ✅ 5. SUBSCRIPTION STATUS VIEW
# ============================================

@login_required
def subscription_status(request):
    """View subscription status"""
    subscriptions = UserSubscription.objects.filter(user=request.user).order_by('-created_at')
    current_sub = subscriptions.filter(status='active', expiry_date__gt=timezone.now()).first()
    
    context = {
        'subscriptions': subscriptions,
        'current_subscription': current_sub,
    }
    return render(request, 'payments/subscription_status.html', context)


# ============================================
# ✅ 6. CANCEL SUBSCRIPTION VIEW
# ============================================

@login_required
def cancel_subscription(request):
    """Cancel subscription"""
    if request.method == 'POST':
        sub = UserSubscription.objects.filter(
            user=request.user, status='active', expiry_date__gt=timezone.now()
        ).first()
        if sub:
            sub.status = 'cancelled'
            sub.save()
            messages.success(request, 'Subscription cancelled.')
        else:
            messages.error(request, 'No active subscription found.')
    return redirect('payments:subscription_status')


# ============================================
# ✅ 7. PURCHASE HISTORY VIEW
# ============================================

@login_required
def purchase_history(request):
    """View purchase history"""
    purchases = UserContentAccess.objects.filter(user=request.user).order_by('-created_at')
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'purchases': purchases,
        'payments': payments,
    }
    return render(request, 'payments/purchase_history.html', context)


# ============================================
# ✅ 8. PURCHASE SUCCESS VIEW
# ============================================

@login_required
def purchase_success(request, payment_id):
    """Purchase success page"""
    payment = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    context = {'payment': payment}
    return render(request, 'payments/purchase_success.html', context)


# ============================================
# ✅ 9. MANAGE PRICING VIEW (ADMIN)
# ============================================

@staff_member_required
def manage_pricing(request):
    """Admin panel to manage pricing"""
    all_content = []
    
    # EXAMS APP
    try:
        from exams.models import ExamCategory, SubCategory, MockTest
        
        for cat in ExamCategory.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='exam_category', content_id=cat.id).first()
            all_content.append({
                'id': cat.id,
                'name': cat.name,
                'app': 'exams',
                'type': 'exam_category',
                'type_display': 'Category',
                'parent': None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
        
        for sub in SubCategory.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='exam_subcategory', content_id=sub.id).first()
            all_content.append({
                'id': sub.id,
                'name': sub.name,
                'app': 'exams',
                'type': 'exam_subcategory',
                'type_display': 'Subcategory',
                'parent': sub.category.name if sub.category else None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
        
        for test in MockTest.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='exam_mocktest', content_id=test.id).first()
            all_content.append({
                'id': test.id,
                'name': test.title,
                'app': 'exams',
                'type': 'exam_mocktest',
                'type_display': 'Mock Test',
                'parent': test.subcategory.name if test.subcategory else None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
    except:
        pass
    
    # QA APP
    try:
        from QA.models import Subject, Topic, Part
        
        for subject in Subject.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='qa_subject', content_id=subject.id).first()
            all_content.append({
                'id': subject.id,
                'name': subject.name,
                'app': 'qa',
                'type': 'qa_subject',
                'type_display': 'Subject',
                'parent': None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
        
        for topic in Topic.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='qa_topic', content_id=topic.id).first()
            all_content.append({
                'id': topic.id,
                'name': topic.name,
                'app': 'qa',
                'type': 'qa_topic',
                'type_display': 'Topic',
                'parent': topic.subject.name if topic.subject else None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
        
        for part in Part.objects.filter(is_active=True):
            pricing = PricingConfig.objects.filter(content_type='qa_part', content_id=part.id).first()
            all_content.append({
                'id': part.id,
                'name': part.name,
                'app': 'qa',
                'type': 'qa_part',
                'type_display': 'Part',
                'parent': f"{part.topic.subject.name} → {part.topic.name}" if part.topic and part.topic.subject else None,
                'is_locked': pricing.is_locked if pricing else False,
                'price': pricing.price if pricing else 0,
            })
    except:
        pass
    
    if request.method == 'POST':
        action = request.POST.get('action')
        content_type = request.POST.get('content_type')
        content_id = request.POST.get('content_id')
        price = request.POST.get('price', '0')
        
        if content_type and content_id:
            content_app = 'exams' if content_type.startswith('exam_') else 'qa'
            pricing, _ = PricingConfig.objects.get_or_create(
                content_type=content_type,
                content_id=content_id,
                content_app=content_app
            )
            
            if action == 'lock':
                pricing.price = Decimal(price) if price else Decimal('99.00')
                pricing.is_locked = True
                pricing.is_active = True
                pricing.save()
                messages.success(request, f'✅ Locked with price ₹{pricing.price}')
            elif action == 'unlock':
                pricing.is_locked = False
                pricing.price = Decimal('0')
                pricing.save()
                messages.success(request, '✅ Unlocked successfully')
            elif action == 'update_price':
                pricing.price = Decimal(price) if price else Decimal('0')
                pricing.save()
                messages.success(request, f'✅ Price updated to ₹{pricing.price}')
        
        return redirect('payments:manage_pricing')
    
    context = {
        'all_content': all_content,
        'total_content': len(all_content),
        'locked_count': sum(1 for c in all_content if c['is_locked']),
    }
    return render(request, 'payments/manage_pricing.html', context)


# ============================================
# ✅ 10. PAYMENT DASHBOARD VIEW (ADMIN)
# ============================================

@staff_member_required
def payment_dashboard(request):
    """Admin payment dashboard"""
    from django.db.models import Sum
    
    total_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'total_revenue': total_revenue,
        'total_payments': Payment.objects.filter(status='completed').count(),
        'total_subscriptions': UserSubscription.objects.filter(status='active').count(),
        'total_locked': PricingConfig.objects.filter(is_locked=True).count(),
    }
    return render(request, 'payments/admin_dashboard.html', context)


# ============================================
# ✅ 11. CHECK ACCESS API
# ============================================

def check_access_api(request):
    """API to check content access"""
    content_type = request.GET.get('content_type')
    content_id = request.GET.get('content_id')
    content_app = request.GET.get('content_app', 'qa')
    
    if not content_type or not content_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    pricing = PricingConfig.objects.filter(
        content_type=content_type,
        content_id=content_id,
        is_active=True
    ).first()
    
    is_locked = pricing.is_locked if pricing else False
    price = float(pricing.price) if pricing else 0
    
    can_access = False
    if request.user.is_authenticated:
        if UserSubscription.objects.filter(
            user=request.user, status='active', expiry_date__gt=timezone.now()
        ).exists():
            can_access = True
        if not can_access:
            if UserContentAccess.objects.filter(
                user=request.user,
                content_type=content_type,
                content_id=content_id,
                content_app=content_app,
                status='active'
            ).exists():
                can_access = True
    
    if not is_locked:
        can_access = True
    
    return JsonResponse({
        'can_access': can_access,
        'is_locked': is_locked,
        'price': price,
        'requires_login': not request.user.is_authenticated,
    })


# ============================================
# ✅ 12. CONTENT STATUS API
# ============================================

def content_status_api(request, content_type, content_id):
    """API to get content status"""
    content_app = request.GET.get('content_app', 'qa')
    
    pricing = PricingConfig.objects.filter(
        content_type=content_type,
        content_id=content_id,
        is_active=True
    ).first()
    
    if not pricing:
        return JsonResponse({
            'status': 'free',
            'is_free': True,
            'is_locked': False,
            'price': 0,
        })
    
    can_access = False
    if request.user.is_authenticated:
        if UserSubscription.objects.filter(
            user=request.user, status='active', expiry_date__gt=timezone.now()
        ).exists():
            can_access = True
        if not can_access:
            if UserContentAccess.objects.filter(
                user=request.user,
                content_type=content_type,
                content_id=content_id,
                content_app=content_app,
                status='active'
            ).exists():
                can_access = True
    
    return JsonResponse({
        'status': 'locked' if pricing.is_locked else 'free',
        'is_free': not pricing.is_locked,
        'is_locked': pricing.is_locked,
        'price': float(pricing.price),
        'discount_price': float(pricing.get_final_price()),
        'has_discount': pricing.discount_percentage > 0,
        'discount_percentage': float(pricing.discount_percentage),
        'can_access': can_access,
        'requires_login': not request.user.is_authenticated,
    })

# payments/views.py - Add this function at the end

@login_required
def user_dashboard(request):
    """User payment dashboard - Show all payment info"""
    
    from django.db.models import Sum
    
    user = request.user
    
    # ✅ 1. User Content Access (Purchased items)
    purchases = UserContentAccess.objects.filter(
        user=user
    ).order_by('-created_at')
    
    # ✅ 2. Payment history
    payments = Payment.objects.filter(
        user=user
    ).order_by('-created_at')
    
    # ✅ 3. Subscription status
    current_subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        expiry_date__gt=timezone.now()
    ).first()
    
    # ✅ 4. Subscription history
    subscription_history = UserSubscription.objects.filter(
        user=user
    ).order_by('-created_at')
    
    # ✅ 5. Stats
    total_purchases = purchases.filter(access_type='purchase').count()
    total_free_access = purchases.filter(access_type='free').count()
    total_spent = Payment.objects.filter(user=user, status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # ✅ 6. Locked content available for purchase
    locked_content = PricingConfig.objects.filter(
        is_locked=True,
        is_active=True
    ).exclude(
        content_id__in=UserContentAccess.objects.filter(
            user=user,
            status='active'
        ).values_list('content_id', flat=True)
    )[:10]
    
    context = {
        'user': user,
        'purchases': purchases,
        'payments': payments,
        'current_subscription': current_subscription,
        'subscription_history': subscription_history,
        'total_purchases': total_purchases,
        'total_free_access': total_free_access,
        'total_spent': total_spent,
        'locked_content': locked_content,
        'has_subscription': current_subscription is not None,
    }
    
    return render(request, 'payments/user_dashboard.html', context)