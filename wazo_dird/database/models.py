# Copyright 2016-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Sequence,
    String,
    Text,
    schema,
    sql,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, HSTORE, JSON, UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

Base = declarative_base()

UUID_LENGTH = 36


class Contact(Base):
    __tablename__ = 'dird_contact'
    __table_args__ = (
        schema.UniqueConstraint('user_uuid', 'hash'),
        schema.UniqueConstraint(
            'phonebook_uuid',
            'hash',
        ),
        schema.Index('dird_contact__idx__user_uuid', 'user_uuid'),
        schema.Index('dird_contact__idx__phonebook_uuid', 'phonebook_uuid'),
    )

    uuid = Column(
        String(38), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    user_uuid = Column(
        String(UUID_LENGTH), ForeignKey('dird_user.user_uuid', ondelete='CASCADE')
    )

    phonebook_uuid = Column(
        UUID(as_uuid=False), ForeignKey('dird_phonebook.uuid', ondelete='CASCADE')
    )
    hash = Column(String(40), nullable=False)

    phonebook = relationship(lambda: Phonebook, foreign_keys=[phonebook_uuid])

    fields = relationship(
        lambda: ContactFields,
        lazy='subquery',
        passive_deletes=True,
        cascade='all, delete-orphan',
    )

    @property
    def fields_dict(self):
        return {field.name: field.value for field in self.fields}


class ContactFields(Base):
    __tablename__ = 'dird_contact_fields'
    __table_args__ = (
        schema.Index('dird_contact_fields__idx__contact_uuid', 'contact_uuid'),
    )

    id = Column(Integer(), primary_key=True)
    name = Column(Text(), nullable=False, index=True)
    value = Column(Text(), index=True)
    contact_uuid = Column(
        String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), nullable=False
    )


class Display(Base):
    __tablename__ = 'dird_display'
    __table_args__ = (
        schema.UniqueConstraint('uuid', 'tenant_uuid'),
        schema.Index('dird_display__idx__tenant_uuid', 'tenant_uuid'),
    )

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    tenant_uuid = Column(
        String(UUID_LENGTH), ForeignKey('dird_tenant.uuid', ondelete='CASCADE')
    )
    name = Column(Text(), nullable=False)

    columns = relationship('DisplayColumn', viewonly=True)


class DisplayColumn(Base):
    __tablename__ = 'dird_display_column'

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    display_uuid = Column(
        String(UUID_LENGTH), ForeignKey('dird_display.uuid', ondelete='CASCADE')
    )
    field = Column(Text())
    title = Column(Text())
    type = Column(Text())
    default = Column(Text())
    number_display = Column(Text())

    display = relationship('Display')


class Favorite(Base):
    __tablename__ = 'dird_favorite'

    source_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_source.uuid', ondelete='CASCADE'),
        primary_key=True,
    )
    contact_id = Column(Text(), primary_key=True)
    user_uuid = Column(
        String(UUID_LENGTH),
        ForeignKey('dird_user.user_uuid', ondelete='CASCADE'),
        primary_key=True,
    )


class Phonebook(Base):
    __tablename__ = 'dird_phonebook'
    __table_args__ = (
        schema.UniqueConstraint('name', 'tenant_uuid'),
        schema.UniqueConstraint('uuid', 'tenant_uuid'),
        schema.UniqueConstraint('id'),
        schema.CheckConstraint("name != ''"),
        schema.Index('dird_phonebook__idx__tenant_uuid', 'tenant_uuid'),
    )

    id = Column(
        Integer, Sequence("dird_phonebook_id_seq", start=1), nullable=False, unique=True
    )
    uuid = Column(
        UUID(as_uuid=False), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid'))


class Profile(Base):
    __tablename__ = 'dird_profile'
    __table_args__ = (
        schema.UniqueConstraint('uuid', 'tenant_uuid'),
        schema.UniqueConstraint('name', 'tenant_uuid'),
        schema.ForeignKeyConstraint(
            ('display_uuid', 'display_tenant_uuid'),
            ('dird_display.uuid', 'dird_display.tenant_uuid'),
            ondelete='SET NULL',
            name='dird_profile_display_uuid_tenant_fkey',
        ),
        schema.CheckConstraint('tenant_uuid = display_tenant_uuid'),
        schema.Index('dird_profile__idx__tenant_uuid', 'tenant_uuid'),
        schema.Index('dird_profile__idx__display_tenant_uuid', 'display_tenant_uuid'),
        schema.Index('dird_profile__idx__display_uuid', 'display_uuid'),
    )

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    tenant_uuid = Column(
        String(UUID_LENGTH), ForeignKey('dird_tenant.uuid', ondelete='CASCADE')
    )
    name = Column(Text(), nullable=False)
    display_tenant_uuid = Column(String(UUID_LENGTH))
    display_uuid = Column(String(UUID_LENGTH))

    display = relationship('Display')
    services = relationship('ProfileService')


class ProfileServiceSource(Base):
    __tablename__ = 'dird_profile_service_source'
    __table_args__ = (
        schema.ForeignKeyConstraint(
            ('profile_service_uuid', 'profile_tenant_uuid'),
            ('dird_profile_service.uuid', 'dird_profile_service.profile_tenant_uuid'),
            ondelete='CASCADE',
            name='dird_profile_service_source_profile_service_uuid_tenant_fkey',
        ),
        schema.ForeignKeyConstraint(
            ('source_uuid', 'source_tenant_uuid'),
            ('dird_source.uuid', 'dird_source.tenant_uuid'),
            ondelete='CASCADE',
            name='dird_profile_service_source_source_uuid_tenant_fkey',
        ),
        schema.CheckConstraint('profile_tenant_uuid = source_tenant_uuid'),
    )

    profile_service_uuid = Column(String(UUID_LENGTH), primary_key=True)
    profile_tenant_uuid = Column(String(UUID_LENGTH))
    source_uuid = Column(String(UUID_LENGTH), primary_key=True)
    source_tenant_uuid = Column(String(UUID_LENGTH))

    sources = relationship('Source')


class ProfileService(Base):
    __tablename__ = 'dird_profile_service'
    __table_args__ = (
        schema.UniqueConstraint('uuid', 'profile_tenant_uuid'),
        schema.ForeignKeyConstraint(
            ('profile_uuid', 'profile_tenant_uuid'),
            ('dird_profile.uuid', 'dird_profile.tenant_uuid'),
            ondelete='CASCADE',
            name='dird_profile_service_profile_uuid_tenant_fkey',
        ),
        schema.Index(
            'dird_profile_service__idx__profile_uuid',
            'profile_uuid',
        ),
        schema.Index(
            'dird_profile_service__idx__profile_tenant_uuid',
            'profile_tenant_uuid',
        ),
        schema.Index(
            'dird_profile_service__idx__service_uuid',
            'service_uuid',
        ),
    )

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    profile_uuid = Column(String(UUID_LENGTH))
    profile_tenant_uuid = Column(String(UUID_LENGTH))
    service_uuid = Column(
        String(UUID_LENGTH), ForeignKey('dird_service.uuid', ondelete='CASCADE')
    )
    config = Column(JSON)

    service = relationship('Service')
    profile_service_sources = relationship('ProfileServiceSource')
    sources = association_proxy('profile_service_sources', 'sources')


class Service(Base):
    __tablename__ = 'dird_service'

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    name = Column(Text(), unique=True, nullable=False)


class Source(Base):
    __tablename__ = 'dird_source'
    __table_args__ = (
        schema.UniqueConstraint('uuid', 'tenant_uuid'),
        schema.UniqueConstraint('name', 'tenant_uuid'),
        schema.Index('dird_source__idx__tenant_uuid', 'tenant_uuid'),
        schema.ForeignKeyConstraint(
            ('phonebook_uuid', 'tenant_uuid'),
            ('dird_phonebook.uuid', 'dird_phonebook.tenant_uuid'),
            name='dird_source_phonebook_fkey',
            ondelete='CASCADE',
        ),
    )

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    _name = Column(
        'name', Text(), server_default=text('uuid_generate_v4()'), nullable=False
    )
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid'))
    searched_columns = Column(ARRAY(Text))
    first_matched_columns = Column(ARRAY(Text))
    format_columns = Column(HSTORE)
    extra_fields = Column(JSON)
    backend = Column(Text(), nullable=False)
    phonebook_uuid = Column(
        UUID, ForeignKey('dird_phonebook.uuid', ondelete='CASCADE'), nullable=True
    )

    phonebook = relationship(
        lambda: Phonebook, foreign_keys=[phonebook_uuid], lazy='joined'
    )

    @hybrid_property
    def name(self):
        if self.backend == 'phonebook':
            return self.phonebook.name
        else:
            return self._name

    @name.setter
    def name(self, value):
        if self.backend == 'phonebook':
            logger.debug(
                'value %s ignored when setting name on source(uuid=%s) with backend phonebook',
                value,
                self.uuid,
            )
        else:
            self._name = value

    @name.expression
    def name(cls):
        return sql.case(
            [
                (
                    cls.backend == 'phonebook',
                    sql.select([Phonebook.name])
                    .where(Phonebook.uuid == cls.phonebook_uuid)
                    .as_scalar(),
                ),
            ],
            else_=cls._name,
        )


class Tenant(Base):
    __tablename__ = 'dird_tenant'

    uuid = Column(
        String(UUID_LENGTH), server_default=text('uuid_generate_v4()'), primary_key=True
    )
    country = Column(String(2))


class User(Base):
    __tablename__ = 'dird_user'
    __table_args__ = (
        schema.Index('dird_user__idx__tenant_uuid', 'tenant_uuid'),
    )

    user_uuid = Column(String(UUID_LENGTH), primary_key=True)
    tenant_uuid = Column(String(UUID_LENGTH), ForeignKey('dird_tenant.uuid'))
