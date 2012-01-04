"""
This Fabric script allows you setup an Ubuntu 11.10 server to run a Django project with Nginx and gunicorn.

For detailed instructions see README in the project's root.

1. This step is optional. If you still haven't created a user to run the project you can start with an existing user to create one:
fab -H existing_user@host add_user:user

That will create user with a random password and sudo permissions.

2. Then you can use this user to continue the setup, the named parameters staging_ip and staging_port are optional.
fab -H user@host setup:mirror=y,ip=192.168.0.181,port=80,staging_ip=192.168.0.181,staging_port=81

Only if you provide staging_ip and staging_port the staging environment will be enabled. The staging virtualenv will be always created
and the staging directory will be always used to get the code from the repository, even if not staging site is activated.
We will never go directly from repository to production.

3. Later, to update project files and run the project.
fab -H user@host start_project:update_settings=y,staging=y

Staging can be accessed at http://PROJECT_DOMAIN_STAGING:staging_port
Production can be accessed at http://PROJECT_DOMAIN:port

"""

from fabric.api import run, sudo, hosts, settings, abort, warn, cd, local, put, get, env
from fabric.contrib.files import exists, sed, comment
from fabric.contrib.files import append as fabappend
from fabric.contrib.console import confirm
from fabric.utils import warn

import string, random

#### START OF CONFIGURATION ####

# DO NOT USE TRAILING SLASH AND USE UNDERSCORES IN DIRECTORIES TO MIMIC django-admin.py starproject.
PROJECT_USER = 'alexis'

PROJECT_NAME = 'django_gunicorn_project'
PROJECT_DESCRIPTIVE_NAME = 'A Django gunicorn project' # Used as description in upstart script
PROJECT_DIR = '/home/alexis/django_gunicorn_project'
PROJECT_LOGDIR = '/home/alexis/logs/django_gunicorn_project'
PROJECT_SCRIPT_NAME = 'run-' + PROJECT_NAME
PROJECT_DOMAIN = 'example.com'

# This will be in local, outside of version control, and should use DEBUG conditionals for switching between staging and production settings,
# see local_settings_template.py (which is not used by the project) for example.

PROJECT_STAGING_SETTINGS_PATH = '/home/alexis/djsettings/django_gunicorn_project_local_settings.py'

PROJECT_GUNICORN_LOGLEVEL = 'info'
PROJECT_GUNICORN_NUM_WORKERS = 3
PROJECT_GUNICORN_BIND_IP = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT = '8000'

STAGING_SUFFIX = 'staging'
PROJECT_NAME_STAGING = PROJECT_NAME + '_' + STAGING_SUFFIX
PROJECT_DESCRIPTIVE_NAME_STAGING = PROJECT_DESCRIPTIVE_NAME + '_' + STAGING_SUFFIX
PROJECT_DIR_STAGING = PROJECT_DIR + '_' + STAGING_SUFFIX
PROJECT_LOGDIR_STAGING = PROJECT_LOGDIR + '_' + STAGING_SUFFIX
PROJECT_SCRIPT_NAME_STAGING = PROJECT_SCRIPT_NAME + '-' + STAGING_SUFFIX
PROJECT_DOMAIN_STAGING = 'example-staging.com'
PROJECT_GUNICORN_LOGLEVEL_STAGING = 'debug'
PROJECT_GUNICORN_NUM_WORKERS_STAGING = 3
PROJECT_GUNICORN_BIND_IP_STAGING = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT_STAGING = '8001'
PROJECT_GUNICORN_BIND_ADDRESS = '%s:%s' % (PROJECT_GUNICORN_BIND_IP, PROJECT_GUNICORN_BIND_PORT)
PROJECT_GUNICORN_BIND_ADDRESS_STAGING = '%s:%s' % (PROJECT_GUNICORN_BIND_IP_STAGING, PROJECT_GUNICORN_BIND_PORT_STAGING)

PROJECT_LOG_GUNICORN = 'gunicorn.log'
PROJECT_LOG_NGINX_ACCESS = 'nginx-access.log'
PROJECT_LOG_NGINX_ERROR = 'nginx-error.log'

PROJECT_REPO_TYPE = 'git' # TODO adapt to others, only git to start
PROJECT_REPO_URL = 'alexis@githost:git/znbone.git'

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
			 )

PIP_VENV_PACKAGES=('psycopg2==2.4.1',
                   'ipython',
				   'Django==1.3.1',
				   'gunicorn',
				   'Fabric',
				   'docutils',
		     	  )

#### END OF CONFIGURATION ####

def add_user(user):
    sudo('useradd %s -s /bin/bash -m' % user)
    sudo('echo "%s ALL=(ALL) ALL" >> /etc/sudoers' % user)
    password = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    sudo('echo "%s:%s" | chpasswd' % (user, password))
    print "Password for %s is %s" % (user, password)

def setup_server(mirror=''):
    # TODO support for pip mirrors, see setup_django
	for p in UBUNTU_PACKAGES:
		sudo('apt-get -y install %s' % p)
	sudo('pip install pip --upgrade')
	
	for p in PIP_PACKAGES:
		sudo('sudo pip install %s' % p)

    # fixes Warning: cannot find svn location for distribute==0.6.16dev-r0
	sudo('pip install distribute --upgrade')

    # TODO check if lines are already there to avoid duplication
	run('echo "export WORKON_HOME=$HOME/.virtualenvs" >> /home/%s/.bash_profile' % PROJECT_USER)
	run('echo "source /usr/local/bin/virtualenvwrapper.sh" >> /home/%s/.bash_profile' % PROJECT_USER)
	
	# need this for interactive shell
	run('echo "export WORKON_HOME=$HOME/.virtualenvs" >> /home/%s/.bashrc' % PROJECT_USER)
	run('echo "source /usr/local/bin/virtualenvwrapper.sh" >> /home/%s/.bashrc' % PROJECT_USER)

	sudo('chown -R %(PROJECT_USER)s:%(PROJECT_USER)s /home/%(PROJECT_USER)s/.virtualenvs' % {'PROJECT_USER': PROJECT_USER})

def setup_django(mirror=''):
    create_log_directories()
    mirror_url = 'http://d.pypi.python.org/simple'

    for name in (PROJECT_NAME, PROJECT_NAME_STAGING):
        run('mkvirtualenv %s' % name)
        for p in PIP_VENV_PACKAGES:
            if mirror != 'y':
                run('workon %s && pip install %s' % (name, p))
            else:
                run('workon %s && pip install %s -i %s' % (name, p, mirror_url))

def run_tests(apps=''):
    # TODO test on staging and production, is this needed or just with development and staging is enough?
    # TODO apps is a semicolon separated list of apps, convert to list first
    #run("./manage.py test my_app")
    with cd(PROJECT_DIR):
        run('workon %s && python manage.py test' % PROJECT_NAME)

def deploy(server='staging'):
    run_tests()
    # TODO commit and probably push

def create_log_directories():
    for dir in (PROJECT_LOGDIR, PROJECT_LOGDIR_STAGING):
        if not exists(dir):
            run('mkdir -p %s' % dir)
            # these need to be created by the user to avoid permission problems when running Nginx and gunicorn
            run('touch %s/%s' % (dir, PROJECT_LOG_GUNICORN))
            run('touch %s/%s' % (dir, PROJECT_LOG_NGINX_ACCESS))
            run('touch %s/%s' % (dir, PROJECT_LOG_NGINX_ERROR))

def put_settings_files():
    """ Only used when called explicitly, we don't want to change settings by default"""
    if exists(PROJECT_DIR_STAGING):
        put(PROJECT_STAGING_SETTINGS_PATH, '%s/%s' % (PROJECT_DIR_STAGING, 'local_settings.py'))

    if exists(PROJECT_DIR):
        put(PROJECT_STAGING_SETTINGS_PATH, '%s/%s' % (PROJECT_DIR, 'local_settings.py'))
        with cd(PROJECT_DIR):
            sed('local_settings.py', '^DEBUG = True$', 'DEBUG = False') 

def update_project_files(update_settings=''):
    if exists(PROJECT_DIR_STAGING):
        run('cd %s && git pull' % PROJECT_DIR_STAGING)
    else:
        run('git clone %s %s' % (PROJECT_REPO_URL, PROJECT_DIR_STAGING))

    run('rsync -az --delete-after --exclude=.git --exclude=.gitignore --exclude=deploy --exclude=local_settings*  --exclude=*.pyc --exclude=*.pyo %s/ %s' % (PROJECT_DIR_STAGING, PROJECT_DIR))

	# TODO customize for other Python versions and probably other GNU/Linux distributions

    project_dict = {'PROJECT_USER': PROJECT_USER, 'PROJECT_NAME': PROJECT_NAME, 'PROJECT_NAME_STAGING': PROJECT_NAME_STAGING}

    if not exists('/home/%(PROJECT_USER)s/%(PROJECT_NAME)s/static' % project_dict):
        run('mkdir -p /home/%(PROJECT_USER)s/%(PROJECT_NAME)s/static' % project_dict)

    if not exists('/home/%(PROJECT_USER)s/%(PROJECT_NAME_STAGING)s/static' % project_dict):
        run('mkdir -p /home/%(PROJECT_USER)s/%(PROJECT_NAME_STAGING)s/static' % project_dict)

    if not exists('/home/%(PROJECT_USER)s/%(PROJECT_NAME)s/static/admin' % project_dict):
        run('ln -s /home/%(PROJECT_USER)s/.virtualenvs/%(PROJECT_NAME)s/lib/python2.7/site-packages/django/contrib/admin/media/ /home/%(PROJECT_USER)s/%(PROJECT_NAME)s/static/admin' % project_dict)

    if not exists('/home/%(PROJECT_USER)s/%(PROJECT_NAME_STAGING)s/static/admin' % project_dict):
        run('ln -s /home/%(PROJECT_USER)s/.virtualenvs/%(PROJECT_NAME_STAGING)s/lib/python2.7/site-packages/django/contrib/admin/media/ /home/%(PROJECT_USER)s/%(PROJECT_NAME_STAGING)s/static/admin' % project_dict)

    if update_settings == 'y':
        put_settings_files()

def put_config_files(ip='', port='', staging_ip='', staging_port=''):

    # fix for nginx: [emerg] could not build the server_names_hash, you should increase server_names_hash_bucket_size: 32
    sed('/etc/nginx/nginx.conf', '# server_names_hash_bucket_size.*', 'server_names_hash_bucket_size 64;', use_sudo=True) 

    put('deploy', '/tmp/')
    if staging_ip != '' and staging_port != '':
        staging = True
    else:
        staging = False

    with cd('/tmp/deploy/'):
        if staging:
            run('cp run-project run-project-%s' % STAGING_SUFFIX)
            run('cp etc/nginx/sites-available/django-project etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX)
            run('cp etc/init/django-project.conf etc/init/django-project-%s.conf' % STAGING_SUFFIX)

        sed('run-project', '^LOGFILE.*', 'LOGFILE=%s/%s' % (PROJECT_LOGDIR, PROJECT_LOG_GUNICORN)) 
        sed('run-project', '^LOGLEVEL.*', 'LOGLEVEL=%s' % PROJECT_GUNICORN_LOGLEVEL) 
        sed('run-project', '^NUM_WORKERS.*', 'NUM_WORKERS=%s' % PROJECT_GUNICORN_NUM_WORKERS) 
        sed('run-project', '^BIND_ADDRESS.*', 'BIND_ADDRESS=%s' % PROJECT_GUNICORN_BIND_ADDRESS) 
        sed('run-project', '^USER.*', 'USER=%s' % PROJECT_USER) 
        sed('run-project', '^GROUP.*', 'GROUP=%s' % PROJECT_USER) 
        sed('run-project', '^PROJECTDIR.*', 'PROJECTDIR=%s' % PROJECT_DIR) 
        sed('run-project', '^PROJECTENV.*', 'PROJECTENV=/home/%s/.virtualenvs/%s' % (PROJECT_USER, PROJECT_NAME)) 

        sed('etc/nginx/sites-available/django-project', 'listen.*', 'listen %s:%s;' % (ip, port)) 
        sed('etc/nginx/sites-available/django-project', 'proxy_pass http.*', 'proxy_pass http://%s:%s/;' % (PROJECT_GUNICORN_BIND_IP, PROJECT_GUNICORN_BIND_PORT)) 
        sed('etc/nginx/sites-available/django-project', 'example\.com', '%s' % PROJECT_DOMAIN) 
        sed('etc/nginx/sites-available/django-project', 'root.*', 'root %s;' % PROJECT_DIR) 
        sed('etc/nginx/sites-available/django-project', 'access_log.*', 'access_log %s/%s;' % (PROJECT_LOGDIR, PROJECT_LOG_NGINX_ACCESS)) 
        sed('etc/nginx/sites-available/django-project', 'error_log.*', 'access_log %s/%s;' % (PROJECT_LOGDIR, PROJECT_LOG_NGINX_ERROR)) 
        
        sed('etc/init/django-project.conf', '^description.*', 'description "%s"' % PROJECT_DESCRIPTIVE_NAME) 
        sed('etc/init/django-project.conf', '^exec.*', 'exec /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME)) 

        run('cp /tmp/deploy/run-project /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME))
        run('chmod u+x /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME)) 
        sudo('cp /tmp/deploy/etc/nginx/sites-available/django-project /etc/nginx/sites-available/%s' % PROJECT_NAME)
        sudo('cp /tmp/deploy/etc/init/django-project.conf /etc/init/%s.conf' % PROJECT_NAME)
        
        if not exists('/etc/nginx/sites-enabled/%s' % PROJECT_NAME):
        	sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (PROJECT_NAME, PROJECT_NAME))
        
        if exists('/etc/nginx/sites-enabled/default'):
        	sudo('rm /etc/nginx/sites-enabled/default')
        
        if not exists('/etc/init.d/%s' % PROJECT_NAME):
        	sudo('ln -s /lib/init/upstart-job /etc/init.d/%s' % PROJECT_NAME)

        if staging:
            sed('run-project-%s' % STAGING_SUFFIX, '^LOGFILE.*', 'LOGFILE=%s/%s' % (PROJECT_LOGDIR_STAGING, PROJECT_LOG_GUNICORN)) 
            sed('run-project-%s' % STAGING_SUFFIX, '^LOGLEVEL.*', 'LOGLEVEL=%s' % PROJECT_GUNICORN_LOGLEVEL_STAGING) 
            sed('run-project-%s' % STAGING_SUFFIX, '^NUM_WORKERS.*', 'NUM_WORKERS=%s' % PROJECT_GUNICORN_NUM_WORKERS_STAGING) 
            sed('run-project-%s' % STAGING_SUFFIX, '^BIND_ADDRESS.*', 'BIND_ADDRESS=%s' % PROJECT_GUNICORN_BIND_ADDRESS_STAGING) 
            sed('run-project-%s' % STAGING_SUFFIX, '^USER.*', 'USER=%s' % PROJECT_USER)
            sed('run-project-%s' % STAGING_SUFFIX, '^GROUP.*', 'GROUP=%s' % PROJECT_USER)
            sed('run-project-%s' % STAGING_SUFFIX, '^PROJECTDIR.*', 'PROJECTDIR=%s' % PROJECT_DIR_STAGING)
            sed('run-project-%s' % STAGING_SUFFIX, '^PROJECTENV.*', 'PROJECTENV=/home/%s/.virtualenvs/%s' % (PROJECT_USER, PROJECT_NAME_STAGING)) 

            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'listen.*', 'listen %s:%s;' % (staging_ip, staging_port)) 
            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'proxy_pass http.*', 'proxy_pass http://%s:%s/;' % (PROJECT_GUNICORN_BIND_IP_STAGING, PROJECT_GUNICORN_BIND_PORT_STAGING)) 
            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'example\.com', '%s' % PROJECT_DOMAIN_STAGING) 
            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'root.*', 'root %s;' % PROJECT_DIR_STAGING) 
            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'access_log.*', 'access_log %s/%s;' % (PROJECT_LOGDIR_STAGING, PROJECT_LOG_NGINX_ACCESS)) 
            sed('etc/nginx/sites-available/django-project-%s' % STAGING_SUFFIX, 'error_log.*', 'access_log %s/%s;' % (PROJECT_LOGDIR_STAGING, PROJECT_LOG_NGINX_ERROR)) 
            
            sed('etc/init/django-project-%s.conf' % STAGING_SUFFIX, '^description.*', 'description "%s"' % PROJECT_DESCRIPTIVE_NAME_STAGING) 
            sed('etc/init/django-project-%s.conf' % STAGING_SUFFIX, '^exec.*', 'exec /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME_STAGING)) 

            run('cp /tmp/deploy/run-project-%s /home/%s/%s' % (STAGING_SUFFIX, PROJECT_USER, PROJECT_SCRIPT_NAME_STAGING))
            run('chmod u+x /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME_STAGING)) 
            sudo('cp /tmp/deploy/etc/nginx/sites-available/django-project-%s /etc/nginx/sites-available/%s' % (STAGING_SUFFIX, PROJECT_NAME_STAGING))
            sudo('cp /tmp/deploy/etc/init/django-project-%s.conf /etc/init/%s.conf' % (STAGING_SUFFIX, PROJECT_NAME_STAGING))
            
            if not exists('/etc/nginx/sites-enabled/%s' % PROJECT_NAME_STAGING):
            	sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (PROJECT_NAME_STAGING, PROJECT_NAME_STAGING))
            
            if not exists('/etc/init.d/%s' % PROJECT_NAME_STAGING):
            	sudo('ln -s /lib/init/upstart-job /etc/init.d/%s' % PROJECT_NAME_STAGING)

	run('rm -rf /tmp/deploy')

def put_apps():
    # TODO install or update apps needed by the project, you should add your apps with this function
    pass

def clean():
    with settings(warn_only=True):
        sudo('service nginx stop')
        result = sudo('service %s stop' % PROJECT_NAME)
    if result.failed:
        warn( "%s was not running." % PROJECT_NAME)

    with settings(warn_only=True):
        result = sudo('service %s stop' % PROJECT_NAME_STAGING)
    if result.failed:
        warn( "%s was not running." % PROJECT_NAME_STAGING)

    for name in (PROJECT_NAME, PROJECT_NAME_STAGING):
        sudo('rmvirtualenv %s' % name)

    with settings(warn_only=True):
        for dir in (PROJECT_DIR, PROJECT_DIR_STAGING, PROJECT_LOGDIR, PROJECT_LOGDIR_STAGING):
            sudo('rm -rf %s' % dir)

        sudo('rm /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME))
        sudo('rm /etc/nginx/sites-enabled/%s' % PROJECT_NAME)
        sudo('rm /etc/nginx/sites-available/%s' % PROJECT_NAME)
        sudo('rm /etc/init/%s.conf' % PROJECT_NAME)
        sudo('rm /etc/init.d/%s' % PROJECT_NAME)
        sudo('rm /home/%s/%s' % (PROJECT_USER, PROJECT_SCRIPT_NAME_STAGING))
        sudo('rm /etc/nginx/sites-enabled/%s' % PROJECT_NAME_STAGING)
        sudo('rm /etc/nginx/sites-available/%s' % PROJECT_NAME_STAGING)
        sudo('rm /etc/init/%s.conf' % PROJECT_NAME_STAGING)
        sudo('rm /etc/init.d/%s' % PROJECT_NAME_STAGING)

def restart_project(staging=''):
    sudo('service nginx restart')

    with settings(warn_only=True):
        result = sudo('service %s restart' % PROJECT_NAME)
    if result.failed:
        warn( "%s was not running, starting for the first time." % PROJECT_NAME)
        result = sudo('service %s start' % PROJECT_NAME)

    if staging == 'y':
        with settings(warn_only=True):
            result = sudo('service %s restart' % PROJECT_NAME_STAGING)
        if result.failed:
            warn( "%s was not running, starting for the first time." % PROJECT_NAME_STAGING)
            result = sudo('service %s start' % PROJECT_NAME_STAGING)

def setup(mirror='', ip='', port='', staging_ip='', staging_port=''):
    setup_server()
    setup_django(mirror)
    put_config_files(ip, port, staging_ip, staging_port)

def start_project(update_settings='', staging=''):
    update_project_files(update_settings)
    # TODO install or update apps needed by the project, you should add your apps with this function
    # put_apps()
    restart_project(staging)
