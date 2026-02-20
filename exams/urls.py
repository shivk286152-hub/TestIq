from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [

    # Home
    path("", views.home, name="home"),

    # Category → Subcategory → Tests
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("subcategory/<int:subcategory_id>/", views.subcategory_detail, name="subcategory_detail"),

    # Mocktest detail
    path("mocktest/<int:pk>/", views.mocktest_detail, name="mocktest_detail"),

    # Start test page
    path("start/<int:mocktest_id>/", views.start_test, name="start_test"),

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

<<<<<<< HEAD
    # ===== NEW RANKING & REVIEW URLS =====
    
    # Test Review
    path(
        "review/<int:attempt_id>/",
        views.test_review,
        name="test_review"
    ),
    
    # Save Question Feedback (AJAX)
    path(
        "save-question-feedback/",
        views.save_question_feedback,
        name="save_question_feedback"
    ),
    
    # Complete Review Session
    path(
        "review/complete/<int:session_id>/",
        views.complete_review_session,
        name="complete_review_session"
    ),
    
    # Rankings
    path("rankings/", views.rankings, name="rankings"),
    path("rankings/<int:test_id>/", views.test_rankings, name="test_rankings"),
    
    # Leaderboard
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    
    # User History & Performance
    path("my-attempts/", views.my_attempts, name="my_attempts"),
    path("my-performance/", views.my_performance, name="my_performance"),
    
    # Dashboard (already exists above)
    # path("dashboard/", views.dashboard, name="dashboard"),  # Already have this
]
=======
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    
    path('rankings/<int:attempt_id>/', views.view_rankings, name='view_rankings'),
     # ... existing URLs ...
    path('detailed-analysis/<int:attempt_id>/', views.detailed_analysis, name='detailed_analysis'),
]
>>>>>>> 90d6b74 (Updated Django project with models and admin configuration)
