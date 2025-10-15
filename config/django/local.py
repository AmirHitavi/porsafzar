import os

from .base import *  # noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_LOCAL_SECRET_KEY",
    cast=str,
    default="django-insecure-i%ahewya@d9bi5d(pzsh(4llh#89o09gc1q&yf3oga^ft5kou*",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


INSTALLED_APPS = [
    *INSTALLED_APPS,
    "debug_toolbar",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

INTERNAL_IPS = [
    "127.0.0.1",
]
