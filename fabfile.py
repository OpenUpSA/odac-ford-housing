from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from contextlib import contextmanager


def staging():
    """
    Env parameters for the staging environment.
    """

    env.hosts = ['54.194.210.25']
    env.envname = 'staging'
    env.user = 'ubuntu'
    env.group = 'ubuntu'
    env.key_filename = '~/.ssh/aws_code4sa.pem'
    env.code_dir = '/var/www/odac-ford-housing'
    env.config_dir = 'config_staging'
    env.activate = 'source %s/env/bin/activate' % env.code_dir
    print("STAGING ENVIRONMENT\n")


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
    # reboot once, to let redis start up automatically
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
        sudo('service uwsgi restart')
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
    sudo('apt-get install python-pip')
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
    Configure uwsgi, Nginx & Flask. Then restart.
    """

    with settings(warn_only=True):
        sudo('stop uwsgi')

    with settings(warn_only=True):
        # disable default site
        sudo('rm /etc/nginx/sites-enabled/default')

    # upload nginx server blocks (virtualhost)
    put(env.config_dir + '/nginx.conf', '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf %s/nginx.conf' % env.code_dir)

    with settings(warn_only=True):
        sudo('ln -s %s/nginx.conf /etc/nginx/conf.d/' % env.code_dir)

    # upload uwsgi config
    put(env.config_dir + '/uwsgi.ini', '/tmp/uwsgi.ini')
    sudo('mv /tmp/uwsgi.ini %s/uwsgi.ini' % env.code_dir)

    # make directory for uwsgi's log
    with settings(warn_only=True):
        sudo('mkdir -p /var/log/uwsgi')
        sudo('chown -R www-data:www-data /var/log/uwsgi')

    with settings(warn_only=True):
        sudo('mkdir -p /etc/uwsgi/vassals')

    # upload upstart configuration for uwsgi 'emperor', which spawns uWSGI processes
    put(env.config_dir + '/uwsgi.conf', '/tmp/uwsgi.conf')
    sudo('mv /tmp/uwsgi.conf /etc/init/uwsgi.conf')

    with settings(warn_only=True):
        # create symlinks for emperor to find config file
        sudo('ln -s %s/uwsgi.ini /etc/uwsgi/vassals' % env.code_dir)

    # upload flask config
    with settings(warn_only=True):
        sudo('mkdir %s/instance' % env.code_dir)
    put(env.config_dir + '/config.py', '/tmp/config.py')
    sudo('mv /tmp/config.py %s/instance/config.py' % env.code_dir)
    put(env.config_dir + '/config_private.py', '/tmp/config_private.py')
    sudo('mv /tmp/config_private.py %s/instance/config_private.py' % env.code_dir)

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

    sudo('touch %s/msg_handler/uwsgi.sock' % env.code_dir)

    # clean out old logfiles
    with settings(warn_only=True):
        sudo('rm %s/debug.log*' % env.code_dir)

    # ensure notification list exists
    sudo('touch %s/instance/notification_list.json' % env.code_dir)

    set_permissions()
    restart()
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