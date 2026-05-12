import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# === Environment ===
env = environ.Env()
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)

# --- Security (required) ---
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

AUTH_USER_MODEL = 'api.UserMaster'
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
CSRF_COOKIE_AGE = 60 * 60 * 24 * 30  # CSRF 토큰: 30일 유지
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 세션: 7일 유지 (자동 로그인 1주일)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # 브라우저 닫아도 세션 유지
SESSION_SAVE_EVERY_REQUEST = True  # 매 요청마다 세션 만료 시간 갱신
SESSION_COOKIE_SECURE = False  # HTTP 환경에서도 세션 쿠키 허용
CSRF_COOKIE_SECURE = False  # HTTP 환경에서도 CSRF 쿠키 허용
SECURE_BROWSER_XSS_FILTER = True  # XSS 보호 활성화
SECURE_CONTENT_TYPE_NOSNIFF = True  # MIME 타입 보안
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"  # 보안 정책 설정
SECURE_CROSS_ORIGIN_OPENER_POLICY = None  # 로컬테스트에서 메세지 감추기

# --- Email (SMTP) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'api',
    'web',
    'rest_framework',
    'rest_framework.authtoken',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'corsheaders',
    'django_extensions',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "http://localhost",
    "https://cdnjs.cloudflare.com",
])

X_FRAME_OPTIONS = 'SAMEORIGIN'
ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

# --- Database (MySQL) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET NAMES 'utf8mb4'",
        }
    }
}

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = False  # UTC 강제 적용을 해제하여 KST 그대로 저장되도록 설정

# --- Static / Media ---
MEDIA_URL = '/data/'
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'web', 'static'),
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'data/')
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
