# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wazo_dird import exception

if TYPE_CHECKING:
    from wazo_confd_client import Client as ConfdClient


class ContactLister:
    def __init__(self, client: ConfdClient) -> None:
        self._client = client

    def list(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            result: dict[str, Any] = self._client.users.list(
                *args, view='directory', **kwargs
            )
            return result
        except Exception as e:
            raise exception.WazoConfdError(self._client, e)
