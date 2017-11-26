from fragforce import app, session_scope, db_session
from flask import Blueprint, render_template, redirect, url_for, \
    request, abort, Response
from flask_flatpages import FlatPages, pygments_style_defs
import re
import os
from ..models import *

mod = Blueprint('fw', __name__)


class InvalidFWID(ValueError):
    """ Given an invalid firewall id """


def validate_firewall(fw_id, p_session=db_session):
    """ Ensure it's a valid firewall. If so, return a Firewall object """
    with session_scope(parent=p_session) as session:
        fw = session.query(Firewall).filter(guid=fw_id).first()
        if not fw:
            raise InvalidFWID("%r isn't a valid firewall guid" % fw_id)
        fw.last_seen = datetime.datetime.now()
        session.add(fw)
        session.commit()

    return session.query(Firewall).filter(guid=fw_id).first()


@mod.route('/firewalls/<uuid:fw_id>/tables/ports/<string:name>.<string:proto>')
def tables_ports(fw_id, name, proto):
    with session_scope(parent=db_session) as session:
        fw = validate_firewall(fw_id=fw_id, session=session)



@mod.route('/firewalls/<uuid:fw_id>/backups/2.3/alias.xml')
def alias_backup_gen(fw_id):
    """ Return an XML doc that can be restored via the pfsense backup interface. It
    will load all aliases. """
    with session_scope(parent=db_session) as session:
        fw = validate_firewall(fw_id=fw_id, session=session)

    from fragforce.pfsense import AliasBackup
    import os, os.path
    import urllib

    # root_url = FW_ALIAS_PATH_FIXER.match(request.base_url).groups()[0]
    #
    # port_path = os.path.join(app.config['BASE_DIR'], 'fragforce', 'templates', 'fwaliases', 'ports')
    # nets_path = os.path.join(app.config['BASE_DIR'], 'fragforce', 'templates', 'fwaliases', 'nets')

    ab = AliasBackup()

    # def visit_port(aba, dirname, names):
    #     for file_name in names:
    #         path = os.path.join(dirname, file_name)
    #         name = file_name.replace('.nets', '')
    #         name = NAME_CHAR_FIX.sub('_', name)
    #         if file_name.endswith('.ports'):
    #             url = root_url + "/firewalls/tables/ports/" + file_name
    #             ab.add_port_alias(name=file_name.replace('.ports', ''), url=url, update_frequency_days=1,
    #                               description="Port Table %r" % file_name)
    #
    # def visit_nets(aba, dirname, names):
    #     for file_name in names:
    #         path = os.path.join(dirname, file_name)
    #         folder = os.path.split(dirname)[-1]
    #         name = "%s_%s" % (folder, file_name.replace('.nets', '').replace('.ips', ''))
    #         name = NAME_CHAR_FIX.sub('_', name)
    #         if file_name.endswith('.nets'):
    #             url = root_url + "/firewalls/tables/nets/%s/%s" % (folder, file_name)
    #             ab.add_ip_alias(name=name, url=url, update_frequency_days=1,
    #                             description='Network Table %r' % file_name)
    #         elif file_name.endswith('.ips'):
    #             url = root_url + "/firewalls/tables/nets/%s/%s" % (folder, file_name)
    #             ab.add_ip_alias(name=name, url=url, update_frequency_days=1,
    #                             description='IP Table %r' % file_name)
    #
    # os.path.walk(port_path, visit_port, ab)
    # os.path.walk(nets_path, visit_nets, ab)

    return Response(ab.render(pretty=False), mimetype='text/xml')
