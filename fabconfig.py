#### START OF FABRIC CONFIGURATION ####

# Use local_settings.py to override settings.
# This file should be outside of control version. 
# Copy local_settings_template.py as a starting point.
try:
    from local_settings import *
except ImportError:
    pass

# DO NOT USE TRAILING SLASH AND USE UNDERSCORES IN DIRECTORIES TO MIMIC django-admin.py starproject.
PROJECT_USER = 'user'

PROJECT_NAME = 'django_gunicorn_project' # Used for upstart script and virtualenv
PROJECT_DESCRIPTIVE_NAME = 'The Django gunicorn project' # Used as description in upstart script

# with the new Django 1.4 project layout there's an inner project directory at PROJECT_DIR/PROJECT_INNER_DIR
PROJECT_DIR = '/home/user/django_gunicorn_project'
PROJECT_INNER_DIR = 'django_gunicorn_project'
PROJECT_LOGDIR = '/home/alexis/logs/django_gunicorn_project'
PROJECT_SCRIPT_NAME = 'run-' + PROJECT_NAME

PROJECT_DOMAIN = 'example.com'
PROJECT_DOMAIN_STAGING = 'staging.example.com'
PROJECT_DOMAIN_DEVELOPMENT = 'development.example.com'

# This will be in local, outside of version control, and should use DEBUG conditionals for switching between development/staging and production settings,
# see local_settings_template.py (which is not used by the project) for example.
PROJECT_SETTINGS_PATH = '/home/user/djsettings/django_gunicorn_project_local_settings.py'

PROJECT_GUNICORN_LOGLEVEL = 'info'
PROJECT_GUNICORN_NUM_WORKERS = 3
PROJECT_GUNICORN_BIND_IP = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT = '8000'

PROJECT_NGINX_IP = '192.168.0.185'
PROJECT_NGINX_PORT = '80'

PROJECT_NGINX_IP_STAGING = '192.168.0.185'
PROJECT_NGINX_PORT_STAGING = '81'

PROJECT_NGINX_IP_DEVELOPMENT = '192.168.0.185'
PROJECT_NGINX_PORT_DEVELOPMENT = '82'

# Some of these values are shared by development when not specified here, update build_projects_var function if needed
PROJECT_GUNICORN_LOGLEVEL_STAGING = 'debug'
PROJECT_GUNICORN_NUM_WORKERS_STAGING = 3
PROJECT_GUNICORN_BIND_IP_STAGING = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT_STAGING = '8001'

PROJECT_GUNICORN_BIND_PORT_DEVELOPMENT = '8002'

PROJECT_LOG_GUNICORN = 'gunicorn.log'
PROJECT_LOG_NGINX_ACCESS = 'nginx-access.log'
PROJECT_LOG_NGINX_ERROR = 'nginx-error.log'

PROJECT_REPO_TYPE = 'git'
PROJECT_REPO_URL = 'git@github.com:user/My-Project.git'

EXTRA_APPS = (
    {
        'name': 'someapp', 
        'production':  {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp',
                       },
        'staging':     {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp_staging',
                       },
        'development': {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp_development',
                       },
    },
    {
        'name': 'anotherapp', 
        'production':  {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project/django-someapp',
                        'dir': '/home/user/django_gunicorn_project/django-someapp',
                       },
        'staging':     {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project_staging/django-someapp',
                        'dir': '/home/user/django_gunicorn_project_staging/django-someapp',
                       },
        'development': {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project_development/django-someapp',
                        'dir': '/home/user/django_gunicorn_project_development/django-someapp',
                       },
    },
)

# Web servers should be setup one by one.
# Public ip and port to be used by Nginx will be passed for each web server in setup_nginx.

UBUNTU_PACKAGES=('man',
                 'manpages',
                 'git-core',
                 'nginx',
                 'python-pip',
                 'postgresql-server-dev-9.1',
                 'postgresql-client-9.1',
                 'sqlite3',
                 'python-dev'
                )

PIP_PACKAGES=('virtualenv',
              'virtualenvwrapper',
              'Fabric',
             )

PIP_VENV_PACKAGES=('psycopg2',
                   'ipython',
                   'yolk',
                   'Django==1.4',
                   'gunicorn',
                   'Fabric',
                   'South',
                   'Sphinx',
                   'docutils',
                  )

MIRROR_URL = '-i http://d.pypi.python.org/simple'

#### END OF CONFIGURATION ####
