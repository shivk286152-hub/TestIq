from django.urls import path
from . import views

urlpatterns = [
    path('', views.current_affairs_list, name='current_affairs_list'),
    path('<slug:slug>/', views.current_affairs_detail, name='current_affairs_detail'),
]
