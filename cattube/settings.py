import os
from urllib.parse import urlparse

# Never put credentials in your code!
from botocore.config import Config
from django.core.exceptions import ImproperlyConfigured
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

_MISSING = object()


def env(name, *legacy_names, default=_MISSING):
    for env_name in (name, *legacy_names):
        value = os.environ.get(env_name)
        if value:
            return value

    if default is not _MISSING:
        return default

    accepted_names = ', '.join((name, *legacy_names))
    raise ImproperlyConfigured(
        f'Missing required environment variable: {accepted_names}'
    )


def b2_endpoint_url(region):
    return f'https://s3.{region}.backblazeb2.com'


def validate_b2_public_url_base(public_url_base, bucket_name, region_name):
    parsed_url = urlparse(public_url_base)
    expected_host = f'{bucket_name}.s3.{region_name}.backblazeb2.com'

    if parsed_url.scheme != 'https':
        raise ImproperlyConfigured('B2_PUBLIC_URL_BASE must start with https://')
    if not parsed_url.netloc:
        raise ImproperlyConfigured('B2_PUBLIC_URL_BASE must include a host')
    if parsed_url.username or parsed_url.password:
        raise ImproperlyConfigured('B2_PUBLIC_URL_BASE must not include user info')
    if parsed_url.port:
        raise ImproperlyConfigured('B2_PUBLIC_URL_BASE must not include a port')
    if parsed_url.query or parsed_url.fragment:
        raise ImproperlyConfigured(
            'B2_PUBLIC_URL_BASE must not include a query string or fragment'
        )
    if parsed_url.path not in ('', '/'):
        raise ImproperlyConfigured('B2_PUBLIC_URL_BASE must not include a path')
    if parsed_url.hostname != expected_host:
        raise ImproperlyConfigured(
            'B2_PUBLIC_URL_BASE host must be '
            f'{expected_host}; got {parsed_url.hostname or "<empty>"}'
        )

    return public_url_base.rstrip('/')


B2_APPLICATION_KEY_ID = env('B2_APPLICATION_KEY_ID', 'DEFAULT_ACCESS_KEY_ID')
B2_APPLICATION_KEY = env('B2_APPLICATION_KEY', 'DEFAULT_SECRET_ACCESS_KEY')
B2_BUCKET_NAME = env('B2_BUCKET_NAME', 'DEFAULT_STORAGE_BUCKET_NAME')
B2_REGION = env('B2_REGION', 'DEFAULT_S3_REGION_NAME')
B2_MEDIA_LOCATION = env('B2_MEDIA_LOCATION', 'DEFAULT_STORAGE_LOCATION', default='')
B2_STATIC_APPLICATION_KEY_ID = env(
    'B2_STATIC_APPLICATION_KEY_ID',
    'STATIC_ACCESS_KEY_ID',
    default=B2_APPLICATION_KEY_ID,
)
B2_STATIC_APPLICATION_KEY = env(
    'B2_STATIC_APPLICATION_KEY',
    'STATIC_SECRET_ACCESS_KEY',
    default=B2_APPLICATION_KEY,
)
B2_STATIC_BUCKET_NAME = env(
    'B2_STATIC_BUCKET_NAME',
    'STATIC_STORAGE_BUCKET_NAME',
    default=B2_BUCKET_NAME,
)
B2_STATIC_REGION = env('B2_STATIC_REGION', 'STATIC_S3_REGION_NAME', default=B2_REGION)
B2_STATIC_LOCATION = env(
    'B2_STATIC_LOCATION',
    'STATIC_STORAGE_LOCATION',
    default='static',
)
B2_PUBLIC_URL_BASE = validate_b2_public_url_base(
    env(
        'B2_PUBLIC_URL_BASE',
        default=f'https://{B2_STATIC_BUCKET_NAME}.s3.{B2_STATIC_REGION}.backblazeb2.com',
    ),
    B2_STATIC_BUCKET_NAME,
    B2_STATIC_REGION,
)
B2_ENDPOINT_URL = b2_endpoint_url(B2_REGION)
B2_STATIC_ENDPOINT_URL = b2_endpoint_url(B2_STATIC_REGION)
B2_USER_AGENT = 'b2-twelvelabs-example (backblaze-b2-samples)'
B2_CLIENT_CONFIG = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'virtual'},
    user_agent_extra=B2_USER_AGENT,
)

B2_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Lifetime for presigned URLs
B2_QUERYSTRING_EXPIRE = 86400

B2_BASE_STORAGE_OPTIONS = {
    "client_config": B2_CLIENT_CONFIG,
    "object_parameters": B2_OBJECT_PARAMETERS,
    "querystring_expire": B2_QUERYSTRING_EXPIRE,
}

B2_DEFAULT_STORAGE_OPTIONS = {
    **B2_BASE_STORAGE_OPTIONS,
    "access_key": B2_APPLICATION_KEY_ID,
    "secret_key": B2_APPLICATION_KEY,
    "endpoint_url": B2_ENDPOINT_URL,
    "region_name": B2_REGION,
    "bucket_name": B2_BUCKET_NAME,
}
if B2_MEDIA_LOCATION:
    B2_DEFAULT_STORAGE_OPTIONS["location"] = B2_MEDIA_LOCATION

B2_STATIC_STORAGE_OPTIONS = {
    **B2_BASE_STORAGE_OPTIONS,
    "access_key": B2_STATIC_APPLICATION_KEY_ID,
    "secret_key": B2_STATIC_APPLICATION_KEY,
    "endpoint_url": B2_STATIC_ENDPOINT_URL,
    "region_name": B2_STATIC_REGION,
    "bucket_name": B2_STATIC_BUCKET_NAME,
}
if B2_STATIC_LOCATION:
    B2_STATIC_STORAGE_OPTIONS["location"] = B2_STATIC_LOCATION

STATIC_URL = f'{B2_PUBLIC_URL_BASE}/'

STORAGES = {
    "default": {
        "BACKEND": "cattube.storage.CachedS3Storage",
        "OPTIONS": B2_DEFAULT_STORAGE_OPTIONS,
    },
    "staticfiles": {
        "BACKEND": "cattube.storage.CachedS3Storage",
        "OPTIONS": B2_STATIC_STORAGE_OPTIONS,
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

TWELVE_LABS_INDEX_ID = os.environ['TWELVE_LABS_INDEX_ID']
TWELVE_LABS_POLL_INTERVAL = 1

TWELVE_LABS_CLIENT = TwelveLabs(api_key=os.environ['TWELVE_LABS_API_KEY'])

# How many videos to show in list pages
PAGE_SIZE = 15
