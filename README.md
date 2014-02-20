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


NOTES:
------
To access this server via SSH:

    ssh -v -i ~/.ssh/aws_code4sa.pem ubuntu@54.194.210.25


Logs can be found at:

* Flask:

        /var/www/odac-ford-housing/debug.log

* Nginx:

        /var/log/nginx/error.log
        /var/log/nginx/access.log

* uWSGI:

        /var/log/uwsgi/emperor.log
        /var/log/uwsgi/uwsgi.log