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

    # NEW: Pretest detail page (instructions, terms, language)
    path("test/<int:mocktest_id>/pretest/", views.pretest_detail, name="pretest_detail"),

    # Start test page (handles form submission from pretest)
    path("test/<int:mocktest_id>/start/", views.start_test, name="start_test"),

    # Attempt test (main exam page)
    path("attempt/<int:mocktest_id>/", views.attempt_test, name="attempt_test"),

    # AJAX question loader
    path(
        "attempt/<int:mocktest_id>/ajax-question/",
        views.ajax_question,
        name="ajax_question"
    ),

    # Save answer
    path("save-answer/", views.save_answer, name="save_answer"),

    # Submit test
    path(
        "mocktest/<int:mocktest_id>/submit/",
        views.submit_test,
        name="submit_test"
    ),

    # Result page
    path(
        "result/<int:attempt_id>/",
        views.result_dashboard,
        name="result_dashboard"
    ),

    # Dashboard
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
    # path('generate-pdf/', views.generate_pdf, name='generate_pdf'),

]