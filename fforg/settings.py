"""

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import datetime
import os
from datetime import timedelta

import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DEBUG', 'True').lower() == 'true')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'INSECURE')
if SECRET_KEY == 'INSECURE':
    if DEBUG:
        import warnings

        warnings.warn('INSECURE SECRET_KEY!', RuntimeWarning)
    else:
        raise ValueError("SECRET_KEY env var must be defined when not in DEBUG=True")

STREAM_URL = os.environ.get('STREAM_URL', None)
# Application definition

STREAM_DASH_BASE = os.environ.get("STREAM_DASH_BASE", "https://stream.fragforce.org")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'memoize',
    "social_django",
    'ffsite',
    'ffdonations',
    'ffstream',
    "eventer",
    "evtsignup",
    "ffoverlay.apps.FfoverlayConfig",
    "ffbot",
    "ffdiscord",
]

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

ROOT_URLCONF = 'fforg.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'ffsite.ctx.common_org',
                'ffdonations.ctx.donations',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'fforg.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
    },
}
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

if bool(os.environ.get('DOCKER', 'False').lower() == 'true'):
    # CI
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "fragforce_test",
            "USER": "postgres",
            "PASSWORD": "postgres",
            "HOST": "db",
            "PORT": 5432,
        },
    }
    DATABASES['default'].update(dj_database_url.config(conn_max_age=500))
elif bool(os.environ.get('DOCKER_PROD', 'False').lower() == 'true'):
    # Production
    DATABASES['default'].update(dj_database_url.config(conn_max_age=500, ssl_require=False))
else:
    # Dev
    DATABASES['default'].update(dj_database_url.config(conn_max_age=500, ssl_require=False))

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
]

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

if bool(os.environ.get('DOCKER', 'False').lower() == 'true') or bool(
        os.environ.get('DOCKER_PROD', 'False').lower() == 'true'):
    SECURE_SSL_REDIRECT = False
else:
    SECURE_SSL_REDIRECT = True

CSRF_TRUSTED_ORIGINS = [
    'https://fragforce.org',
    'https://dev.fragforce.org',
]
if os.environ.get('CSRF_TRUSTED_ORIGINS'):
    CSRF_TRUSTED_ORIGINS += [
        origin.strip()
        for origin in os.environ['CSRF_TRUSTED_ORIGINS'].split(',')
        if origin.strip()
    ]

SINGAPORE_DONATIONS = float(os.environ.get('SINGAPORE_DONATIONS', '0.0'))
OTHER_DONATIONS = float(os.environ.get('OTHER_DONATIONS', '0.0'))
TARGET_DONATIONS = float(os.environ.get('TARGET_DONATIONS', '1.0'))

FRAG_BOT_API = os.environ.get('FRAG_BOT_API', 'https://bot.fragforce.org/dbquery')
FRAG_BOT_KEY = os.environ.get('FRAG_BOT_KEY', '')
FRAG_BOT_BOT = os.environ.get('FRAG_BOT_BOT', 'misterfragbot')

# Max rows for api to return
MAX_API_ROWS = int(os.environ.get('MAX_API_ROWS', 1024))

REDIS_LOCALHOST = 'redis://localhost'

if os.environ.get('REDIS_URL', None):
    REDIS_URL_DEFAULT = REDIS_LOCALHOST
    # Base URL - Needs DB ID added
    REDIS_URL_BASE = os.environ.get('REDIS_URL', REDIS_URL_DEFAULT)
    # Don't use DB 0 for anything
    REDIS_URL_DEFAULT = REDIS_URL_BASE + "/0"
    # Celery tasks
    REDIS_URL_TASKS = REDIS_URL_BASE + "/1"
    # Celery tombstones (aka results)
    REDIS_URL_TOMBS = REDIS_URL_BASE + "/2"
    # Misc timers
    REDIS_URL_TIMERS = REDIS_URL_BASE + "/3"
    # Django cache
    REDIS_URL_DJ_CACHE = REDIS_URL_BASE + "/4"


else:
    REDIS_URL_DEFAULT = REDIS_LOCALHOST
    # Base URL - Needs DB ID added
    REDIS_URL_BASE = REDIS_URL_DEFAULT
    # Don't use DB 0 for anything
    REDIS_URL_DEFAULT = os.environ.get('REDIS0_URL', REDIS_LOCALHOST) + "/0"
    # Celery tasks
    REDIS_URL_TASKS = os.environ.get('REDIS1_URL', REDIS_LOCALHOST) + "/0"
    # Celery tombstones (aka results)
    REDIS_URL_TOMBS = os.environ.get('REDIS2_URL', REDIS_LOCALHOST) + "/0"
    # Misc timers
    REDIS_URL_TIMERS = os.environ.get('REDIS3_URL', REDIS_LOCALHOST) + "/0"
    # Django cache
    REDIS_URL_DJ_CACHE = os.environ.get('REDIS4_URL', REDIS_LOCALHOST) + "/0"

CELERY_IMPORTS = [
    'eventer.tasks',
    'evtsignup.tasks',
    'ffdonations.tasks.donations',
    'ffdonations.tasks.participants',
    'ffdonations.tasks.sender',
    'ffdonations.tasks.teams',
]
CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_URL = REDIS_URL_TASKS
CELERY_RESULT_BACKEND = REDIS_URL_TOMBS
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', None)
MAX_UPCOMING_EVENTS = int(os.environ.get('MAX_UPCOMING_EVENTS', 20))
MAX_PAST_EVENTS = int(os.environ.get('MAX_PAST_EVENTS', 20))
MAX_ALL_EVENTS = int(os.environ.get('MAX_ALL_EVENTS', 20))

# Various view cache timeouts
VIEW_TEAMS_CACHE = int(os.environ.get('VIEW_TEAMS_CACHE', 20))
VIEW_PARTICIPANTS_CACHE = int(os.environ.get('VIEW_PARTICIPANTS_CACHE', 20))
VIEW_DONATIONS_CACHE = int(os.environ.get('VIEW_DONATIONS_CACHE', 20))
VIEW_DONATIONS_STATS_CACHE = int(os.environ.get('VIEW_DONATIONS_STATS_CACHE', 20))
VIEW_SITE_EVENT_CACHE = int(os.environ.get('VIEW_SITE_EVENT_CACHE', 60))
VIEW_SITE_SITE_CACHE = int(os.environ.get('VIEW_SITE_SITE_CACHE', 60))
VIEW_SITE_STATIC_CACHE = int(os.environ.get('VIEW_SITE_STATIC_CACHE', 300))

# Extra Life Limits and Data
EXTRALIFE_TEAMID = int(os.environ.get('EXTRALIFE_TEAMID', 73149))
MIN_EL_TEAMID = int(os.environ.get('MIN_EL_TEAMID', 73127))
MIN_EL_PARTICIPANTID = int(os.environ.get('MIN_EL_PARTICIPANTID', 565075))

# Min time between team updates - Only cares about tracked teams!
EL_TEAM_UPDATE_FREQUENCY_MIN = timedelta(minutes=int(os.environ.get('EL_TEAM_UPDATE_FREQUENCY_MIN', 5)))
# Max time between updates for any given team - Only cares about tracked teams!
EL_TEAM_UPDATE_FREQUENCY_MAX = timedelta(minutes=int(os.environ.get('EL_TEAM_UPDATE_FREQUENCY_MAX', 15)))
# How often to check for updates
EL_TEAM_UPDATE_FREQUENCY_CHECK = timedelta(minutes=int(os.environ.get('EL_TEAM_UPDATE_FREQUENCY_CHECK', 5)))

# Min time between participants updates - Only cares about tracked participants!
EL_PTCP_UPDATE_FREQUENCY_MIN = timedelta(seconds=int(os.environ.get('EL_PTCP_UPDATE_FREQUENCY_MIN', 15)))
# Max time between updates for any given participants - Only cares about tracked participants!
EL_PTCP_UPDATE_FREQUENCY_MAX = timedelta(minutes=int(os.environ.get('EL_PTCP_UPDATE_FREQUENCY_MAX', 1)))
# How often to check for updates
EL_PTCP_UPDATE_FREQUENCY_CHECK = timedelta(seconds=int(os.environ.get('EL_PTCP_UPDATE_FREQUENCY_CHECK', 5)))

# Min time between donation list updates - Only cares about tracked teams/participants!
EL_DON_UPDATE_FREQUENCY_MIN = timedelta(seconds=int(os.environ.get('EL_DON_UPDATE_FREQUENCY_MIN', 30)))
# Max time between updates for any given donation list - Only cares about tracked teams/participants!
EL_DON_UPDATE_FREQUENCY_MAX = timedelta(minutes=int(os.environ.get('EL_DON_UPDATE_FREQUENCY_MAX', 5)))
# How often to check for updates
EL_DON_UPDATE_FREQUENCY_CHECK = timedelta(seconds=int(os.environ.get('EL_DON_UPDATE_FREQUENCY_CHECK', 5)))

# Min time between donation list updates for a team - Only cares about tracked teams
EL_DON_TEAM_UPDATE_FREQUENCY_MIN = timedelta(seconds=int(os.environ.get('EL_DON_TEAM_UPDATE_FREQUENCY_MIN', 30)))
# Max time between updates of donations for any given team - Only cares about tracked teams
EL_DON_TEAM_UPDATE_FREQUENCY_MAX = timedelta(minutes=int(os.environ.get('EL_DON_TEAM_UPDATE_FREQUENCY_MAX', 5)))

# Min time between donation list updates for a participants - Only cares about tracked participants
EL_DON_PTCP_UPDATE_FREQUENCY_MIN = timedelta(minutes=int(os.environ.get('EL_DON_PTCP_UPDATE_FREQUENCY_MIN', 5)))
# Max time between updates of donations for any given participants - Only cares about tracked participants
EL_DON_PTCP_UPDATE_FREQUENCY_MAX = timedelta(minutes=int(os.environ.get('EL_DON_PTCP_UPDATE_FREQUENCY_MAX', 15)))

# Min time between EL REST requests
EL_REQUEST_MIN_TIME = timedelta(seconds=int(os.environ.get('EL_REQUEST_MIN_TIME_SECONDS', 15)))
# Seconds to wait after a 429 if no Retry-After header is present
EL_RETRY_AFTER_SECONDS = int(os.environ.get('EL_RETRY_AFTER_SECONDS', 60))
# Number of times to retry a request after a 429
EL_MAX_RETRIES = int(os.environ.get('EL_MAX_RETRIES', 3))
# Seconds to wait between retries on 5xx or network errors
EL_SERVER_RETRY_AFTER_SECONDS = int(os.environ.get('EL_SERVER_RETRY_AFTER_SECONDS', 600))
# Number of times to retry a request on 5xx or network errors (7 total attempts)
EL_SERVER_MAX_RETRIES = int(os.environ.get('EL_SERVER_MAX_RETRIES', 6))
# Min time between EL REST requests for any given URL
EL_REQUEST_MIN_TIME_URL = timedelta(seconds=int(os.environ.get('EL_REQUEST_MIN_TIME_URL_SECONDS', 15)))
# Min time between request for any given remote host
REQUEST_MIN_TIME_HOST = timedelta(seconds=int(os.environ.get('REQUEST_MIN_TIME_HOST_SECONDS', 15)))

# How often to check for missed donations to send to twitch bot
SEND_MISSED_DONATIONS = datetime.timedelta(minutes=int(os.environ.get('SEND_MISSED_DONATIONS', 10)))

# Current Extra-Life event id - Unused atm
EL_EVENT_ID = int(os.environ.get('EL_EVENT_ID', -1))

# Cache Configuration
if REDIS_URL_BASE and REDIS_URL_BASE == REDIS_URL_DEFAULT:
    # Dev and release config
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
    }
else:
    def make_key_hash(key, key_prefix, version):
        """ Create a hashed key"""
        import hashlib
        m = hashlib.sha512()
        m.update(':'.join([key_prefix, str(version), key]))
        return m.hexdigest()


    def make_key_nohash(key, key_prefix, version):
        return ':'.join([key_prefix, str(version), key])


    if os.environ.get('DJANGO_CACHE_HASH', 'false').lower() == 'true':
        make_key = make_key_hash
    else:
        make_key = make_key_nohash

    # Real config
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL_DJ_CACHE,
            'TIMEOUT': int(os.environ.get('REDIS_DJ_TIMEOUT', 300)),
            'KEY_FUNCTION': make_key,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                # hiredis is used automatically when the hiredis package is installed (redis-py 4+)
                'SOCKET_TIMEOUT': int(os.environ.get('REDIS_DJ_SOCKET_TIMEOUT', 5)),
                'SOCKET_CONNECT_TIMEOUT': int(os.environ.get('REDIS_DJ_SOCKET_CONNECT_TIMEOUT', 3)),
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': int(os.environ.get('REDIS_DJ_POOL_MAX_CONN', 5)),
                    'timeout': int(os.environ.get('REDIS_DJ_POOL_TIMEOUT', 3)),
                },
            },
        },
    }

    if os.environ.get('DJANGO_COMPRESS_REDIS', 'false').lower() == 'true':
        CACHES['default']['OPTIONS']['COMPRESSOR'] = 'django_redis.compressors.zlib.ZlibCompressor'

# Second to last
CELERY_BEAT_SCHEDULE = {
    'update-all-teams': {
        'task': 'ffdonations.tasks.teams.update_teams_if_needed',
        'schedule': EL_TEAM_UPDATE_FREQUENCY_CHECK,
    },
    'update-all-participants': {
        'task': 'ffdonations.tasks.participants.update_participants_if_needed',
        'schedule': EL_PTCP_UPDATE_FREQUENCY_CHECK,
    },
    'update-all-donations': {
        'task': 'ffdonations.tasks.donations.update_donations_if_needed',
        'schedule': EL_DON_UPDATE_FREQUENCY_CHECK,
    },
'send-missed-tracks': {
        'task': 'ffdonations.tasks.sender.note_new_donations',
        'schedule': SEND_MISSED_DONATIONS,
    },
    'sync-discord-guild-roles': {
        'task': 'ffdiscord.tasks.sync_discord_roles',
        'schedule': timedelta(hours=int(os.environ.get('DISCORD_ROLE_SYNC_HOURS', 1))),
    },
    'sync-discord-member-roles': {
        'task': 'ffdiscord.tasks.sync_all_guild_members',
        'schedule': timedelta(minutes=int(os.environ.get('DISCORD_MEMBER_SYNC_MINUTES', 15))),
    },
    'sync-all-igdb-games': {
        'task': 'eventer.tasks.sync_all_igdb_games',
        'schedule': timedelta(days=int(os.environ.get('IGDB_SYNC_INTERVAL_DAYS', 7))),
    },
    'fetch-top-igdb-games-hypes': {
        'task': 'eventer.tasks.fetch_top_games_by_hypes',
        'schedule': timedelta(days=int(os.environ.get('IGDB_TOP_GAMES_INTERVAL_DAYS', 7))),
    },
    'fetch-top-igdb-games-rating': {
        'task': 'eventer.tasks.fetch_top_games_by_rating',
        'schedule': timedelta(days=int(os.environ.get('IGDB_TOP_GAMES_INTERVAL_DAYS', 7))),
    },
    'close-signups-for-started-events': {
        'task': 'eventer.tasks.close_signups_for_started_events',
        'schedule': timedelta(minutes=int(os.environ.get('CLOSE_SIGNUPS_CHECK_MINUTES', 15))),
    },
    'retry-pending-url-resolutions': {
        'task': 'evtsignup.tasks.retry_pending_url_resolutions',
        'schedule': timedelta(hours=int(os.environ.get('RETRY_URL_RESOLUTION_HOURS', 1))),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')
        },
        'root': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        '': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'social_core.backends.discord.DiscordOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_DISCORD_KEY = os.environ.get('DISCORD_CLIENT_ID', '')
SOCIAL_AUTH_DISCORD_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '')
SOCIAL_AUTH_DISCORD_SCOPE = ['identify', 'email', 'guilds']
SOCIAL_AUTH_DISCORD_AUTH_EXTRA_ARGUMENTS = {'prompt': 'consent'}
DISCORD_REQUIRED_GUILD_ID = os.environ.get('DISCORD_GUILD_ID', '164136635762606081')
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '')
ADD_DISCORD_COMMANDS = os.environ.get('ADD_DISCORD_COMMANDS', 'true').lower() not in ('false', '0', 'no')

IGDB_CLIENT_ID = os.environ.get('IGDB_CLIENT_ID', '')
IGDB_CLIENT_SECRET = os.environ.get('IGDB_CLIENT_SECRET', '')
IGDB_RATE_LIMIT_RETRIES = int(os.environ.get('IGDB_RATE_LIMIT_RETRIES', 3))
IGDB_RATE_LIMIT_RETRY_AFTER = float(os.environ.get('IGDB_RATE_LIMIT_RETRY_AFTER', 1.0))
IGDB_BULK_SYNC_DELAY = float(os.environ.get('IGDB_BULK_SYNC_DELAY', 0.5))

URL_RESOLUTION_MAX_ATTEMPTS = int(os.environ.get('URL_RESOLUTION_MAX_ATTEMPTS', 3))

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'evtsignup.pipeline.require_discord_guild',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

LOGIN_URL = '/auth/login/discord/'
LOGIN_REDIRECT_URL = '/stream/my-keys'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login-error'

TEST_RUNNER = 'fforg.test_runner.GitHashTestRunner'

