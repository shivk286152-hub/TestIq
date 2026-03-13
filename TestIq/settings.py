import os
import dj_database_url
from pathlib import Path


# ----------------------------
# BASE DIR
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------
# SECRET KEY
# ----------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-k%!lom5oc2y%mwch^x)=nny+9muld+a09mg&e@7sxeh_%ufs1g"
)

# ----------------------------
# DEBUG
# ----------------------------
DEBUG = os.environ.get("DEBUG", "False") == "True"

# ----------------------------
# ALLOWED HOSTS
# ----------------------------
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "127.0.0.1,localhost,testiq-3.onrender.com"
).split(",")

# ----------------------------
# INSTALLED APPS
# ----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'ckeditor',
    'ckeditor_uploader',
    'taggit',
    'exams',
    'ExamNotification',
    'User',
    # 'django_q',
    'CurrentAffairs',
   
   
  
   
]

# Django-Q configuration
# settings.py - Alternative using Django ORM (no Redis needed)
Q_CLUSTER = {
    'name': 'TestIQ',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'orm': 'default'  # Use database as broker
}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}
# CKEditor Configuration
# CKEditor configuration
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', '|',
            'link', 'bulletedList', 'numberedList', '|',
            'insertTable', 'imageUpload', '|',
            'undo', 'redo'
        ],
        'height': 300,
        'width': '100%',
    }
}
# CKEDITOR SETTINGS (IMPORTANT)
CKEDITOR_UPLOAD_PATH = "uploads/"
# To suppress the CKEditor warning (optional)
import warnings
warnings.filterwarnings('ignore', message='django-ckeditor bundles CKEditor 4.22.1')

# ----------------------------
# MIDDLEWARE
# ----------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ----------------------------
# URLS
# ----------------------------
ROOT_URLCONF = 'TestIq.urls'

# ----------------------------
# TEMPLATES
# ----------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'exams.context_processors.site_settings',
                'exams.context_processors.latest_mocktests',
                 # Add this line
                
            ],
        },
    },
]

# ----------------------------
# WSGI
# ----------------------------
WSGI_APPLICATION = 'TestIq.wsgi.application'

# ----------------------------
# DATABASE (Fixed)
# ----------------------------
if os.environ.get("RENDER") == "TRUE":
    # Optional: use SQLite on Render temporarily
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default="sqlite:///db.sqlite3",
            conn_max_age=600
        )
    }
# ----------------------------
# STATIC FILES
# ----------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ----------------------------
# MEDIA FILES
# ----------------------------
MEDIA_URL = "/media/"
# MEDIA_ROOT = BASE_DIR / "media"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ----------------------------
# LOGIN
# ----------------------------
LOGIN_REDIRECT_URL = "home"
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'home'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755


# ----------------------------
# DEFAULT AUTO FIELD
# ----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ----------------------------
# SESSION COOKIE SECURE
# ----------------------------
CSRF_TRUSTED_ORIGINS = [
    "https://testiq-3.onrender.com"
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True