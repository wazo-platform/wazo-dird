# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, cast

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies

from .http import PersonalAll, PersonalImport, PersonalOne

if TYPE_CHECKING:
    from wazo_dird.plugins.personal_service.plugin import _PersonalService

logger = logging.getLogger(__name__)

CHARSET_REGEX = re.compile('.*; *charset *= *(.*)')


class PersonalViewPlugin(BaseViewPlugin):
    personal_all_url = '/personal'
    personal_one_url = '/personal/<contact_id>'
    personal_import_url = '/personal/import'

    def load(self, dependencies: ViewDependencies) -> None:
        api = dependencies['api']
        personal_service = cast(
            '_PersonalService | None', dependencies['services'].get('personal')
        )
        if personal_service:
            PersonalAll.configure(personal_service)
            PersonalOne.configure(personal_service)
            PersonalImport.configure(personal_service)
            api.add_resource(PersonalAll, self.personal_all_url)
            api.add_resource(PersonalOne, self.personal_one_url)
            api.add_resource(PersonalImport, self.personal_import_url)
