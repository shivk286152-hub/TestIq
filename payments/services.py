# payments/services.py

from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import (
    PricingConfig,
    SubscriptionPlan,
    UserSubscription,
    UserContentAccess,
    Payment,
    TransactionLog
)


class PaymentService:
    """Core payment business logic"""
    
    @staticmethod
    def get_content_pricing(content_type, content_id, content_app='qa'):
        """Get pricing for content"""
        try:
            return PricingConfig.objects.get(
                content_type=content_type,
                content_id=content_id,
                content_app=content_app,
                is_active=True
            )
        except PricingConfig.DoesNotExist:
            return None
    
    @staticmethod
    def check_user_access(user, content_type, content_id, content_app='qa'):
        """Check if user has access to content"""
        if not user.is_authenticated:
            return False, 'Please login to access'
        
        # Check if content is free
        pricing = PaymentService.get_content_pricing(content_type, content_id, content_app)
        if not pricing or not pricing.is_locked:
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
        
        # Check if parent content has access (for hierarchical content)
        # For QA app: Subject → Topic → Part
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
        
        # For Exams app: Category → Subcategory → MockTest
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
        
        return False, 'Content locked - Requires payment'
    
    @staticmethod
    def grant_access(user, content_type, content_id, content_app='qa', access_type='purchase', expiry_date=None):
        """Grant access to content"""
        access, created = UserContentAccess.objects.get_or_create(
            user=user,
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            defaults={
                'access_type': access_type,
                'status': 'active',
                'expiry_date': expiry_date,
            }
        )
        
        if not created:
            access.status = 'active'
            if expiry_date:
                access.expiry_date = expiry_date
            access.save()
        
        # Log
        TransactionLog.objects.create(
            user=user,
            action='access_granted',
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            details={'access_type': access_type}
        )
        
        return access
    
    @staticmethod
    def lock_content(content_type, content_id, content_app='qa', price=Decimal('99.00')):
        """Lock content with price"""
        pricing, created = PricingConfig.objects.get_or_create(
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            defaults={
                'price': price,
                'is_locked': True,
                'is_active': True
            }
        )
        
        if not created:
            pricing.price = price
            pricing.is_locked = True
            pricing.is_active = True
            pricing.save()
        
        TransactionLog.objects.create(
            action='content_locked',
            content_type=content_type,
            content_id=content_id,
            content_app=content_app,
            details={'price': str(price)}
        )
        
        return pricing


class SubscriptionService:
    """Subscription management"""
    
    @staticmethod
    def create_subscription(user, plan):
        """Create a new subscription"""
        # Deactivate old subscriptions
        UserSubscription.objects.filter(
            user=user,
            status='active'
        ).update(status='expired')
        
        expiry_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
        
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            expiry_date=expiry_date,
            status='active'
        )
        
        # Grant access to all locked content for this app
        apps = ['exams', 'qa'] if plan.applies_to == 'all' else [plan.applies_to]
        for app in apps:
            locked_contents = PricingConfig.objects.filter(
                content_app=app,
                is_locked=True,
                is_active=True
            )
            for content in locked_contents:
                # Check if user already has access
                if not UserContentAccess.objects.filter(
                    user=user,
                    content_type=content.content_type,
                    content_id=content.content_id,
                    content_app=content.content_app,
                    status='active'
                ).exists():
                    UserContentAccess.objects.create(
                        user=user,
                        content_type=content.content_type,
                        content_id=content.content_id,
                        content_app=content.content_app,
                        access_type='subscription',
                        status='active',
                        expiry_date=expiry_date
                    )
        
        TransactionLog.objects.create(
            user=user,
            action='subscription_created',
            details={
                'plan': plan.name,
                'duration': plan.duration,
                'price': str(plan.price),
                'expiry': expiry_date.isoformat()
            }
        )
        
        return subscription
    
    @staticmethod
    def cancel_subscription(user):
        """Cancel user's active subscription"""
        try:
            subscription = UserSubscription.objects.get(
                user=user,
                status='active',
                expiry_date__gt=timezone.now()
            )
            subscription.status = 'cancelled'
            subscription.save()
            
            TransactionLog.objects.create(
                user=user,
                action='subscription_cancelled',
                details={'plan': subscription.plan.name}
            )
            return True
        except UserSubscription.DoesNotExist:
            return False