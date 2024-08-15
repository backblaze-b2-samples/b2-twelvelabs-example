import os

# Never put credentials in your code!
from dotenv import load_dotenv
from twelvelabs import TwelveLabs

load_dotenv()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9tf$jps6u-rxnv8nuur=*z&44$d!*_k@9td4jfaurtd5)xu_50'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [os.environ['WEB_APPLICATION_HOST']]

CSRF_TRUSTED_ORIGINS = list(map(lambda host: f'https://{host}', ALLOWED_HOSTS))

# Required for ngrok and other proxies that terminate TLS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'storages',

    'cattube.core',

    'huey.contrib.djhuey',
    'huey_django_orm',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cattube.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'cattube/templates')],
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

WSGI_APPLICATION = 'cattube.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'cattube/static'),
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# TBD Fastly
# AWS_S3_CUSTOM_DOMAIN = '...'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Lifetime for presigned URLs
AWS_QUERYSTRING_EXPIRE = 86400

STATIC_S3_REGION_NAME = os.environ['STATIC_S3_REGION_NAME']
STATIC_STORAGE_BUCKET_NAME = os.environ['STATIC_STORAGE_BUCKET_NAME']

STATIC_URL = f'https://{STATIC_STORAGE_BUCKET_NAME}.s3.{STATIC_S3_REGION_NAME}.backblazeb2.com/'

STORAGES = {
    "default": {
        "BACKEND": "cattube.storage.CachedS3Storage",
        "OPTIONS": {
            "access_key": os.environ['DEFAULT_ACCESS_KEY_ID'],
            "secret_key": os.environ['DEFAULT_SECRET_ACCESS_KEY'],
            "endpoint_url": os.environ['DEFAULT_S3_ENDPOINT_URL'],
            "region_name": os.environ['DEFAULT_S3_REGION_NAME'],
            "bucket_name": os.environ['DEFAULT_STORAGE_BUCKET_NAME'],
            "location": os.environ['DEFAULT_STORAGE_LOCATION'],
        },
    },
    "staticfiles": {
        "BACKEND": "cattube.storage.CachedS3Storage",
        "OPTIONS": {
            "access_key": os.environ['STATIC_ACCESS_KEY_ID'],
            "secret_key": os.environ['STATIC_SECRET_ACCESS_KEY'],
            "endpoint_url": os.environ['STATIC_S3_ENDPOINT_URL'],
            "region_name": os.environ['STATIC_S3_REGION_NAME'],
            "bucket_name": os.environ['STATIC_STORAGE_BUCKET_NAME'],
            "location": os.environ['STATIC_STORAGE_LOCATION'],
        },
    },
}

TRANSLOADIT_KEY = os.environ['TRANSLOADIT_KEY']
TRANSLOADIT_SECRET = os.environ['TRANSLOADIT_SECRET']
TRANSLOADIT_TEMPLATE_ID = os.environ['TRANSLOADIT_TEMPLATE_ID']
POLL_TRANSLOADIT = True

HUEY = {
    'huey_class': 'huey_django_orm.storage.DjangoORMHuey',
    'immediate': False,
}

VIDEOS_PATH = 'video'
THUMBNAILS_PATH = 'thumbnail'
TRANSCRIPTS_PATH = 'transcription'
TEXT_PATH = 'text_in_video'
LOGOS_PATH = 'logo'

TWELVE_LABS_INDEX_ID = os.environ['TWELVE_LABS_INDEX_ID']
TWELVE_LABS_POLL_INTERVAL = 1

TWELVE_LABS_CLIENT = TwelveLabs(api_key=os.environ['TWELVE_LABS_API_KEY'])
