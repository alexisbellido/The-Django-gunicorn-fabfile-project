DEBUG = True

#if DEBUG:
#	# add my apps to PYTHONPATH, ideally in production these apps should installed in the virtualenv via pip
#    import os
#    import sys
#    I can add a list of paths and add them to sys.path in one command
#    sys.path.insert(0, "/app-parent-dir")

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': '',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': '',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

STATIC_ROOT = ''
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'REPLACE-THIS-IS-A-PLACEHOLDER-KEY-$xy*t!si3gfl60o9^-*a3(hz0r%572t25mo5o8&vx99fbfp*+-'

#MIDDLEWARE_CLASSES = (
#    'middleware.DeleteSessionOnLogoutMiddleware', # Varnish http://ghughes.com/blog/2011/11/11/using-varnish-with-django-for-high-performance-caching/
#    'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#)

ROOT_URLCONF = 'urls' # no need to include project name

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'gunicorn', # you need this one to launch the Django project with gunicorn
)
