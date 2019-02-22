# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from uuid import uuid4
from sqlalchemy import (Column, ForeignKey, Integer, schema, String, text, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    HSTORE,
    JSON,
)

Base = declarative_base()

UUID_LENGTH = len(str(uuid4()))


class Contact(Base):

    __tablename__ = 'dird_contact'
    __table_args__ = (
        schema.UniqueConstraint('user_uuid', 'hash'),
        schema.UniqueConstraint('phonebook_id', 'hash'),
    )

    uuid = Column(String(38), server_default=text('uuid_generate_v4()'), primary_key=True)
    user_uuid = Column(String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'))
    phonebook_id = Column(Integer(), ForeignKey('dird_phonebook.id', ondelete='CASCADE'))
    hash = Column(String(40), nullable=False)


class ContactFields(Base):

    __tablename__ = 'dird_contact_fields'

    id = Column(Integer(), primary_key=True)
    name = Column(Text(), nullable=False, index=True)
    value = Column(Text(), index=True)
    contact_uuid = Column(String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), nullable=False)


class Display(Base):

    __tablename__ = 'dird_display'

    uuid = Column(String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid', ondelete='CASCADE'))
    name = Column(Text(), nullable=False)
    columns = relationship('DisplayColumn', viewonly=True)


class DisplayColumn(Base):

    __tablename__ = 'dird_display_column'

    uuid = Column(String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True)
    display_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_display.uuid', ondelete='CASCADE'))
    field = Column(Text())
    title = Column(Text())
    type = Column(Text())
    default = Column(Text())
    number_display = Column(Text())
    display = relationship('Display')


class Favorite(Base):

    __tablename__ = 'dird_favorite'

    source_uuid = Column(
        String(36),
        ForeignKey('dird_source.uuid', ondelete='CASCADE'),
        primary_key=True,
    )
    contact_id = Column(Text(), primary_key=True)
    user_uuid = Column(String(38),
                       ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'),
                       primary_key=True)


class Phonebook(Base):

    __tablename__ = 'dird_phonebook'
    __table_args__ = (
        schema.UniqueConstraint('name', 'tenant_uuid'),
        schema.CheckConstraint("name != ''"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid'))


class Profile(Base):

    __tablename__ = 'dird_profile'

    uuid = Column(String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid', ondelete='CASCADE'))
    name = Column(Text(), nullable=False)
    display_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_display.uuid', ondelete='SET NULL'))

    display = relationship('Display')
    profile_sources = relationship(
        'ProfileSource',
        cascade='all, delete-orphan',
    )
    sources = association_proxy('profile_sources', 'source')
    profile_services = relationship('ProfileService')


class ProfileSource(Base):

    __tablename__ = 'dird_profile_source'

    profile_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_profile.uuid', ondelete='CASCADE'),
        primary_key=True,
    )
    source_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_source.uuid', ondelete='CASCADE'),
        primary_key=True,
    )


class ProfileService(Base):

    __tablename__ = 'dird_profile_service'

    profile_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_profile.uuid', ondelete='CASCADE'),
        primary_key=True,
    )
    service_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_service.uuid', ondelete='CASCADE'),
        primary_key=True,
    )
    config = Column(JSON)
    service = relationship('Service')


class Service(Base):

    __tablename__ = 'dird_service'

    uuid = Column(String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True)
    name = Column(Text(), unique=True, nullable=False)


class Source(Base):

    __tablename__ = 'dird_source'
    __table_args__ = (
        schema.UniqueConstraint('name', 'tenant_uuid'),
    )

    uuid = Column(String(36), server_default=text('uuid_generate_v4()'), primary_key=True)
    name = Column(Text(), nullable=False)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid'))
    searched_columns = Column(ARRAY(Text))
    first_matched_columns = Column(ARRAY(Text))
    format_columns = Column(HSTORE)
    extra_fields = Column(JSON)
    backend = Column(Text(), nullable=False)


class Tenant(Base):

    __tablename__ = 'dird_tenant'

    uuid = Column(String(UUID_LENGTH), server_default=text('uuid_generate_v4()'),  primary_key=True)
    # DEPRECATED uuids should match wazo-auth and names should not be used
    # the field will be removed after an upgrade that forces an upgrade above version 19.02
    name = Column(String(255))


class User(Base):

    __tablename__ = 'dird_user'

    xivo_user_uuid = Column(String(38), primary_key=True)
