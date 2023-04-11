#!/usr/bin/env bash

cd /code
# Load hc schema
# ffsfdc.sql generated with pg_dump --clean --schema org --no-owner --schema-only --no-comments --if-exists --no-acl $HC_RO_URL
cat /code/dev/ffsfdc.sql | pipenv run python manage.py dbshell --database hc
# Migrate public db
pipenv run python manage.py migrate
# Collect static files
pipenv run python manage.py collectstatic --no-input
