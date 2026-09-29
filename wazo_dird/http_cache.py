# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from flask import Response, current_app, request

logger = logging.getLogger(__name__)

CACHE_CONTROL_CONFIG_KEY = 'cache_control_max_age'


def sanitized_max_ages(raw: dict[str, object]) -> dict[str, int]:
    max_ages: dict[str, int] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            logger.warning(
                'ignoring rest_api.cache_control.%s: %r is not a positive number '
                'of seconds',
                key,
                value,
            )
            continue
        max_ages[key] = value
    return max_ages


def _cache_control_key() -> str | None:
    rule = request.url_rule
    if rule is None:
        return None
    view = current_app.view_functions.get(rule.endpoint)
    return getattr(getattr(view, 'view_class', None), 'cache_control_key', None)


def add_cache_control(response: Response) -> Response:
    """Mark a GET response as fresh for the lifetime configured for its resource.

    A resource opts in by declaring `cache_control_key`. Everything else keeps
    the current behaviour: no freshness metadata, so the response is stale on
    arrival and the client revalidates.
    """
    if request.method != 'GET' or response.status_code != 200:
        return response

    key = _cache_control_key()
    if key is None:
        return response

    max_age = current_app.config.get(CACHE_CONTROL_CONFIG_KEY, {}).get(key)
    if not max_age:
        return response

    # `private`: every dird response is authenticated. No `Vary` on the token:
    # clients honour it and tokens rotate, which would mean a permanent miss.
    response.cache_control.private = True
    response.cache_control.max_age = max_age
    return response
