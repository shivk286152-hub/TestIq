from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [

    # Home
    path("", views.home, name="home"),
    path('about/', views.about, name='about'),

    # Category → Subcategory → Tests
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("subcategory/<int:subcategory_id>/", views.subcategory_detail, name="subcategory_detail"),

    # Mocktest detail
    path("mocktest/<int:pk>/", views.mocktest_detail, name="mocktest_detail"),

    # Pretest detail page
    path("test/<int:mocktest_id>/pretest/", views.pretest_detail, name="pretest_detail"),
    path("test/<int:mocktest_id>/start/", views.start_test, name="start_test"),
    path("attempt/<int:mocktest_id>/", views.attempt_test, name="attempt_test"),
    path("attempt/<int:mocktest_id>/ajax-question/", views.ajax_question, name="ajax_question"),
    path("save-answer/", views.save_answer, name="save_answer"),
    path("mocktest/<int:mocktest_id>/submit/", views.submit_test, name="submit_test"),
    path("result/<int:attempt_id>/", views.result_dashboard, name="result_dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('rankings/<int:attempt_id>/', views.view_rankings, name='view_rankings'),
    path('detailed-analysis/<int:attempt_id>/', views.detailed_analysis, name='detailed_analysis'),
    
    # Testimonial URLs
    path('testimonial/submit/', views.submit_testimonial, name='submit_testimonial'),
    path('testimonial/<int:testimonial_id>/edit/', views.edit_testimonial, name='edit_testimonial'),
    path('testimonial/<int:testimonial_id>/delete/', views.delete_testimonial, name='delete_testimonial'),

    path('statistics/<int:attempt_id>/', views.test_statistics, name='test_statistics'),
    path('statistics/<int:attempt_id>/pdf/', views.download_statistics_pdf, name='download_statistics_pdf'),
    path('faq/', views.faq_page, name='faq_page'),
    
    # Contact URLs
    path('contact/', views.contact_page, name='contact_page'),
    path('contact/success/', views.contact_success, name='contact_success'),
    
    # Legal URLs - ADD THESE
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),

    # path('analytics/', views.advanced_analytics, name='advanced_analytics'),
    
    path('advanced-analytics/', views.advanced_analytics, name='advanced_analytics'),
    path('test-content/<int:test_id>/', views.get_test_content, name='get_test_content'),
]