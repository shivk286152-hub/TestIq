
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('exams.urls', 'exams'), namespace='exams')),

    path("accounts/", include("accounts.urls")),
    path("notification/", include("ExamNotification.urls")),
    path("profile/", include("User.urls")),
    path('current-affairs/', include('CurrentAffairs.urls')),
    
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


