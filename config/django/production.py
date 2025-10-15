from .base import *  # noqa

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_PRODUCTION_SECRET_KEY", cast=str)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
