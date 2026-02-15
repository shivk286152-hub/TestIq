import os
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
    'exams',
    'ExamNotification',
    'User',
]

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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ----------------------------
# WSGI
# ----------------------------
WSGI_APPLICATION = 'TestIq.wsgi.application'

# ----------------------------
# DATABASE
# ----------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
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
MEDIA_ROOT = BASE_DIR / "media"

# ----------------------------
# LOGIN
# ----------------------------
LOGIN_REDIRECT_URL = "home"
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = 'home'

# ----------------------------
# DEFAULT AUTO FIELD
# ----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# SESSION COOKIE SECURE 

CSRF_TRUSTED_ORIGINS = [
    "https://testiq-3.onrender.com"
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
