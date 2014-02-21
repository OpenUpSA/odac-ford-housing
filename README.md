odac-ford-housing
=================

USSD, SMS &amp; Web application for disseminating information relating to the progress of government housing projects.

http://ford-housing.demo4sa.org/

Local setup:
------------
Install Redis

Run Redis:

    redis-server

In an new terminal window, create a virtual environment:

    virtualenv --no-site-packages env
    source env/bin/activate

Install python libraries:

    pip install -r requirements/local.txt

Run Flask dev server:

    python runserver.py


Deploy the application via fabric:
----------------------------------
Install fabric

    pip install fabric

Setup application folder, and install requirements

    fab production setup

Install Redis (note: this reboots the server)

    fab production install_redis

Configure Nginx, supervisor, gunicorn & Flask

    fab production configure

Deploy application package

    fab production deploy

Initiate an empty db

    fab production rebuild_db



NOTES:
------
Access the staging server via SSH with:

    ssh -v -i ~/.ssh/aws_code4sa.pem ubuntu@54.194.210.25


Logs, on staging, can be found at:

* Flask:

        /var/www/odac-ford-housing/debug.log

* Nginx:

        /var/log/nginx/error.log
        /var/log/nginx/access.log