from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    # path('curriculum/', include('curriculum.urls')), 
    path('', include('exams.urls')),
    path('notification/', include('ExamNotification.urls')),
    path('user/', include('User.urls')),
    path('current-affairs/', include('CurrentAffairs.urls')),
    # your app URLs
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('subject-mocktests/', include('subject_mocktests.urls')), 
   
   

    # ... your other URLs

]

# THIS IS CRITICAL FOR MEDIA FILES IN DEVELOPMENT
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)