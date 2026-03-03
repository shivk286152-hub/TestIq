from django.urls import path
from . import views

app_name = "ExamNotification"

urlpatterns = [
    # LIST PAGE
    path("info/", views.notification_list, name="notification_list"),

    # DETAIL PAGE
    path("<int:pk>/", views.notification_detail, name="notification_detail"),
]
