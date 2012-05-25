"""
This Fabric script allows you setup an Ubuntu 11.10 server to run a Django project with Nginx and gunicorn.

For detailed instructions see README in the project's root.

"""

from fabric.api import run, sudo, hosts, settings, abort, warn, cd, local, put, get, env
from fabric.contrib.files import exists, sed, comment, contains
from fabric.contrib.files import append as fabappend
from fabric.contrib.console import confirm
from fabric.utils import warn
from fabric.context_managers import hide
from fabric.contrib import django

import string, random

def build_projects_vars():
    settings = get_settings()
    projects = {'production': {}, 'staging': {}, 'development': {}}

    projects['production']['user'] = projects['staging']['user'] = projects['development']['user'] = settings.PROJECT_USER
    projects['production']['inner_dir'] = projects['staging']['inner_dir'] = projects['development']['inner_dir'] = settings.PROJECT_INNER_DIR
    projects['production']['repo_url'] = projects['staging']['repo_url'] = projects['development']['repo_url'] = settings.PROJECT_REPO_URL

    projects['production']['settings_path'] = projects['staging']['settings_path'] = projects['development']['settings_path'] = settings.PROJECT_SETTINGS_PATH

    projects['production']['domain'] = settings.PROJECT_DOMAIN
    projects['staging']['domain'] = settings.PROJECT_DOMAIN_STAGING
    projects['development']['domain'] = settings.PROJECT_DOMAIN_DEVELOPMENT

    projects['production']['gunicorn_loglevel'] = settings.PROJECT_GUNICORN_LOGLEVEL
    projects['staging']['gunicorn_loglevel'] = projects['development']['gunicorn_loglevel'] = settings.PROJECT_GUNICORN_LOGLEVEL_STAGING

    projects['production']['gunicorn_num_workers'] = settings.PROJECT_GUNICORN_NUM_WORKERS
    projects['staging']['gunicorn_num_workers'] = projects['development']['gunicorn_num_workers'] = settings.PROJECT_GUNICORN_NUM_WORKERS_STAGING

    projects['production']['gunicorn_bind_ip'] = settings.PROJECT_GUNICORN_BIND_IP
    projects['staging']['gunicorn_bind_ip'] = projects['development']['gunicorn_bind_ip'] = settings.PROJECT_GUNICORN_BIND_IP_STAGING

    projects['production']['gunicorn_bind_port'] = settings.PROJECT_GUNICORN_BIND_PORT
    projects['staging']['gunicorn_bind_port'] = settings.PROJECT_GUNICORN_BIND_PORT_STAGING
    projects['development']['gunicorn_bind_port'] = settings.PROJECT_GUNICORN_BIND_PORT_DEVELOPMENT

    for key in projects.keys():
        projects[key]['name'] = suffix(settings.PROJECT_NAME, key)
        projects[key]['descriptive_name'] = suffix(settings.PROJECT_DESCRIPTIVE_NAME, key)
        projects[key]['dir'] = suffix(settings.PROJECT_DIR, key)
        projects[key]['run-project'] = suffix('run-project', key)
        projects[key]['django-project'] = suffix('django-project', key)
        projects[key]['logdir'] = suffix(settings.PROJECT_LOGDIR, key)
        projects[key]['log_gunicorn'] = settings.PROJECT_LOG_GUNICORN
        projects[key]['log_nginx_access'] = settings.PROJECT_LOG_NGINX_ACCESS
        projects[key]['log_nginx_error'] = settings.PROJECT_LOG_NGINX_ERROR
        projects[key]['script_name'] = suffix(settings.PROJECT_SCRIPT_NAME, key)
        projects[key]['gunicorn_bind_address'] = '%s:%s' % (projects[key]['gunicorn_bind_ip'], projects[key]['gunicorn_bind_port'])

        if key == 'production':
            projects[key]['ip'] = settings.PROJECT_NGINX_IP
            projects[key]['port'] = settings.PROJECT_NGINX_PORT

        if key == 'staging':
            projects[key]['ip'] = settings.PROJECT_NGINX_IP_STAGING
            projects[key]['port'] = settings.PROJECT_NGINX_PORT_STAGING

        if key == 'development':
            projects[key]['ip'] = settings.PROJECT_NGINX_IP_DEVELOPMENT
            projects[key]['port'] = settings.PROJECT_NGINX_PORT_DEVELOPMENT

    return projects

def build_parameters_list(projects, key):
    """
    Choose a key and create a list containing the value for that key for the development, staging and production keys
    on the projects dictionary.
    """
    seq = []
    projects = build_projects_vars()
    for project in projects.values():
        seq.append(project[key])
    return seq

def suffix(string, suffix, sep = '_'):
    """
    Adds a suffix to staging and development values.
    Example: if dir_name is the value for production then dir_name_staging and dir_name_development will
    be used for staging and development.
    """
    if suffix == 'production':
        suffixed = string
    else:
        suffixed = string + sep + suffix
    return suffixed

def debug(x=''):
    """
    Simple debugging of some functions
    """
    settings = get_settings()
    print settings.ROOT_URLCONF
    print settings.TIME_ZONE
    print settings.EXTRA_APPS

def get_settings():
    import os
    import sys

    # gets project name, which is the directory where settings is
    for dirpath, dirnames, filenames in os.walk('.'):
        if dirpath != '.':
            dirname = dirpath.split('/')[1]
            if dirname not in ('docs', 'deploy', 'static', 'templates', '.git') and 'settings.py' in filenames:
                settings_module = '%s.settings' % dirname

    django.settings_module(settings_module)

    root_dir = os.path.dirname(__file__)
    sys.path.insert(0, root_dir)

    from django.conf import settings
    return settings

def add_user(user):
    sudo('useradd %s -s /bin/bash -m' % user)
    sudo('echo "%s ALL=(ALL) ALL" >> /etc/sudoers' % user)
    password = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    sudo('echo "%s:%s" | chpasswd' % (user, password))
    print "Password for %s is %s" % (user, password)

def fix_venv_permission():
    projects = build_projects_vars()
    project = projects['development'] # could use any environment as key user is always the same
    with settings(hide('warnings'), warn_only=True):
        sudo('chown -R %(user)s:%(user)s /home/%(user)s/.virtualenvs' % {'user': project['user']})

def setup_server(mirror=''):
    settings = get_settings()
    projects = build_projects_vars()
    project = projects['development'] # could use any environment as key user is always the same

    if mirror == 'y':
        mirror_url = settings.MIRROR_URL
    else:
        mirror_url = ''

    for p in settings.UBUNTU_PACKAGES:
        sudo('apt-get -y install %s' % p)

    sudo('pip install pip --upgrade %s' % mirror_url)
    
    for p in settings.PIP_PACKAGES:
        sudo('sudo pip install %s %s' % (p, mirror_url))

    # fixes Warning: cannot find svn location for distribute==0.6.16dev-r0
    sudo('pip install distribute --upgrade %s' % mirror_url)

    fix_venv_permission()

    for file in ('.bash_profile', '.bashrc'):
        if not contains('/home/%s/%s' % (project['user'], file), 'export WORKON_HOME'):
            run('echo "export WORKON_HOME=$HOME/.virtualenvs" >> /home/%s/%s' % (project['user'], file))
        if not contains('/home/%s/%s' % (project['user'], file), 'source /usr/local/bin/virtualenvwrapper.sh'):
            run('echo "source /usr/local/bin/virtualenvwrapper.sh" >> /home/%s/%s' % (project['user'], file))

def setup_django(*args, **kwargs):
    settings = get_settings()
    projects = build_projects_vars()
    mirror = kwargs.get('mirror','n')
    if mirror == 'y':
        mirror_url = settings.MIRROR_URL
    else:
        mirror_url = ''

    for key in args:
        if not exists(projects[key]['logdir']):
            run('mkdir -p %s' % projects[key]['logdir'])
            # these need to be created by the user to avoid permission problems when running Nginx and gunicorn
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_gunicorn']))
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_nginx_access']))
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_nginx_error']))

        run('mkvirtualenv %s' % projects[key]['name'])

        for p in settings.PIP_VENV_PACKAGES:
            run('workon %s && pip install %s %s' % (projects[key]['name'], p, mirror_url))

def put_settings_files(env='development'):
    """
    Only used when called explicitly, we don't want to change settings by default
    """
    projects = build_projects_vars()
    project = projects[env]
    if exists('%(dir)s/%(inner_dir)s' % project):
        put(project['settings_path'], '%(dir)s/%(inner_dir)s/local_settings.py' % project)
        if env == 'production':
            with cd('%(dir)s/%(inner_dir)s' % project):
                sed('local_settings.py', '^DEBUG = True$', 'DEBUG = False') 

# TODO revisit how the apps are committed and update from production, it may be safer using different
# repositories or probably branches.

def update_apps(env='development', upgrade_apps='n'):
    """
    Install the project related apps. It can use pip install from a repository or use the editable option to install from a source directory.
    Examples of commands generated:
    pip install git+ssh://user@githost/home/user/someapp.git
    pip install -e /home/user/anotherapp/
    """

    settings = get_settings()
    projects = build_projects_vars()
    project = projects[env]

    for app in settings.EXTRA_APPS:
        option = ''
        if app[env]['type'] == 'git' and upgrade_apps == 'y':
            option = '--upgrade'
        if app[env]['type'] == 'editable':
            option = '-e'

        run('workon %(name)s && pip install %(option)s %(source)s' % {'name': project['name'], 'option': option, 'source': app[env]['source']})

def update_project(env='development', update_settings='n'):
    projects = build_projects_vars()
    project = projects[env]

    # TODO check if previous setup steps done, optional to avoid following the correct order manually
    # TODO check that staging env is set before running for production, optional to avoid following the correct order manually

    if env == 'production':
        if exists(projects['staging']['dir']):
            run('rsync -az --delete-after --exclude=.git --exclude=.gitignore --exclude=deploy --exclude=local_settings*  --exclude=*.pyc --exclude=*.pyo %s/ %s' % (projects['staging']['dir'], project['dir']))
        else:
            print "Staging environment doesn't exist. Please create it before running update_project for production on this host."
    else:
        if exists(project['dir']):
            run('cd %(dir)s && git pull' % project)
        else:
            run('git clone %(repo_url)s %(dir)s' % project)

    if not exists('%(dir)s/static' % project):
        run('mkdir -p %(dir)s/static' % project)

    if not exists('%(dir)s/static/admin' % project):
        run('ln -s /home/%(user)s/.virtualenvs/%(name)s/lib/python2.7/site-packages/django/contrib/admin/static/admin/ %(dir)s/static/admin' % project)

    if update_settings == 'y':
        put_settings_files(env)

def put_config_files(*args):
    """
    Call with the names of the enviroments where you want to put the config files, for example:
    fab -H user@host put_config_files:production,staging,development
    """
    # fix for nginx: Starting nginx: nginx: [emerg] could not build the types_hash, you should increase either types_hash_max_size: 1024 or types_hash_bucket_size: 32
    sed('/etc/nginx/nginx.conf', '# types_hash_max_size.*', 'types_hash_max_size 2048;', use_sudo=True) 
    # fix for nginx: [emerg] could not build the server_names_hash, you should increase server_names_hash_bucket_size: 32
    sed('/etc/nginx/nginx.conf', '# server_names_hash_bucket_size.*', 'server_names_hash_bucket_size 64;', use_sudo=True) 
    put('deploy', '/tmp/')
    projects = build_projects_vars()

    for key in args:
        """
        Copy basic configuration files, this has to be done first for all environments to avoid changing the original contents
        required by sed on the next loop.
        """
        with cd('/tmp/deploy/'):
            print "COPYING CONFIGURATION FILES FOR  %s..." % key
            if key != 'production':
                run('cp run-project %(run-project)s' % projects[key])
                run('cp etc/nginx/sites-available/django-project etc/nginx/sites-available/%(django-project)s' % projects[key])
                run('cp etc/init/django-project.conf etc/init/%(django-project)s.conf' % projects[key])

    for key in args:
        """
        Loop over the original configuration files, make changes with sed and then copy to final locations.
        """
        with cd('/tmp/deploy/'):
            print "SETTING UP CONFIGURATION FILES FOR %s..." % key
            sed(projects[key]['run-project'], '^LOGFILE.*', 'LOGFILE=%(logdir)s/%(log_gunicorn)s' % projects[key]) 
            sed(projects[key]['run-project'], '^LOGLEVEL.*', 'LOGLEVEL=%(gunicorn_loglevel)s' % projects[key]) 
            sed(projects[key]['run-project'], '^NUM_WORKERS.*', 'NUM_WORKERS=%(gunicorn_num_workers)s' % projects[key]) 
            sed(projects[key]['run-project'], '^BIND_ADDRESS.*', 'BIND_ADDRESS=%(gunicorn_bind_ip)s:%(gunicorn_bind_port)s' % projects[key]) 
            sed(projects[key]['run-project'], '^USER.*', 'USER=%(user)s' % projects[key]) 
            sed(projects[key]['run-project'], '^GROUP.*', 'GROUP=%(user)s' % projects[key]) 
            sed(projects[key]['run-project'], '^PROJECTDIR.*', 'PROJECTDIR=%(dir)s' % projects[key]) 
            sed(projects[key]['run-project'], '^PROJECTENV.*', 'PROJECTENV=/home/%(user)s/.virtualenvs/%(name)s' % projects[key]) 

            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'listen.*', 'listen %(ip)s:%(port)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'proxy_pass http.*', 'proxy_pass http://%(gunicorn_bind_ip)s:%(gunicorn_bind_port)s/;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'example\.com', '%(domain)s' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'root.*', 'root %(dir)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'access_log.*', 'access_log %(logdir)s/%(log_nginx_access)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'error_log.*', 'error_log %(logdir)s/%(log_nginx_error)s;' % projects[key]) 

            sed('etc/init/%(django-project)s.conf' % projects[key], '^description.*', 'description "%(descriptive_name)s"' % projects[key]) 
            sed('etc/init/%(django-project)s.conf' % projects[key], '^exec.*', 'exec /home/%(user)s/%(script_name)s' % projects[key]) 

            fix_venv_permission()
            run('cp %(run-project)s /home/%(user)s/%(script_name)s' % projects[key])
            run('chmod u+x /home/%(user)s/%(script_name)s' % projects[key]) 
            sudo('cp etc/nginx/sites-available/%(django-project)s /etc/nginx/sites-available/%(name)s' % projects[key])
            sudo('cp etc/init/%(django-project)s.conf /etc/init/%(name)s.conf' % projects[key])

            if not exists('/etc/nginx/sites-enabled/%(name)s' % projects[key]):
            	sudo('ln -s /etc/nginx/sites-available/%(name)s /etc/nginx/sites-enabled/%(name)s' % projects[key])
            
            if not exists('/etc/init.d/%(name)s' % projects[key]):
            	sudo('ln -s /lib/init/upstart-job /etc/init.d/%(name)s' % projects[key])

    with settings(hide('warnings'), warn_only=True):
        fix_venv_permission()
        sudo('rm /etc/nginx/sites-enabled/default')
        run('rm -rf /tmp/deploy')

def clean(*args, **kwargs):
    """
    Clean before reinstalling. It can be called for multiple environments and there's an optional clean_nginx argument at the end.
    fab -H user@host clean:production,staging,development,clean_nginx=y
    """

    settings = get_settings()
    projects = build_projects_vars()

    with settings(hide('warnings'), warn_only=True):
        sudo('service nginx stop')
        for key in args:
            print "CLEANING CONFIGURATION FILES AND STOPPING SERVICES FOR %s..." % key
            result = sudo('service %(name)s stop' % projects[key])
            if result.failed:
                warn( "%(name)s was not running." % projects[key])

            for app in settings.EXTRA_APPS:
                run('workon %s && pip uninstall -y %s' % (projects[key]['name'], app['name']))

            sudo('rm -rf %(dir)s' % projects[key])
            sudo('rm -rf %(logdir)s' % projects[key])
            sudo('rmvirtualenv %(name)s' % projects[key])
            sudo('rm /home/%(user)s/%(script_name)s' % projects[key])
            sudo('rm /etc/nginx/sites-enabled/%(name)s' % projects[key])
            sudo('rm /etc/nginx/sites-available/%(name)s' % projects[key])
            sudo('rm /etc/init/%(name)s.conf' % projects[key])
            sudo('rm /etc/init.d/%(name)s' % projects[key])

    if kwargs.get('clean_nginx','n') == 'y':
        sed('/etc/nginx/nginx.conf', 'types_hash_max_size.*', '# types_hash_max_size 2048;', use_sudo=True) 
        sed('/etc/nginx/nginx.conf', 'server_names_hash_bucket_size.*', '# server_names_hash_bucket_size 64;', use_sudo=True) 

    fix_venv_permission()

def setup(*args, **kwargs):
    """
    Call with the names of the enviroments to setup and optionally add the mirror keyword argument.
    fab -H user@host setup:production,staging,development,mirror=y
    """
    mirror = kwargs.get('mirror','n')
    setup_server(mirror)
    setup_django(*args, **kwargs)
    put_config_files(*args)

def update_site(env='development', update_settings='n', upgrade_apps='n'):
    """
    Update files for the project and its companion apps.
    """
    update_project(env, update_settings)
    update_apps(env, upgrade_apps)

def start_site(env='development'):
    sudo('service nginx start')

    projects = build_projects_vars()
    project = projects[env]

    with settings(hide('warnings'), warn_only=True):
        result = sudo('service %s start' % project['name'])
    if result.failed:
        warn( "%s already running." % project['name'])

def stop_site(env='development'):
    sudo('service nginx stop')

    projects = build_projects_vars()
    project = projects[env]

    with settings(hide('warnings'), warn_only=True):
        result = sudo('service %s stop' % project['name'])
    if result.failed:
        warn( "%s was not running." % project['name'])

def restart_site(env='development'):
    stop_site(env)
    start_site(env)

def commit(env='development', message='', push='n', test='y'):
    """
    Run tests, add, commit and push files for the project and extra apps.
    Notice this adds all changed files to git index. This can e replaced by manual git commands if more granularity is needed.
    """

    settings = get_settings()
    projects = build_projects_vars()
    project = projects[env]

    if env != 'production':
        print "========================================================"
        print "COMMIT IN %s..." % env.upper()
        # TODO testing before committing
        #run_tests(env)
        for app in settings.EXTRA_APPS:
            if app[env]['dir'][:len(project['dir'])] == project['dir']:
                print "\nThe application %s is inside the project directory, no need to commit separately." % app['name']
            else:
                with settings(hide('warnings'), warn_only=True):
                    print "\nCommitting changes for application %s in %s." % (app['name'], app[env]['dir'])
                    local("cd %s && git add . && git commit -m '%s'" % (app[env]['dir'], message))
                    if push == 'y':
                        local("cd %s && git push" % app[env]['dir'])

        with settings(hide('warnings'), warn_only=True):
            print "\nCommitting changes in the directory project %s." % project['dir']
            local("cd %s && git add . && git commit -m '%s'" % (project['dir'], message))
            if push == 'y':
                local("cd %s && git push" % project['dir'])
        print "========================================================"

def run_tests(env='development'):
    # TODO test on development, staging and production? I think so
    # TODO allow testing per app, use a parameter
    #run("./manage.py test my_app")
    projects = build_projects_vars()
    project = projects[env]
    with cd(project['dir']):
        run('workon %s && python manage.py test' % project['dir'])

def deploy(env='development', update_settings='n', upgrade_apps='n'):
    """
    Run update the site and then restart it for the specified environment. Run after successful test and commit.
    """
    update_site(env, update_settings, upgrade_apps)
    restart_site(env)
