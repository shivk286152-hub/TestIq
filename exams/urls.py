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

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
]
