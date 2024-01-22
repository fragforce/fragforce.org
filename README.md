# Fragforce
## About
This is a rewrite of Fragforce.org using Django. 

## Who we are
Fragforce is the global charity gaming team from Salesforce that is raising money to support kids facing scary stuff
like social mistreatment and medical issues (i.e. cancer, cystic-fibrosise, accidents, etc). By rallying our
friends, family, and co-workers, we are creating/facilitating a new philanthropic tradition to boost employee morale
and support cross-team and community collaboration through a shared love of gaming.

## Who we are supporting
Extra Life is a charity organization that is raising money to support Children's Miracle Network (CMN) hospitals
across the country. Extra Life helps games to pledge to play games for 24 hours, and to solicit donations from their
families and friends for CMN in the process.

Child's Play is an international charity organization that seeks to improve the lives of children in hospitals and
domestic violence shelters through the generosity and kindness of the video game industry and the power of play.

## How can I donate?
Make a donation to Fragforce's Extra Life team by visiting the Extra Life page and searching for Fragforce, or just
go to team.fragforce.org

Make a donation to Fragforce's Child's Play donation drive by visiting our donation campaign page

## How can I help?
Sign up to participate in an event and raise money as you can to save kid's lives! Simply click the 'Join Team' link
on the Extra Life team page for Fragforce at team.fragforce.org

International team members can raise money for Child's Play, join our Tiltify Team, and sign up to help run or
participate in an international Fragforce event

## Packages

### ffsfdc
Fragforce org to Fragforce.org linkage

### fforg
Project files

### ffsite
Fragforce.org pages

### ffdonations
Various donation sync options

## Development

### Requirements

* [Docker](https://docker.com) 
* [Docker Compose](https://docs.docker.com/compose/)

### Initial Setup

* `cp env.sample .env`
* generate a secret key and set it in the `SECRET_KEY` value in `.env`, not required, but best practice
* `docker-compose up -d` to spin up all the containers
* `docker-compose exec web bash` to shell into the main web container
* `dev/init.sh` to load the hc initial data, run migrations, collectstatic, and activate the pipenv
* `python manage.py shell` to load a django shell, or `python manage.py dbshell` to connect to the database to verify data after running tasks

