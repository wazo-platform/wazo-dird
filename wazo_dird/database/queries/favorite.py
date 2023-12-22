# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import and_
from sqlalchemy.orm.session import make_transient

from wazo_dird.exception import DuplicatedFavoriteException, NoSuchFavorite

from .. import Favorite, Source
from .base import BaseDAO


class FavoriteCRUD(BaseDAO):
    def create(self, user_uuid, backend, source_name, contact_id):
        with self.new_session() as s:
            user = self._get_dird_user(s, user_uuid)
            source = self._get_source(s, backend, source_name)
            favorite = Favorite(
                source_uuid=source.uuid, contact_id=contact_id, user_uuid=user.user_uuid
            )
            s.add(favorite)
            self.flush_or_raise(s, DuplicatedFavoriteException)
            make_transient(favorite)
            return favorite

    def delete(self, user_uuid, source_name, contact_id):
        with self.new_session() as s:
            matching_source_uuids = (
                s.query(Source.uuid).filter(Source.name == source_name).all()
            )
            if not matching_source_uuids:
                raise NoSuchFavorite((source_name, contact_id))

            filter_ = and_(
                Favorite.contact_id == contact_id,
                Favorite.user_uuid == user_uuid,
                Favorite.source_uuid.in_(matching_source_uuids),
            )
            deleted = (
                s.query(Favorite).filter(filter_).delete(synchronize_session=False)
            )

            s.commit()

        if not deleted:
            raise NoSuchFavorite((source_name, contact_id))

    def get(self, user_uuid):
        with self.new_session() as s:
            favorites = (
                s.query(Favorite.contact_id, Source.name)
                .join(Source)
                .filter(Favorite.user_uuid == user_uuid)
            )
            return [(f.name, f.contact_id) for f in favorites.all()]

    def _get_source(self, session, backend, source_name):
        source = (
            session.query(Source)
            .filter(and_(Source.name == source_name, Source.backend == backend))
            .first()
        )

        return source
