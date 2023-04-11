#!/usr/bin/env bash

cd /code
cat /code/dev/ffsfdc.sql | pipenv run python manage.py dbshell --database hc
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic --no-input
