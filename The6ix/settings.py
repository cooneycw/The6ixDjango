"""
Django settings for The6ix project.

Generated by 'django-admin startproject' using Django 4.0.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

from pathlib import Path
from .secrets import get_secrets
import ast
import socket
import os
import redis
from joblib import load

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

STAT_DATE = 'June 10, 2022'

IPADD = socket.gethostbyname(socket.gethostname())
ec2 = True
if IPADD in ('192.168.4.244', '127.0.0.1'):
    ec2 = False
print(f'EC2 environment: {ec2} ip address:{IPADD}')

secret = get_secrets()
secret_dict = ast.literal_eval(secret)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secret_dict['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
if ec2 == True:
    DEBUG = False
    BASE_URL = 'https://the6ixclan.ca'
else:
    DEBUG = True
    BASE_URL = 'http://127.0.0.1:8000'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.the6ixclan.ca']

CSRF_TRUSTED_ORIGINS = ["https://the6ixclan.ca"]

# Application definition

INSTALLED_APPS = [
    'The6ixDjango.apps.The6IxdjangoConfig',
    'users.apps.UsersConfig',
    'clashstats.apps.ClashstatsConfig',
    'crispy_forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
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

ROOT_URLCONF = 'The6ix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'The6ix.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

POSTGRES_PORT = secret_dict['POSTGRES_PORT']
POSTGRES_HOST = secret_dict['POSTGRES_HOST']

CLASH_API = secret_dict['API']
REDIS_PORT = secret_dict['REDIS_PORT']
REDIS_HOST = secret_dict['REDIS_HOST']
CELERY_BROKER_URL = secret_dict['CELERY_BROKER_URL']
CELERY_RESULT_BACKEND = secret_dict['CELERY_RESULT_BACKEND']
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT = ['pickle']

if DEBUG==True:
    POSTGRES_PORT = secret_dict['POSTGRES_PORT_DEV']
    POSTGRES_HOST = secret_dict['POSTGRES_HOST_DEV']
    CLASH_API = secret_dict['API_DEV']
    REDIS_HOST = secret_dict['REDIS_HOST_DEV']
    CELERY_BROKER_URL = secret_dict['CELERY_BROKER_URL_DEV']

CELERY_RESULT_BACKEND = 'django-db'

REDIS_LOCK_KEY = secret_dict['REDIS_LOCK_KEY']
REDIS_INSTANCE = redis.StrictRedis(host=REDIS_HOST,
                                  port=REDIS_PORT, db=0)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': secret_dict['POSTGRES_DB'],
        'USER': secret_dict['POSTGRES_USER'],
        'PASSWORD': secret_dict['POSTGRES_PASSWORD'],
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'US/Eastern'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "mediafiles")

STAT_FILES = BASE_DIR / "stat_files"

CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_REDIRECT_URL = 'The6ixDjango-home'
LOGIN_URL = 'login'

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

kmeans_name = STAT_FILES / 'pickles/kmeans.pickle'
hclust_name = STAT_FILES / 'pickles/hclust.pickle'
new_segment_map_name = STAT_FILES / 'pickles/new_segment_map.pickle'
segment_cols_name = STAT_FILES / 'pickles/segment_cols'
max_seg_name = STAT_FILES / 'pickles/max_seg'
max_a_seg_name = STAT_FILES / 'pickles/max_a_seg'
analysis_var_list_name = STAT_FILES / 'pickles/analysis_var_list'
analysis_sel_cols_name = STAT_FILES / 'pickles/analysis_sel_cols'
stats_sel_cols_name = STAT_FILES / 'pickles/stats_sel_cols'
sample_decks_name = STAT_FILES / 'pickles/sample_df'
lbounds_name = STAT_FILES / 'pickles/lbounds'
ubounds_name = STAT_FILES / 'pickles/ubounds'
elixr_lbounds_name = STAT_FILES / 'pickles/home_lbounds'
elixr_ubounds_name = STAT_FILES / 'pickles/home_ubounds'
lr_anova_name = STAT_FILES / 'pickles/lr_outcome_model'
lr_model_name = STAT_FILES / 'pickles/lr_outcome_model'
lg_model_name = STAT_FILES / 'pickles/lg_outcome_model'
gn_model_name = STAT_FILES / 'pickles/gn_outcome_model'
xgb_model_name = STAT_FILES / 'pickles/xg_outcome_model'
min_max_scaler_name = STAT_FILES / 'pickles/min_max_scaler'
tf_model_name = STAT_FILES / 'pickles/nn_outcome_model'
stacked_model_name = STAT_FILES / 'pickles/stacked_outcome_model'

CLUSTERING = load(kmeans_name)
HCLUSTERING = load(hclust_name)
NEW_SEGMENT_MAP = load(new_segment_map_name)
SEGMENT_COLS = load(segment_cols_name)
MAX_SEG = load(max_seg_name)
MAX_A_SEG = load(max_a_seg_name)
ANALYSIS_VAR_LIST = load(analysis_var_list_name)
ANALYSIS_SEL_COLS = load(analysis_sel_cols_name)
SAMPLE_DECKS = load(sample_decks_name)
STATS_SEL_COLS = load(stats_sel_cols_name)
LBOUNDS = load(lbounds_name)
UBOUNDS = load(ubounds_name)
ELIXR_LBOUNDS = load(elixr_lbounds_name)
ELIXR_UBOUNDS = load(elixr_ubounds_name)
LR_ANOVA = load(lr_anova_name)
LR_MODEL = load(lr_model_name)
XGB_MODEL = load(xgb_model_name)
STACKED_MODEL = load(stacked_model_name)