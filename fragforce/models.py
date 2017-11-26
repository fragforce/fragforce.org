""" Database schema

WARNING: DON'T FORGET TO RUN 'alembic revision --autogenerate -m "<message>"' AFTER ANY CHANGES TO THE SCHEMA!!!!

Also need to run ```heroku run --app=<APP NAME> bash upgrade_db.sh``` on all apps
"""
import datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, backref, deferred
from sqlalchemy.dialects.postgresql import UUID, ENUM, HSTORE, ARRAY, JSONB
from fragforce import app, Base, RemoteBaseMeta, engine
import uuid
import enum


class Location(Base):
    """ An SFDC Office Location """
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), unique=True, nullable=False)
    code = Column(String(4), unique=True, nullable=False)
    country_code = Column(String(255), nullable=False)
    address = Column(Text(), nullable=False)
    primary_contact_id = Column(Integer, ForeignKey('contacts.id'))
    primary_contact = relation('Contacts')


class Contacts(Base):
    """ An office contact """
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    display_name = Column(String(255), unique=True, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))
    location = relation(Location, backref=backref('contacts', order_by=display_name))


class Firewall(Base):
    """ A Fragforce Firewall """
    HARDWARE_TYPE_STANDARD_V0_LOW = 'Standard v0 Low'
    HARDWARE_TYPE_STANDARD_V0_HIGH = 'Standard v0 High'
    HARDWARE_TYPE_CUSTOM = 'Custom'

    __tablename__ = 'firewalls'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), unique=True, nullable=False)
    fqdn = Column(String(4096), nullable=False)
    alt_fqdns = Column(ARRAY(String(4096)), nullable=False, default=[])
    hardware_type = Column(Enum(HARDWARE_TYPE_STANDARD_V0_LOW, HARDWARE_TYPE_STANDARD_V0_HIGH, HARDWARE_TYPE_CUSTOM,
                                name='hardware_types'), nullable=True, default=HARDWARE_TYPE_CUSTOM)
    last_seen = Column(DateTime(), nullable=True, default=None)


class Host(Base):
    """ A Fragforce server or host """
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), unique=True, nullable=False)
    trusted = Column(Boolean, nullable=True)


class Network(Base):
    """ A Fragforce Network """
    __tablename__ = 'networks'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False)
    trusted_network = Column(Boolean, nullable=True)


class FirewallInterface(Base):
    __tablename__ = "fw_interfaces"
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False)
    fqdn = Column(String(4096), nullable=False)
    alt_fqdns = Column(ARRAY(String(4096)), nullable=False, default=[])
    ip_address = Column(String(255), nullable=False)
    netmask = Column(String(255), nullable=False)
    mac_address = Column(String(255), nullable=False)
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False)
    network = relation(Network, backref=backref('interfaces', order_by=ip_address))
    mac_whitelisted = Column(Boolean, nullable=True, default=None)
    firewall_id = Column(Integer, ForeignKey('firewalls.id'), nullable=False)
    firewall = relation(Firewall, backref=backref('interfaces', order_by=name))


class HostInterface(Base):
    __tablename__ = "host_interfaces"
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False)
    fqdn = Column(String(4096), nullable=False)
    alt_fqdns = Column(ARRAY(String(4096)), nullable=False, default=[])
    ip_address = Column(String(255), nullable=False)
    netmask = Column(String(255), nullable=False)
    mac_address = Column(String(255), nullable=False)
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False)
    network = relation(Network, backref=backref('interfaces', order_by=ip_address))
    host_id = Column(Integer, ForeignKey('hosts.id'), nullable=False)
    host = relation(Host, backref=backref('interfaces', order_by=name))


class PortGroup(Base):
    """ A group of port(s) """
    TCP = 'TCP'
    UDP = 'UDP'

    __tablename__ = 'port_groups'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), unique=True, nullable=False)
    ports = Column(ARRAY(Integer, dimensions=2), nullable=False, default=[])
    proto = Column(Enum(TCP, UDP, name='protocol_types'), nullable=True)


class PageFile(Base):
    FILE_TYPE_IMAGE = 'image'
    FILE_TYPE_BIN = 'binary'

    __tablename__ = 'page_file'
    id = Column(Integer, primary_key=True)
    guid = Column(UUID, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    filename = Column(String(255), unique=False, nullable=False)
    page = Column(String(255), unique=False, nullable=False)
    title = Column(String(255), unique=False, nullable=False)
    desc = Column(Text, nullable=False, default='')
    uploaded_at = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow())
    s3path = Column(String(8192), nullable=False) # May be the guid - for now - don't assume this will always be the case
    published = Column(Boolean, nullable=False, default=False)
    ftype = Column(String(255), nullable=False, default=FILE_TYPE_IMAGE)
