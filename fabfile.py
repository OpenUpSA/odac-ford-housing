from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from contextlib import contextmanager


def common():
    """
    Common environment parameters
    """

    env.activate = 'source %s/env/bin/activate' % env.code_dir
    return

def staging():
    """
    Env parameters for the staging environment.
    """

    env.hosts = ['54.194.210.25']
    env.user = 'ubuntu'
    env.envname = 'staging'
    env.key_filename = '~/.ssh/aws_code4sa.pem'
    env.code_dir = '/var/www/odac-ford-housing'
    env.config_dir = 'config_staging'
    common()
    print("STAGING ENVIRONMENT\n")
    return


def production():
    """
    Env parameters for the staging environment.
    """

    env.host_string = 'adi@197.221.34.5:2222'
    env.envname = 'production'
    env.code_dir = '/var/www/ford-housing.code4sa.org'
    env.config_dir = 'config_production'
    common()
    print("PRODUCTION ENVIRONMENT\n")
    return


@contextmanager
def virtualenv():
    with cd(env.code_dir):
        with prefix(env.activate):
            yield


def configure_redis():

    # upload config file
    put('instance/redis.conf', '/tmp/redis.conf')
    sudo('mv -f /tmp/redis.conf /etc/redis/6379.conf')

    return


def install_redis():
    """
    Install the redis key-value store on port 6379
    http://redis.io/topics/quickstart
    """
    sudo('apt-get install tcl8.5')
    with cd(env.code_dir):
        sudo('wget http://download.redis.io/redis-stable.tar.gz')
        sudo('tar xvzf redis-stable.tar.gz')
        with cd('redis-stable'):
            sudo('make')
            sudo('make test')
            if confirm("Do you want to continue?"):
                #continue processing
                sudo('cp src/redis-server /usr/local/bin/')
                sudo('cp src/redis-cli /usr/local/bin/')
            with settings(warn_only=True):
                # create dir for config files, data and log
                sudo('mkdir /etc/redis')
                sudo('mkdir /var/redis')
                sudo('touch /var/log/redis_6379.log')
            # init file for handling server restart
            sudo('cp utils/redis_init_script /etc/init.d/redis_6379')
            # copy config file
            sudo('cp redis.conf /etc/redis/6379.conf')
            with settings(warn_only=True):
                # create working directory
                sudo('mkdir /var/redis/6379')

            # ensure redis restarts if the server reboots
            sudo('update-rc.d redis_6379 defaults')

    configure_redis()
    # a reboot is required for redis to start up nicely
    sudo('reboot')
    return


def test_redis():

    sudo('redis-cli ping')
    return


def restart_redis():

    with settings(warn_only=True):
        sudo('/etc/init.d/redis_6379 stop')
    sudo('/etc/init.d/redis_6379 start')
    return


def restart():

    with settings(warn_only=True):
        sudo('service nginx restart')
        sudo('supervisorctl restart odac-ford-housing')
    return


def set_permissions():
    """
     Ensure that www-data has access to the application folder
    """

    sudo('chmod -R 775 ' + env.code_dir)
    sudo('chown -R www-data:www-data ' + env.code_dir)
    return


def setup():
    """
    Install dependencies and create an application directory.
    """

    with settings(warn_only=True):
        sudo('service nginx stop')

    # update locale
    sudo('locale-gen en_ZA.UTF-8')

    # install packages
    sudo('apt-get install build-essential python python-dev')
    sudo('apt-get install python-pip supervisor')
    sudo('pip install virtualenv')

    # create application directory if it doesn't exist yet
    with settings(warn_only=True):
        if run("test -d %s" % env.code_dir).failed:
            # create project folder
            sudo('mkdir -p ' + env.code_dir)
            sudo('mkdir -p %s/msg_handler' % env.code_dir)
            sudo('mkdir %s/instance' % env.code_dir)
        if run("test -d %s/env" % env.code_dir).failed:
            # create virtualenv
            sudo('virtualenv --no-site-packages %s/env' % env.code_dir)

    # install the necessary Python packages
    with virtualenv():
        put('requirements/base.txt', '/tmp/base.txt')
        put('requirements/production.txt', '/tmp/production.txt')
        sudo('pip install -r /tmp/production.txt')

    # install nginx
    sudo('apt-get install nginx')
    # restart nginx after reboot
    sudo('update-rc.d nginx defaults')
    sudo('service nginx start')

    set_permissions()
    return


def configure():
    """
    Configure Nginx, supervisor & Flask. Then restart.
    """

    with settings(warn_only=True):
        # disable default site
        sudo('rm /etc/nginx/sites-enabled/default')

    # upload nginx server blocks (virtualhost)
    put(env.config_dir + '/nginx.conf', '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf %s/nginx_odac-ford-housing.conf' % env.code_dir)

    with settings(warn_only=True):
        sudo('ln -s %s/nginx_odac-ford-housing.conf /etc/nginx/conf.d/' % env.code_dir)

    # upload supervisor config
    put(env.config_dir + '/supervisor.conf', '/tmp/supervisor.conf')
    sudo('mv /tmp/supervisor.conf /etc/supervisor/conf.d/supervisor_odac-ford-housing.conf')
    sudo('supervisorctl reread')
    sudo('supervisorctl update')

    # upload flask config
    with settings(warn_only=True):
        sudo('mkdir %s/instance' % env.code_dir)
    put(env.config_dir + '/config.py', '/tmp/config.py')
    sudo('mv /tmp/config.py %s/instance/config.py' % env.code_dir)
    put(env.config_dir + '/config_private.py', '/tmp/config_private.py')
    sudo('mv /tmp/config_private.py %s/instance/config_private.py' % env.code_dir)

    # upload rebuild_db script
    put('rebuild_db.py', '/tmp/rebuild_db.py')
    sudo('mv /tmp/rebuild_db.py %s/rebuild_db.py' % env.code_dir)

    set_permissions()
    restart()
    return


def deploy():
    """
    Upload our package to the server, unzip it, and restart.
    """

    # create a tarball of our package
    local('tar -czf msg_handler.tar.gz msg_handler/', capture=False)

    # upload the source tarball to the temporary folder on the server
    put('msg_handler.tar.gz', '/tmp/msg_handler.tar.gz')

    with settings(warn_only=True):
        sudo('service nginx stop')

    # enter application directory
    with cd(env.code_dir):
        # and unzip new files
        sudo('tar xzf /tmp/msg_handler.tar.gz')

    # now that all is set up, delete the tarball again
    sudo('rm /tmp/msg_handler.tar.gz')
    local('rm msg_handler.tar.gz')

    sudo('touch %s/msg_handler/gunicorn.sock' % env.code_dir)

    # clean out old logfiles
    with settings(warn_only=True):
        sudo('rm %s/debug.log*' % env.code_dir)

    # ensure notification list exists
    sudo('touch %s/instance/notification_list.json' % env.code_dir)

    set_permissions()
    restart()
    return


def rebuild_db():

    with cd(env.code_dir):
        with virtualenv():
            sudo('python rebuild_db.py')
    return


def upload_db():
    """
    Overwrite the db on the server with a copy of the local db.
    """

    # upload db
    put('instance/ford-housing.db', '/tmp/ford-housing.db')
    sudo('mv /tmp/ford-housing.db %s/instance/ford-housing.db' % env.code_dir)

    set_permissions()
    return


def download_db():
    """
    Overwrite the local db with a copy from the server.
    """

    get('%s/instance/ford-housing.db' % env.code_dir, 'instance/ford-housing.db')
    return