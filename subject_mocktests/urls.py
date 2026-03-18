from django.urls import path
from . import views

app_name = 'subject_mocktests'

urlpatterns = [
    # Subject listing
    path('', views.subject_list, name='subject_list'),
    
    # Subject detail with topics and mock tests
    path('subject/<slug:subject_slug>/', views.subject_detail, name='subject_detail'),
    
    # Topic detail with mock tests
    path('topic/<int:topic_id>/', views.topic_detail, name='topic_detail'),
    
    # Mock test listing for subject/topic
    path('mocktests/<slug:subject_slug>/', views.mocktest_list, name='mocktest_list'),
    path('mocktests/topic/<int:topic_id>/', views.mocktest_list_by_topic, name='mocktest_list_by_topic'),
    
    # Mock test pretest page
    path('pretest/<int:mocktest_id>/', views.pretest_detail, name='pretest_detail'),
    
    # Start test (with language selection)
    path('start/<int:mocktest_id>/', views.start_test, name='start_test'),
    
    # Attempt test
    path('attempt/<int:mocktest_id>/', views.attempt_test, name='attempt_test'),
    
    # AJAX endpoints for test taking
    path('ajax/question/<int:mocktest_id>/', views.ajax_question, name='ajax_question'),
    path('save-answer/', views.save_answer, name='save_answer'),
    
    # Submit test
    path('submit/<int:mocktest_id>/', views.submit_test, name='submit_test'),
    
    # Results and analytics (reusing existing templates)
    path('result/<int:attempt_id>/', views.result_dashboard, name='result_dashboard'),
    path('analysis/<int:attempt_id>/', views.detailed_analysis, name='detailed_analysis'),
    path('statistics/<int:attempt_id>/', views.test_statistics, name='test_statistics'),
    path('rankings/<int:attempt_id>/', views.view_rankings, name='view_rankings'),
    
    # Dashboard for subject mock tests
    path('my-attempts/', views.subject_dashboard, name='subject_dashboard'),
]