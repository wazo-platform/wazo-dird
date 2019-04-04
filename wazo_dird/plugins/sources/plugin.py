# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from . import http


class SourcesViewPlugin(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']
        source_service = dependencies['services']['source']

        api.add_resource(
            http.Sources,
            '/sources',
            resource_class_args=(source_service,),
        )
