# exams/urls.py
from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
     # subcategory → tests
    path("subcategory/<int:subcategory_id>/", views.subcategory_detail, name="subcategory_detail"),
    path( 'start/<int:mocktest_id>/',views.start_test,name='start_test'),
    # urls.py
    path('mocktest/<int:pk>/', views.mocktest_detail, name='mocktest_detail'),
    path(
    "attempt/<int:mocktest_id>/",
    views.attempt_test,
    name="attempt_test"),

    path("dashboard/", views.dashboard, name="dashboard"),
    
 
    path("dashboard/", views.dashboard, name="dashboard"),

    # Result dashboard (after submit)
    path(
        "mocktest/result/<int:attempt_id>/",
        views.result_dashboard,
        name="result_dashboard"
    ),
    
    path(
    "mocktest/<int:mocktest_id>/submit/",
    views.submit_test,
    name="submit_test"
),
   path('attempt/<int:mocktest_id>/ajax_question/', views.ajax_question, name='ajax_question'),
    path("save-answer/", views.save_answer, name="save_answer"),

    
    path(
    "mocktest/<int:mocktest_id>/submit/",
    views.submit_test,
    name="submit_test"
),
    path("attempt/<int:mocktest_id>/", views.attempt_test, name="attempt_test"),
    path("submit/<int:mocktest_id>/", views.submit_test, name="submit_test"),
    path("result/<int:attempt_id>/", views.result_dashboard, name="result_dashboard"),
    # path("attempt/<int:mocktest_id>/", views.attempt_test, name="attempt_test"),
    # path("mocktest/<int:mocktest_id>/submit/", views.submit_test, name="submit_test"),
    # path("dashboard/", views.dashboard, name="dashboard"),
    # path("start/<int:mocktest_id>/", views.start_test, name="start_test"),
    # path("attempt/<int:attempt_id>/", views.attempt_test, name="attempt_test"),
    # path("submit/<int:attempt_id>/", views.submit_test, name="submit_test"),
    # path("result/<int:attempt_id>/", views.mock_result, name="mock_result"),
]