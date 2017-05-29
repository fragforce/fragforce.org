from fragforce import app
from flask import Blueprint, render_template, session, redirect, url_for, \
    request, abort
from flask_flatpages import FlatPages, pygments_style_defs
import re
import os

mod = Blueprint('general', __name__)
RE_FW_TABLE_NAME = re.compile(r'^[a-zA-Z]+\.(nets|ports|urls|ips)$')


@mod.route('/')
def index(name=None):
    return render_template('general/index.html', name=name)


@mod.route('/contact')
def contact(name=None):
    return render_template('general/contact.html', name=name)


@mod.route('/donate')
def donate(name=None):
    return render_template('general/donate.html', name=name)


@mod.route('/join')
def join(name=None):
    return render_template('general/join.html', name=name)


@mod.route('/tracker')
def tracker(name=None):
    return render_template('tracker.html', name=name)


@mod.route('/static/css/pygments.css')
def pygments_css():
    return pygments_style_defs(), 200, {'Content-Type': 'text/css'}


@mod.route('/firewalls/tables/<string:table_type>/<string:fname>')
def section_archives_year(table_type, fname):
    if table_type not in ['ports', 'urls', 'nets']:
        abort(404)
    if fname not in os.listdir(os.path.join(app.template_folder, 'fwaliases', table_type)):
        abort(404)
    if not RE_FW_TABLE_NAME.match(fname):
        abort(404)

    return render_template('fwaliases/%s/%s' % (table_type, fname), table_type=table_type)
