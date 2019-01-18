# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import (
    and_,
)
from sqlalchemy.orm.session import make_transient

from wazo_dird.exception import (
    DuplicatedFavoriteException,
    NoSuchFavorite,
)
from .. import (
    Favorite,
    Source,
)
from .base import BaseDAO


class FavoriteCRUD(BaseDAO):

    def create(self, xivo_user_uuid, source_name, contact_id):
        with self.new_session() as s:
            user = self._get_dird_user(s, xivo_user_uuid)
            source = self._get_source(s, source_name)
            favorite = Favorite(source_uuid=source.uuid,
                                contact_id=contact_id,
                                user_uuid=user.xivo_user_uuid)
            s.add(favorite)
            self.flush_or_raise(s, DuplicatedFavoriteException)
            make_transient(favorite)
            return favorite

    def delete(self, xivo_user_uuid, source_name, contact_id):
        with self.new_session() as s:
            source_uuid = s.query(Source.uuid).filter(Source.name == source_name).scalar()
            filter_ = and_(Favorite.contact_id == contact_id,
                           Favorite.user_uuid == xivo_user_uuid,
                           Favorite.source_uuid == source_uuid)
            deleted = s.query(Favorite).filter(filter_).delete(synchronize_session=False)

            s.commit()

        if not deleted:
            raise NoSuchFavorite((source_name, contact_id))

    def get(self, xivo_user_uuid):
        with self.new_session() as s:
            favorites = s.query(
                Favorite.contact_id,
                Source.name
            ).join(Source).filter(Favorite.user_uuid == xivo_user_uuid)
            return [(f.name, f.contact_id) for f in favorites.all()]

    def _get_source(self, session, source_name):
        source = session.query(Source).filter(Source.name == source_name).first()
        if not source:
            source = Source(name=source_name)
            session.add(source)
            session.flush()

        return source
