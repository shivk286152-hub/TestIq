# payments/utils.py

from django.utils import timezone
from .models import PricingConfig, UserSubscription, UserContentAccess


def check_content_access(user, content_type, content_id, content_app='qa'):
    """Check if user has access to content - For use in other apps"""
    
    if not user.is_authenticated:
        return False, 'Please login to access'
    
    # Check if content is free
    try:
        pricing = PricingConfig.objects.get(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            is_active=True
        )
        if not pricing.is_locked:
            return True, 'Free content'
    except PricingConfig.DoesNotExist:
        return True, 'Free content'
    
    # Check subscription
    if UserSubscription.objects.filter(
        user=user,
        status='active',
        expiry_date__gt=timezone.now()
    ).exists():
        subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            expiry_date__gt=timezone.now()
        ).first()
        if subscription.plan.applies_to_app(content_app):
            return True, 'Subscription access'
    
    # Check direct purchase
    if UserContentAccess.objects.filter(
        user=user,
        content_type=content_type,
        content_id=content_id,
        content_app=content_app,
        status='active'
    ).exists():
        return True, 'Purchased access'
    
    # Check parent content access for hierarchical content
    if content_type == 'qa_part':
        try:
            from QA.models import Part
            part = Part.objects.get(id=content_id)
            if part.topic and part.topic.user_has_access(user):
                return True, 'Parent topic access'
            if part.topic.subject and part.topic.subject.user_has_access(user):
                return True, 'Parent subject access'
        except:
            pass
    
    if content_type == 'qa_topic':
        try:
            from QA.models import Topic
            topic = Topic.objects.get(id=content_id)
            if topic.subject and topic.subject.user_has_access(user):
                return True, 'Parent subject access'
        except:
            pass
    
    if content_type == 'exam_mocktest':
        try:
            from exams.models import MockTest
            mocktest = MockTest.objects.get(id=content_id)
            if mocktest.subcategory and mocktest.subcategory.user_has_access(user):
                return True, 'Parent subcategory access'
            if mocktest.subcategory and mocktest.subcategory.category and mocktest.subcategory.category.user_has_access(user):
                return True, 'Parent category access'
        except:
            pass
    
    if content_type == 'exam_subcategory':
        try:
            from exams.models import SubCategory
            subcategory = SubCategory.objects.get(id=content_id)
            if subcategory.category and subcategory.category.user_has_access(user):
                return True, 'Parent category access'
        except:
            pass
    
    # Check if content is locked
    try:
        pricing = PricingConfig.objects.get(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            is_active=True
        )
        if pricing.is_locked:
            return False, 'Content locked - Requires payment'
    except:
        pass
    
    return True, 'Free content'


def is_content_locked(content_type, content_id, content_app='qa'):
    """Check if content is locked"""
    try:
        pricing = PricingConfig.objects.get(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            is_active=True
        )
        return pricing.is_locked
    except PricingConfig.DoesNotExist:
        return False


def get_content_price(content_type, content_id, content_app='qa'):
    """Get content price"""
    try:
        pricing = PricingConfig.objects.get(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            is_active=True
        )
        return float(pricing.get_final_price())
    except PricingConfig.DoesNotExist:
        return 0