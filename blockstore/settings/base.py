import os
import environ
import platform
from logging.handlers import SysLogHandler
from os.path import join, abspath, dirname

env = environ.Env()


# PATH vars
def here(*x):
    return join(abspath(dirname(__file__)), *x)


PROJECT_ROOT = here("..")


def root(*x):
    return join(abspath(PROJECT_ROOT), *x)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('BLOCKSTORE_SECRET_KEY', 'insecure-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles'
)

THIRD_PARTY_APPS = (
    'rest_framework',
    'rest_framework.authtoken',  # For authenticating API clients
    'rest_framework_swagger',
    'django_filters',
    'social_django',  # To let admin users log in using their LMS user account
    'waffle',
    'corsheaders',
    'release_util',
)

PROJECT_APPS = (
    'blockstore.apps.mysql_unicode',
    'blockstore.apps.core',
    'blockstore.apps.bundles.apps.BundlesConfig',
    'blockstore.apps.rest_api',
)

INSTALLED_APPS += THIRD_PARTY_APPS
INSTALLED_APPS += PROJECT_APPS

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'waffle.middleware.WaffleMiddleware',
)

ROOT_URLCONF = 'blockstore.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'blockstore.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# Set this value in the environment-specific files (e.g. local.py, production.py, test.py)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',  # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',  # Set to empty string for default.
        'OPTIONS': {
            # Use a non-broken unicode encoding. See "mysql_unicode/migrations/0001_initial.py"
            # for details. Together with that migration, this setting will force the use of
            # the correct unicode implementation.
            # Note that this limits the length of InnoDB indexed columns to 191 characters.
            'charset': 'utf8mb4',
            'init_command': 'SET NAMES utf8mb4',
        },
    }
}


################################################################################
# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (
    root('conf', 'locale'),
)


################################################################################
# MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = root('media')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
# END MEDIA CONFIGURATION


################################################################################
# STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = root('assets')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = []

################################################################################
# TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/1.11/ref/settings/#templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': (
            root('templates'),
        ),
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'blockstore.apps.core.context_processors.core',
            ),
            'debug': True,  # Django will only display debug pages if the global DEBUG setting is set to True.
        }
    },
]
# END TEMPLATE CONFIGURATION


################################################################################
# COOKIE CONFIGURATION
# The purpose of customizing the cookie names is to avoid conflicts when
# multiple Django services are running behind the same hostname.
# Detailed information at: https://docs.djangoproject.com/en/dev/ref/settings/
SESSION_COOKIE_NAME = 'blockstore_sessionid'
CSRF_COOKIE_NAME = 'blockstore_csrftoken'
LANGUAGE_COOKIE_NAME = 'blockstore_language'
# END COOKIE CONFIGURATION

################################################################################
# AUTHENTICATION CONFIGURATION
LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'

AUTH_USER_MODEL = 'core.User'

AUTHENTICATION_BACKENDS = (
    'auth_backends.backends.EdXOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

ENABLE_AUTO_AUTH = False
AUTO_AUTH_USERNAME_PREFIX = 'auto_auth_'

SOCIAL_AUTH_STRATEGY = 'auth_backends.strategies.EdxDjangoStrategy'
# Django model max_length overrides required for MySQL utf8mb4 charset:
SOCIAL_AUTH_UID_LENGTH = 190
SOCIAL_AUTH_NONCE_SERVER_URL_LENGTH = 190
SOCIAL_AUTH_ASSOCIATION_SERVER_URL_LENGTH = 190
SOCIAL_AUTH_ASSOCIATION_HANDLE_LENGTH = 190
SOCIAL_AUTH_EMAIL_LENGTH = 190

# Set these to the correct values for your Open edX OAuth2 SSO provider (e.g., devstack)
SOCIAL_AUTH_EDX_OAUTH2_KEY = 'replace-me'
SOCIAL_AUTH_EDX_OAUTH2_SECRET = 'replace-me'
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = 'http://edx.devstack.lms:18000'
SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT = 'http://localhost:18000'

# CORS Config
CORS_ORIGIN_ALLOW_ALL = env('DJANGO_CORS_ORIGIN_ALLOW_ALL', default=False)
CORS_ORIGIN_WHITELIST = env.list('DJANGO_CORS_ORIGIN_WHITELIST', default=[])
CORS_ORIGIN_REGEX_WHITELIST = (r'^(https?://)?localhost:.+$', )


# TODO Set this to another (non-staff, ideally) path.
LOGIN_REDIRECT_URL = '/admin/'
# END AUTHENTICATION CONFIGURATION

################################################################################
# REST FRAMEWORK CONFIGURATION

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # We use token authentication to secure the API. We can't use OAuth2
        # because django-oauth-toolkit is currently incompatible with utf8mb4
        # (requires a small upstream fix to their DB migrations, to make the
        # index length configurable like python-social-auth does.)
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # Only superusers or authorized applications that authenticate with a
        # token are allowed to use the API.
        'blockstore.apps.rest_api.permissions.IsSuperUserOrAuthorizedApplication',
    ),
}

################################################################################
# OPENEDX-SPECIFIC CONFIGURATION

PLATFORM_NAME = 'Your Platform Name Here'

################################################################################
# LOGGING CONFIGURATION

hostname = platform.node().split(".")[0]

syslog_address = '/var/run/syslog' if platform.system().lower() == 'darwin' else '/dev/log'
syslog_format = '[service_variant=blockstore][%(name)s] %(levelname)s [{hostname}  %(process)d] ' \
                '[%(filename)s:%(lineno)d] - %(message)s'.format(hostname=hostname)

# Set up logging for development use (logging to stdout)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(process)d '
                      '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
        },
        'syslog_format': {'format': syslog_format},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        'local': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': syslog_address,
            'formatter': 'syslog_format',
            'facility': SysLogHandler.LOG_LOCAL0,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'local'],
            'propagate': False,
            'level': 'INFO'
        },
        'requests': {
            'handlers': ['console', 'local'],
            'propagate': True,
            'level': 'WARNING'
        },
        'factory': {
            'handlers': ['console', 'local'],
            'propagate': True,
            'level': 'WARNING'
        },
        'django.request': {
            'handlers': ['console', 'local'],
            'propagate': True,
            'level': 'WARNING'
        },
        '': {
            'handlers': ['console', 'local'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}
