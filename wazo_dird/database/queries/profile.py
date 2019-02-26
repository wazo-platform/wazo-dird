# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import (
    and_,
    exc,
    text,
)

from wazo_dird.database import schemas
from wazo_dird import exception

from .base import (
    BaseDAO,
    extract_constraint_name,
)
from ..import (
    Profile,
    ProfileService,
    ProfileServiceSource,
    Service,
)


class ProfileCRUD(BaseDAO):

    _profile_schema = schemas.ProfileSchema()

    def create(self, body):
        with self.new_session() as s:
            self._create_tenant(s, body['tenant_uuid'])
            body['uuid'] = self._create_profile(s, body)
            for service_name, config in body['services'].items():
                service_uuid = self._create_service(s, service_name)
                profile_service_uuid = self._create_profile_service(
                    s, body['uuid'], service_uuid, config,
                )
                for source in config['sources']:
                    source_uuid = source.get('uuid')
                    self._create_profile_service_source(
                        s, profile_service_uuid, source_uuid,
                    )
        return body

    def delete(self, visible_tenants, profile_uuid):
        filter_ = Profile.uuid == profile_uuid
        if visible_tenants is not None:
            if not visible_tenants:
                raise exception.NoSuchProfile(profile_uuid)
            filter_ = and_(filter_, Profile.tenant_uuid.in_(visible_tenants))

        with self.new_session() as s:
            nb_deleted = s.query(Profile).filter(filter_).delete(synchronize_session=False)

        if not nb_deleted:
            raise exception.NoSuchProfile(profile_uuid)

    def get(self, visible_tenants, profile_uuid):
        filter_ = and_(
            Profile.uuid == profile_uuid,
            Profile.tenant_uuid.in_(visible_tenants),
        )
        with self.new_session() as s:
            profile = s.query(Profile).filter(filter_).first()
            return self._profile_schema.dump(profile).data

    def list_(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Profile).filter(filter_)
            # add pagination here
            return [self._profile_schema.dump(row).data for row in query.all()]

    def _list_filter(self, visible_tenants, uuid=None, name=None, **list_params):
        filter_ = text('true')
        if visible_tenants is not None:
            if not visible_tenants:
                return text('false')
            filter_ = and_(filter_, Profile.tenant_uuid.in_(visible_tenants))
        if uuid is not None:
            filter_ = and_(filter_, Profile.uuid == uuid)
        if name is not None:
            filter_ = and_(filter_, Profile.name == name)
        return filter_

    @staticmethod
    def _create_profile(session, body):
        display = body.get('display') or {}
        display_uuid = display.get('uuid')
        profile = Profile(
            tenant_uuid=body['tenant_uuid'],
            name=body['name'],
            display_uuid=display_uuid,
        )
        session.add(profile)
        try:
            session.flush()
        except exc.IntegrityError as e:
            if extract_constraint_name(e) == 'dird_profile_display_uuid_fkey':
                raise exception.NoSuchDisplay(display_uuid)
            raise
        return profile.uuid

    @staticmethod
    def _create_profile_service(session, profile_uuid, service_uuid, config):
        config = dict(config)
        config.pop('sources', None)
        profile_service = ProfileService(
            profile_uuid=profile_uuid,
            service_uuid=service_uuid,
            config=config,
        )
        session.add(profile_service)
        session.flush()
        return profile_service.uuid

    @staticmethod
    def _create_profile_service_source(session, profile_service_uuid, source_uuid):
        if source_uuid is None:
            raise exception.NoSuchSource(source_uuid)

        profile_service_source = ProfileServiceSource(
            profile_service_uuid=profile_service_uuid,
            source_uuid=source_uuid,
        )
        session.add(profile_service_source)
        try:
            session.flush()
        except exc.IntegrityError as e:
            if extract_constraint_name(e) == 'dird_profile_service_source_source_uuid_fkey':
                raise exception.NoSuchSource(source_uuid)
            raise

    @staticmethod
    def _create_service(session, name):
        service = session.query(Service).filter(Service.name == name).scalar()
        if not service:
            service = Service(name=name)
            session.add(service)
            session.flush()

        return service.uuid

    @staticmethod
    def _display_to_dict(display):
        result = display.__dict__
        result['columns'] = display.columns
        return result
