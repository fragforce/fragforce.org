import boto
from boto.s3.key import Key

import os.path
from uuid import uuid4
from werkzeug.utils import secure_filename
from fragforce import app, session_scope, db_session, fcache
import re
from .models import *
import uuid

EXT_MATCH = re.compile(r'^[a-zA-Z0-9]+$')


class FileNotFoundError(ValueError):
    """ File wasn't found """


class NotPublishedError(ValueError):
    """ File isn't published """


class FileUploadsDisabledError(ValueError):
    """ File uploads are not enabled """


class BadExtensionError(ValueError):
    """ File extension doesn't make sense """


def _file_uploads_enabled():
    if not app.config['FILE_UPLOADS']:
        raise FileUploadsDisabledError("File uploads disabled")


def upload(data, s3path, acl='private'):
    """ Upload a file to S3
    :argument src_file: File upload object
    :argument s3path: The PageFile GUID. Used as the S3 key
    :argument acl: S3 ACL to use http://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
    """
    _file_uploads_enabled()  # Make sure image uploads are enabled

    # http://boto.cloudhackers.com/en/latest/s3_tut.html
    conn = boto.connect_s3(app.config["BUCKETEER_AWS_ACCESS_KEY_ID"], app.config["BUCKETEER_AWS_SECRET_ACCESS_KEY"])
    b = conn.get_bucket(app.config["BUCKETEER_BUCKET_NAME"])

    sml = Key(b)
    sml.key = s3path
    sml.set_contents_from_string(data)
    sml.set_acl(acl)


def upload_image_form_f(img_form, page):
    """ Process an image upload form """
    _file_uploads_enabled()  # Make sure image uploads are enabled

    assert not img_form.validate_on_submit(), 'Expected form to already be validated'

    # Get the file ext
    # https://docs.python.org/2/library/os.path.html#os.path.splitext
    # Not a simple text split!
    ext=os.path.splitext(secure_filename(img_form.img.data.filename))[1]
    if not EXT_MATCH.match(ext):
        raise BadExtensionError("Bad Extension")
    filename = "%s%s" % (uuid.uuid4(), ext)

    with session_scope(parent=db_session) as session:
        pfile = PageFile(
            title=img_form.title,
            desc=img_form.desc,
            published=img_form.published,
            ftype=PageFile.FILE_TYPE_IMAGE,
            filename=filename,
            page=page,
        )

        session.add(pfile)
        session.commit()

        upload(img_form.img.data.read(), s3path=pfile.guid)
        return pfile.id, pfile.guid, pfile.filename


@fcache.memoize()
def fetch_s3_file(s3path):
    """ Fetch a file from S3 - Function cached """
    _file_uploads_enabled()  # Make sure image uploads are enabled

    conn = boto.connect_s3(app.config["BUCKETEER_AWS_ACCESS_KEY_ID"], app.config["BUCKETEER_AWS_SECRET_ACCESS_KEY"])
    b = conn.get_bucket(app.config["BUCKETEER_BUCKET_NAME"])

    # TODO: Wrap in try/except to raise FileNotFoundError when file doesn't exist
    sml = Key(b)
    sml.key = s3path
    return sml.get_contents_from_string()


def fetch_file(id=None, guid=None, filename=None, req_published=True):
    """ Fetch a file from S3. Use redis cache if possible """
    _file_uploads_enabled()  # Make sure image uploads are enabled

    # Get the PageFile record
    assert id or guid or filename, "Expected at least id, guid, or filename to be given as args"
    with session_scope(parent=db_session) as session:
        pfq = session.query(PageFile)
        if id:
            pfq.filter_by(id=id)
        if guid:
            pfq.filter_by(guid=guid)
        if filename:
            pfq.filter_by(filename=filename)
        pfile = pfq.first()
        if not pfile:
            raise FileNotFoundError("PageFile(id=%r,guid=%r,filename=%r) Not Found" % (id, guid, filename))

        if req_published and not pfile.published:
            raise NotPublishedError("File isn't published")

        return dict(id=pfile.id, guid=pfile.guid, filename=pfile.filename, title=pfile.title, desc=pfile.desc,
                    ftype=pfile.ftype, fdata=fetch_s3_file(s3path=pfile.s3path), published=pfile.published)
