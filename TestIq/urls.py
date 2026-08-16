from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Import from exams instead of accounts
from exams.views import home  # Changed this line
from accounts.views import user_login, user_logout, register, profile, change_password
from accounts.views import CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView, CustomPasswordResetCompleteView

urlpatterns = [
    # ===== ADMIN =====
    path('admin/', admin.site.urls),
    
    # ===== HOME =====
    # Home is now from exams.views.home
    path('', home, name='home'),
    path('home/', home, name='home_redirect'),
    
    # ===== AUTHENTICATION =====
    path('accounts/', include('accounts.urls')),
    
    # Direct authentication URLs
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('register/', register, name='register'),
    path('profile/', profile, name='profile'),
    path('change-password/', change_password, name='change_password'),
    
    # ===== PASSWORD RESET =====
    path('password-reset/', 
         CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('password-reset/done/', 
         CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', 
         CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
    
    # ===== YOUR APPS =====
    # Remove this line - we already have the home URL above
    path('', include('exams.urls')),  # COMMENT THIS OUT
    
    # Subject Mocktests
    path('subject-mocktests/', include('subject_mocktests.urls')),
    
    # Current Affairs
    path('current-affairs/', include('CurrentAffairs.urls')),
    
    # QA (Questions & Answers)
    path('qa/', include('QA.urls', namespace='qa')),
    
    # Exam Notifications
    path('notification/', include('ExamNotification.urls')),
    
    # User App
    path('user/', include('User.urls')),
    
    # CKEditor
    path('ckeditor/', include('ckeditor_uploader.urls')),

    path('accounts/', include('allauth.urls')), 
    path('payments/', include('payments.urls', namespace='payments')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns