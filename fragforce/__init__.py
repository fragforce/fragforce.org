from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import MetaData
from flask import Flask, render_template_string, request
from flask_flatpages import FlatPages
from flask_flatpages.utils import pygmented_markdown
from flask_images import Images
from flask_sslify import SSLify
import requests
import os
from flask_cache import Cache
from flask_sqlalchemy import SQLAlchemy
from contextlib import contextmanager


def jinja_renderer(text):
    prerendered_body = render_template_string(text)
    return pygmented_markdown(prerendered_body)


app = Flask(__name__)
sslify = SSLify(app)

app.config['SECTION_MAX_LINKS'] = int(os.environ.get('SECTION_MAX_LINKS', '10'))
app.config['FLATPAGES_HTML_RENDERE'] = jinja_renderer
app.config['DEBUG'] = bool(os.environ.get('DEBUG', 'False').lower() == 'true')
app.config['BASE_DIR'] = os.path.abspath(os.path.dirname(__file__))
app.config['THREADS_PER_PAGE'] = int(os.environ.get('THREADS_PER_PAGE', '2'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'insecure')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgres://postgres@localhost:5432/fragforce')
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DATABASE_URL']
app.config['DATABASE_CONNECT_OPTIONS'] = {}
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', None)
app.config['EXTRALIFE_TEAMID'] = os.environ.get('EXTRALIFE_TEAMID', None)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_DONATIONS_TIME'] = int(os.environ.get('CACHE_DONATIONS_TIME', 300))
app.config['CRON_TEAM_REFRESH_MINUTES'] = int(os.environ.get('CRON_TEAM_REFRESH_MINUTES', 2))
app.config['CRON_PARTICIPANTS_REFRESH_MINUTES'] = int(os.environ.get('CRON_PARTICIPANTS_REFRESH_MINUTES', 2))
app.config['CACHE_DONATIONS_TIME'] = int(os.environ.get('CACHE_DONATIONS_TIME', 120))

# S3
app.config['BUCKETEER_BUCKET_NAME'] = os.environ.get('BUCKETEER_BUCKET_NAME', None)
app.config['BUCKETEER_AWS_SECRET_ACCESS_KEY'] = os.environ.get('BUCKETEER_AWS_SECRET_ACCESS_KEY', None)
app.config['BUCKETEER_AWS_REGION'] = os.environ.get('BUCKETEER_AWS_REGION', None)
app.config['BUCKETEER_AWS_ACCESS_KEY_ID'] = os.environ.get('BUCKETEER_AWS_ACCESS_KEY_ID', None)

# Image Uploads
app.config['FILE_UPLOADS'] = bool(os.environ.get('FILE_UPLOADS', 'False').lower() == 'true')
# Make sure the redis backend is set to auto evect
# FIXME: Automate redis to auto evect
app.config['FILE_CACHE_NAME'] = os.environ.get('FILE_CACHE_NAME', 'CYAN')
app.config['FILE_CACHE_URL'] = os.environ.get('HEROKU_REDIS_%s_URL' % app.config['FILE_CACHE_NAME'], None)

pages = FlatPages(app)
images = Images(app)

engine = create_engine(app.config.get('SQLALCHEMY_DATABASE_URI'), convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=True,
                                         autoflush=True,
                                         bind=engine))
BaseMeta = MetaData(schema='public')
Base = declarative_base(metadata=BaseMeta)
Base.query = db_session.query_property()

RemoteBaseMeta = MetaData(schema='gus')


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import fragforce.models
    Base.metadata.create_all(bind=engine)


def drop_all():
    import fragforce.models
    Base.metadata.drop_all(bind=engine)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@contextmanager
def session_scope(parent=db_session):
    """Provide a transactional scope around a series of operations."""
    session = parent.session_factory()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


init_db()

from fragforce.views import general
from fragforce.views import pages
from fragforce.views import fw

app.register_blueprint(general.mod)
app.register_blueprint(pages.mod)
app.register_blueprint(fw.mod)

# Init cache (general)
if app.config['REDIS_URL']:
    cache = Cache(app, config={'CACHE_KEY_PREFIX': 'cache', 'CACHE_TYPE': 'redis',
                               'CACHE_REDIS_URL': app.config['REDIS_URL']})
else:
    # fallback for local testing
    cache = Cache(app, config={'CACHE_KEY_PREFIX': 'cache', 'CACHE_TYPE': 'simple'})

# Init cache (files)
if app.config['FILE_UPLOADS']:
    if app.config['FILE_CACHE_URL']:
        fcache = Cache(app, config={'CACHE_KEY_PREFIX': 'fcache', 'CACHE_TYPE': 'redis',
                                    'CACHE_REDIS_URL': app.config['FILE_CACHE_URL'],
                                    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24 * 30,
                                    })
    else:
        # fallback for local testing
        fcache = Cache(app, config={'CACHE_KEY_PREFIX': 'fcache', 'CACHE_TYPE': 'simple',
                                    'CACHE_THRESHOLD': 8,
                                    })


@app.context_processor
def random_participant():
    """ Add a random participant to use for donation links to all page contexts """
    from .extralife import participants
    from random import choice
    participant = choice(participants(app.config['EXTRALIFE_TEAMID']))
    return dict(
        rnd_pct=participant,
        rnd_pct_link=participant.donate_link(),
        rnd_pct_name=participant.display_name,
    )


@app.context_processor
def tracker_data():
    def is_active(endpoint=None, section=None, noclass=False):
        rtn = ""
        if noclass:
            rtn = 'active'
        else:
            rtn = 'class=active'
        if endpoint and section:
            if 'section' in request.view_args:
                if request.url_rule.endpoint == endpoint and request.view_args['section'] == section:
                    return rtn
        elif endpoint:
            return rtn if request.url_rule.endpoint == endpoint else ''
        elif section:
            if 'section' in request.view_args:
                return rtn if request.view_args['section'] == section else ''
        return ''

    @cache.memoize(timeout=app.config['CACHE_DONATIONS_TIME'])
    def print_bar(goal, total, percent, label):
        return '   <div>' + \
               '     <div class="progress-text">' + \
               '       <span class="label">' + str(label) + '</span>' + \
               '     </div>' + \
               '     <div class="progress-amount">' + \
               '       <span class="label"> $' + u'{:0,.0f}'.format(float(total)) + ' &#47; $' + u'{:0,.0f}'.format(
            float(goal)) + '</span>' + \
               '     </div>' + \
               '   </div>' + \
               '   <div class="progress">' + \
               '     <div class="progress-bar" role="progressbar" aria-valuenow="60" aria-valuemin="0" ' \
               'aria-valuemax="100" style="' + str(
            percent) + '%; max-width: ' + str(percent) + '%; min-width: 2em; width: ' + str(percent) + '%;">' + \
               '     ' + str(percent) + '% ' + \
               '     </div>' + \
               '   </div>'

    @cache.cached(timeout=app.config['CACHE_DONATIONS_TIME'], key_prefix='tracker_data.print_bars')
    def print_bars():
        extralife_total = 0
        extralife_goal = 0
        extralife_percent = 0
        childsplay_total = 0
        childsplay_goal = 0
        childsplay_percent = 0
        full_total = 0
        full_goal = 0
        full_percent = 0
        try:
            team = extralife.Team.from_url(app.config['EXTRALIFE_TEAMID'])
            extralife_total = team.raised
            extralife_goal = team.goal

            if extralife_goal > 0:
                extralife_percent = u'{:0,.2f}'.format(100 * (extralife_total / extralife_goal))

        except extralife.WebServiceException as e:
            fail = True
        try:
            r = requests.get('https://tiltify.com/api/v2/campaign',
                             headers={'Authorization': 'Token 10e41ff90dbf83dd1b31c7ac902e243c'
                                      })
            if r.status_code == 200:
                data = r.json()
                childsplay_total = data['total_raised']
                childsplay_goal = data['goal']
                childsplay_percent = data['percent_raised'].rstrip("%")
        except requests.exceptions.RequestException as e:
            fail = True
        full_total = extralife_total + childsplay_total
        full_goal = extralife_goal + childsplay_goal
        if full_goal > 0:
            full_percent = u'{:0,.2f}'.format(100 * (full_total / full_goal))
        else:
            full_percent = 0
        return print_bar(extralife_goal, extralife_total, extralife_percent, "Extra Life") + \
               print_bar(childsplay_goal, childsplay_total, childsplay_percent, "Childs Play") + \
               print_bar(full_goal, full_total, full_percent, "Totals")

    return dict(
        print_bar=print_bar,
        print_bars=print_bars,
        extralife_link="http://team.fragforce.org",
        childsplay_link="https://tiltify.com/teams/fragforce",
        is_active=is_active)


import fragforce.extralife as extralife

from apscheduler.schedulers.blocking import BlockingScheduler
from rq import Queue
from worker import conn

sched = BlockingScheduler()
high = Queue('high', connection=conn)
q = Queue('default', connection=conn)
low = Queue('low', connection=conn)
