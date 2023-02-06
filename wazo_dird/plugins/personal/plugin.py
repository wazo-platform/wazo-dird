# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re

from wazo_dird import BaseViewPlugin

from .http import PersonalAll, PersonalImport, PersonalOne

logger = logging.getLogger(__name__)

CHARSET_REGEX = re.compile('.*; *charset *= *(.*)')


class PersonalViewPlugin(BaseViewPlugin):
    personal_all_url = '/personal'
    personal_one_url = '/personal/<contact_id>'
    personal_import_url = '/personal/import'

    def load(self, dependencies):
        api = dependencies['api']
        personal_service = dependencies['services'].get('personal')
        if personal_service:
            PersonalAll.configure(personal_service)
            PersonalOne.configure(personal_service)
            PersonalImport.configure(personal_service)
            api.add_resource(PersonalAll, self.personal_all_url)
            api.add_resource(PersonalOne, self.personal_one_url)
            api.add_resource(PersonalImport, self.personal_import_url)
