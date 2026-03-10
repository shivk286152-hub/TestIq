from django.urls import path
from . import views

app_name = 'subject_mocktests'

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('subject/<slug:slug>/', views.subject_detail, name='subject_detail'),
    path('pretest/<int:mocktest_id>/', views.pretest_page, name='pretest_page'),
    path('start/<int:mocktest_id>/', views.start_test, name='start_test'),
]