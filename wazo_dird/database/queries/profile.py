# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import (
    and_,
    exc,
    func,
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

    def count(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(func.count(Profile.uuid)).filter(filter_)
            return query.scalar()

    def create(self, body):
        tenant_uuid = body['tenant_uuid']
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            body['uuid'] = self._create_profile(s, body)
            self._associate_all_services(s, tenant_uuid, body['uuid'], body['services'])
        return body

    def delete(self, visible_tenants, profile_uuid):
        filter_ = self._build_filter(visible_tenants, profile_uuid)
        with self.new_session() as s:
            nb_deleted = s.query(Profile).filter(filter_).delete(synchronize_session=False)

        if not nb_deleted:
            raise exception.NoSuchProfileAPIException(profile_uuid)

    def edit(self, visible_tenants, profile_uuid, body):
        filter_ = self._build_filter(visible_tenants, profile_uuid)
        with self.new_session() as s:
            self._dissociate_all_services(s, profile_uuid)

            profile = s.query(Profile).filter(filter_).first()
            if not profile:
                raise exception.NoSuchProfileAPIException(profile_uuid)

            profile.name = body['name']
            profile.display_uuid = body['display']['uuid']
            profile.display_tenant_uuid = profile.tenant_uuid
            try:
                s.flush()
            except exc.IntegrityError as e:
                if extract_constraint_name(e) == 'dird_profile_display_uuid_tenant_fkey':
                    raise exception.NoSuchDisplay(body['display']['uuid'])
                raise

            self._associate_all_services(s, profile.tenant_uuid, profile_uuid, body['services'])

    def get(self, visible_tenants, profile_uuid):
        filter_ = self._build_filter(visible_tenants, profile_uuid)
        with self.new_session() as s:
            profile = s.query(Profile).filter(filter_).first()
            if not profile:
                raise exception.NoSuchProfileAPIException(profile_uuid)

            return self._profile_schema.dump(profile).data

    def list_(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Profile).filter(filter_)
            query = self._paginate(query, **list_params)
            return self._profile_schema.dump(query.all(), many=True).data

    def _build_filter(self, visible_tenants, profile_uuid):
        filter_ = Profile.uuid == profile_uuid
        if visible_tenants is not None:
            if not visible_tenants:
                raise exception.NoSuchProfileAPIException(profile_uuid)
            filter_ = and_(filter_, Profile.tenant_uuid.in_(visible_tenants))
        return filter_

    def _associate_all_services(self, session, tenant_uuid, profile_uuid, services):
        for service_name, config in services.items():
            service_uuid = self._create_service(session, service_name)
            profile_service_uuid = self._create_profile_service(
                session, tenant_uuid, profile_uuid, service_uuid, config,
            )
            for source in config['sources']:
                source_uuid = str(source.get('uuid'))
                self._create_profile_service_source(
                    session, tenant_uuid, profile_service_uuid, source_uuid,
                )

    def _dissociate_all_services(self, session, profile_uuid):
        session.query(ProfileService).filter(
            ProfileService.profile_uuid == profile_uuid,
        ).delete(synchronize_session=False)

    def _list_filter(self, visible_tenants, uuid=None, name=None, search=None, **list_params):
        filter_ = text('true')
        if visible_tenants is not None:
            if not visible_tenants:
                return text('false')
            filter_ = and_(filter_, Profile.tenant_uuid.in_(visible_tenants))
        if uuid is not None:
            filter_ = and_(filter_, Profile.uuid == uuid)
        if name is not None:
            filter_ = and_(filter_, Profile.name == name)
        if search is not None:
            pattern = '%{}%'.format(search)
            filter_ = and_(filter_, Profile.name.ilike(pattern))
        return filter_

    @staticmethod
    def _paginate(query, limit=None, offset=None, order=None, direction=None, **ignored):
        if order and direction:
            field = None
            if order == 'name':
                field = Profile.name

            if field:
                order_clause = field.asc() if direction == 'asc' else field.desc()
                query = query.order_by(order_clause)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        return query

    @staticmethod
    def _create_profile(session, body):
        display = body.get('display') or {}
        display_uuid = display.get('uuid')
        profile = Profile(
            tenant_uuid=body['tenant_uuid'],
            name=body['name'],
            display_uuid=display_uuid,
            display_tenant_uuid=body['tenant_uuid'],
        )
        session.add(profile)
        try:
            session.flush()
        except exc.IntegrityError as e:
            if extract_constraint_name(e) == 'dird_profile_display_uuid_tenant_fkey':
                raise exception.NoSuchDisplay(display_uuid)
            raise
        return profile.uuid

    @staticmethod
    def _create_profile_service(session, tenant_uuid, profile_uuid, service_uuid, config):
        config = dict(config)
        config.pop('sources', None)
        profile_service = ProfileService(
            profile_uuid=profile_uuid,
            profile_tenant_uuid=tenant_uuid,
            service_uuid=service_uuid,
            config=config,
        )
        session.add(profile_service)
        session.flush()
        return profile_service.uuid

    @staticmethod
    def _create_profile_service_source(session, tenant_uuid, profile_service_uuid, source_uuid):
        if source_uuid is None:
            raise exception.NoSuchSource(source_uuid)

        profile_service_source = ProfileServiceSource(
            profile_service_uuid=profile_service_uuid,
            profile_tenant_uuid=tenant_uuid,
            source_uuid=source_uuid,
            source_tenant_uuid=tenant_uuid,
        )
        session.add(profile_service_source)
        try:
            session.flush()
        except exc.IntegrityError as e:
            if extract_constraint_name(e) == 'dird_profile_service_source_source_uuid_tenant_fkey':
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
