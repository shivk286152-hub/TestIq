# payments/urls.py

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # ✅ Short URLs - redirect to full content type
    path('locked/<str:content_type>/<int:content_id>/', views.redirect_to_locked, name='locked_short'),
    
    # ✅ Main locked content URL (used by templates)
    path('locked/<str:content_type>/<int:content_id>/', views.locked_content, name='locked_content'),
    
    # ✅ Full URLs - Direct access with specific content types
    path('locked/qa_subject/<int:content_id>/', views.locked_content, {'content_type': 'qa_subject'}, name='locked_qa_subject'),
    path('locked/qa_topic/<int:content_id>/', views.locked_content, {'content_type': 'qa_topic'}, name='locked_qa_topic'),
    path('locked/qa_part/<int:content_id>/', views.locked_content, {'content_type': 'qa_part'}, name='locked_qa_part'),
    path('locked/exam_category/<int:content_id>/', views.locked_content, {'content_type': 'exam_category'}, name='locked_exam_category'),
    path('locked/exam_subcategory/<int:content_id>/', views.locked_content, {'content_type': 'exam_subcategory'}, name='locked_exam_subcategory'),
    path('locked/exam_mocktest/<int:content_id>/', views.locked_content, {'content_type': 'exam_mocktest'}, name='locked_exam_mocktest'),
    
    # ✅ Purchase
    path('purchase/<str:content_type>/<int:content_id>/', views.purchase_content, name='purchase_content'),
    path('purchase/history/', views.purchase_history, name='purchase_history'),
    path('purchase/success/<str:payment_id>/', views.purchase_success, name='purchase_success'),
    
    # ✅ Subscription
    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/create/<int:plan_id>/', views.create_subscription, name='create_subscription'),
    path('subscription/status/', views.subscription_status, name='subscription_status'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # ✅ Admin
    path('admin/manage-pricing/', views.manage_pricing, name='manage_pricing'),
    path('admin/dashboard/', views.payment_dashboard, name='payment_dashboard'),
    
    # ✅ API
    path('api/check-access/', views.check_access_api, name='check_access_api'),
    path('api/content-status/<str:content_type>/<int:content_id>/', views.content_status_api, name='content_status_api'),
    path('my-dashboard/', views.user_dashboard, name='user_dashboard'),
]