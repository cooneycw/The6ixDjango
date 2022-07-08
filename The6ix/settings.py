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
import boto3
import pickle
import redis
from joblib import load


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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
S3_BUCKET = secret_dict['S3_BUCKET']

if DEBUG==True:
    POSTGRES_PORT = secret_dict['POSTGRES_PORT_DEV']
    POSTGRES_HOST = secret_dict['POSTGRES_HOST_DEV']
    CLASH_API = secret_dict['API_DEV']
    REDIS_HOST = secret_dict['REDIS_HOST_DEV']
    CELERY_BROKER_URL = secret_dict['CELERY_BROKER_URL_DEV']
    S3_BUCKET = secret_dict['S3_BUCKET_DEV']

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

AWS_ACCESS = os.environ.get('aws_access_key_id')
AWS_SECRET = os.environ.get('aws_secret_access_key')
session_s3 = boto3.session.Session(
                aws_access_key_id=AWS_ACCESS,
                aws_secret_access_key=AWS_SECRET)
s3_resource = session_s3.resource('s3')

key_01 = 'segment_summary'
key_02 = 'setting_vars'
key_03 = 'setting_vars_names'
key_04 = 'card_obj_get_cards'
key_05 = 'card_list_compare_01'
key_06 = 'card_list_compare_02'
key_07 = 'stat_date'
key_list = [key_01, key_02, key_03, key_04, key_05, key_06, key_07]
ret_dict = {}
for item in key_list:
    print(f'Getting: {item}')
    s3_resource_object = s3_resource.Object(S3_BUCKET, item).get()
    ret_dict[f'{item}'] = pickle.loads(s3_resource_object['Body'].read())

segment_data = ret_dict[key_01]
SEGMENT_SUMMARY = segment_data[0]
SEGMENT_SUMMARY_QUART = segment_data[1]

CARD_OBJ_GET_CARDS = ret_dict[key_04]
CARD_LIST_COMPARE_01 = ret_dict[key_05]
CARD_LIST_COMPARE_02 = ret_dict[key_06]
STAT_DATE = ret_dict[key_07]

ANALYSIS_SEL_COLS = ret_dict[key_02][0]
ANALYSIS_VAR_LIST = ret_dict[key_02][1]
MAX_SEG = ret_dict[key_02][2]
HCLUSTERING = ret_dict[key_02][3]
ELIXR_LBOUNDS = ret_dict[key_02][4]
ELIXR_UBOUNDS = ret_dict[key_02][5]
CLUSTERING = ret_dict[key_02][6]
LBOUNDS = ret_dict[key_02][7]
LR_ANOVA = ret_dict[key_02][8]
LR_MODEL = ret_dict[key_02][9]
MAX_A_SEG = ret_dict[key_02][10]
NEW_SEGMENT_MAP = ret_dict[key_02][11]
SAMPLE_DECKS = ret_dict[key_02][12]
SEGMENT_COLS = ret_dict[key_02][13]
STACKED_MODEL = ret_dict[key_02][14]
STATS_SEL_COLS = ret_dict[key_02][15]
UBOUNDS = ret_dict[key_02][16]
XGB_MODEL = ret_dict[key_02][17]
