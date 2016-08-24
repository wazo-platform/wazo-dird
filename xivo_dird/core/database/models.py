# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from sqlalchemy import (Column, ForeignKey, Integer, schema, String, text, Text)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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


class Favorite(Base):

    __tablename__ = 'dird_favorite'

    source_id = Column(Integer(), ForeignKey('dird_source.id', ondelete='CASCADE'), primary_key=True)
    contact_id = Column(Text(), primary_key=True)
    user_uuid = Column(String(38),
                       ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'),
                       primary_key=True)


class Phonebook(Base):

    __tablename__ = 'dird_phonebook'
    __table_args__ = (
        schema.UniqueConstraint('name', 'tenant_id'),
        schema.CheckConstraint("name != ''"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tenant_id = Column(Integer, ForeignKey('dird_tenant.id'))


class Source(Base):

    __tablename__ = 'dird_source'

    id = Column(Integer(), primary_key=True)
    name = Column(Text(), nullable=False, unique=True)


class Tenant(Base):

    __tablename__ = 'dird_tenant'
    __table_args__ = (
        schema.CheckConstraint("name != ''"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)


class User(Base):

    __tablename__ = 'dird_user'

    xivo_user_uuid = Column(String(38), primary_key=True)
