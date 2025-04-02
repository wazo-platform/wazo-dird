# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import patch
from unittest.mock import sentinel as s

from hamcrest import assert_that, calling, raises

from ..user_sync import main


class TestWazoDirdSyncUsers(TestCase):
    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_injects_argv_into_config_loading(self, load_config, *_):
        main(s.argv)

        load_config.assert_called_once_with(s.argv)

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_setup_logging(
        self, load_config, xivo_logging, _, __, ___, ____, init_db
    ):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': s.user,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        main(s.argv)

        xivo_logging.setup_logging.assert_called_once_with(
            s.log_filename, debug=s.debug, log_level=s.log_level
        )
        init_db.assert_called_once_with(s.db_uri, pool_size=s.max_threads)

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_when_config_user_then_change_user(
        self, load_config, _, change_user, *__
    ):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': s.user,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        main(s.argv)

        change_user.assert_called_once_with(s.user)

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_when_no_config_user_then_dont_change_user(
        self, load_config, _, change_user, *__
    ):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': None,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        main(s.argv)

        load_config.assert_called_once()
        change_user.assert_not_called()

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_calls_sync_users(
        self, load_config, _, __, sync_users, stdin_readable, stdin_read, *___
    ):
        stdin_readable.return_value = True
        json_data = (
            '['
            '{"uuid":"valid-uuid-1","tenant_uuid":"valid-uuid-2"},'
            '{"uuid":"valid-uuid-3","tenant_uuid":"valid-uuid-4"}'
        )
        ']'
        stdin_read.return_value = json_data
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': None,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        main(s.argv)

        stdin_read.assert_called_once()
        sync_users.assert_called_once_with(json_data)

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_users')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_calls_sync_users_missing_value(
        self, load_config, _, __, sync_users, stdin_readable, ___, *____
    ):
        stdin_readable.return_value = False
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': None,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        main(s.argv)

        sync_users.assert_not_called()

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.sync_user')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_calls_sync_users_invalid_json(
        self, load_config, _, __, sync_user, stdin_readable, stdin_read, *____
    ):
        stdin_readable.return_value = True
        json_data = '{"uuid":"valid-uuid-1","tenant_uuid":"valid-uuid-2"}'
        stdin_read.return_value = json_data
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': None,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        assert_that(calling(main).with_args(s.argv), raises(ValueError))
        sync_user.assert_not_called()

        json_data = ''
        stdin_read.return_value = json_data

        assert_that(calling(main).with_args(s.argv), raises(ValueError))
        sync_user.assert_not_called()

    @patch('wazo_dird.user_sync.init_db')
    @patch('wazo_dird.user_sync.Session')
    @patch('wazo_dird.user_sync.sys.stdin.read')
    @patch('wazo_dird.user_sync.sys.stdin.readable')
    @patch('wazo_dird.user_sync.change_user')
    @patch('wazo_dird.user_sync.xivo_logging')
    @patch('wazo_dird.user_sync.load_config')
    def test_main_calls_sync_users_valid_json_missing_values(
        self, load_config, _, __, stdin_readable, stdin_read, session, *____
    ):
        stdin_readable.return_value = True
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'user': None,
            'db_uri': s.db_uri,
            'rest_api': {'max_threads': s.max_threads},
        }

        # Missing tenant_uuid
        json_data = '[{"uuid":"valid-uuid-1"}]'
        stdin_read.return_value = json_data

        main(s.argv)
        # No Session object created means that the condition to add/modify a user failed
        session.assert_not_called()

        # Missing uuid
        json_data = '[{"tenant_uuid":"valid-uuid-1"}]'
        stdin_read.return_value = json_data

        main(s.argv)
        # No Session object created means that the condition to add/modify a user failed
        session.assert_not_called()

        # No missing value
        json_data = '[{"uuid":"valid-uuid-1","tenant_uuid":"valid-uuid-2"}]'
        stdin_read.return_value = json_data
        main(s.argv)

        session.assert_called()
