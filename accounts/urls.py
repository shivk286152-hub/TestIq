from django.urls import path
from .views import register, user_login, user_logout,home

urlpatterns = [
    path("login/", user_login, name="login"),
    path("register/", register, name="register"),
    path("logout/", user_logout, name="logout"),
    path('home/', home, name='home'),
]