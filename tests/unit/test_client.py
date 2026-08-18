#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for tvdinner.jellyfin client and modules."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from ansible.module_utils.six.moves.urllib.error import HTTPError

from ansible_collections.tvdinner.core.plugins.module_utils.client import TVDinnerError
from ansible_collections.tvdinner.jellyfin.plugins.module_utils.client import (
    JellyfinClient,
)
from ansible_collections.tvdinner.jellyfin.plugins.module_utils.common import (
    get_client_from_module,
    jellyfin_argument_spec,
)


def _resp(status, body=None):
    resp = MagicMock()
    resp.status = status
    resp.getcode.return_value = status
    if body is None:
        resp.read.return_value = b''
    elif isinstance(body, bytes):
        resp.read.return_value = body
    else:
        resp.read.return_value = json.dumps(body).encode()
    return resp


def _http_error(code, message='error'):
    return HTTPError('url', code, message, {}, io.BytesIO(json.dumps({'message': message}).encode()))


KEYS = {
    'Items': [
        {'AppName': 'homepage', 'AccessToken': 'old', 'DateCreated': '2025-01-01T00:00:00Z'},
        {'AppName': 'homepage', 'AccessToken': 'new', 'DateCreated': '2026-01-01T00:00:00Z'},
        {'AppName': 'other', 'AccessToken': 'zzz', 'DateCreated': '2026-02-01T00:00:00Z'},
    ],
    'TotalRecordCount': 3,
}


class TestClientWiring(unittest.TestCase):

    def test_get_client_from_module_builds_client(self):
        module = MagicMock()
        module.params = dict(jellyfin_url='https://j/', jellyfin_api_key='k',
                             validate_certs=False, timeout=7)
        client = get_client_from_module(module)
        self.assertIsInstance(client, JellyfinClient)
        self.assertEqual(client.base_url, 'https://j')
        self.assertEqual(client._auth_headers(), {'X-Emby-Token': 'k'})
        self.assertFalse(client.validate_certs)
        self.assertEqual(client.timeout, 7)

    def test_argument_spec_keys(self):
        spec = jellyfin_argument_spec()
        self.assertTrue(spec['jellyfin_url']['required'])
        self.assertTrue(spec['jellyfin_api_key']['no_log'])


class TestJellyfinClient(unittest.TestCase):

    def _client(self):
        client = JellyfinClient('https://jellyfin.example.com/', 'key-123')
        client._request = MagicMock()
        return client

    def test_auth_header(self):
        self.assertEqual(self._client()._auth_headers(), {'X-Emby-Token': 'key-123'})

    def test_system_info(self):
        client = self._client()
        client._request.open.return_value = _resp(200, {'Version': '10.10.0'})
        self.assertEqual(client.get_system_info(), {'Version': '10.10.0'})
        self.assertEqual(client._request.open.call_args[1]['url'],
                         'https://jellyfin.example.com/System/Info')

    # --- API keys ---

    def test_list_keys_unwraps_items(self):
        client = self._client()
        client._request.open.return_value = _resp(200, KEYS)
        keys = client.list_keys()
        self.assertEqual(len(keys), 3)
        kwargs = client._request.open.call_args[1]
        self.assertEqual(kwargs['method'], 'GET')
        self.assertEqual(kwargs['url'], 'https://jellyfin.example.com/Auth/Keys')

    def test_list_keys_empty_body(self):
        client = self._client()
        client._request.open.return_value = _resp(200, {'Items': [], 'TotalRecordCount': 0})
        self.assertEqual(client.list_keys(), [])

    def test_create_key_posts_then_relists_newest(self):
        client = self._client()
        client._request.open.side_effect = [_resp(204), _resp(200, KEYS)]
        created = client.create_key('homepage')
        post = client._request.open.call_args_list[0][1]
        self.assertEqual(post['method'], 'POST')
        self.assertEqual(post['url'], 'https://jellyfin.example.com/Auth/Keys?app=homepage')
        self.assertEqual(created['AccessToken'], 'new')

    def test_create_key_missing_after_post_raises(self):
        client = self._client()
        client._request.open.side_effect = [_resp(204), _resp(200, {'Items': []})]
        with self.assertRaises(TVDinnerError):
            client.create_key('homepage')

    def test_delete_key_url(self):
        client = self._client()
        client._request.open.return_value = _resp(204)
        client.delete_key('tok')
        kwargs = client._request.open.call_args[1]
        self.assertEqual(kwargs['method'], 'DELETE')
        self.assertEqual(kwargs['url'], 'https://jellyfin.example.com/Auth/Keys/tok')

    # --- items ---

    def test_query_items_paginates(self):
        client = self._client()
        pages = [
            {'Items': [{'Id': str(i)} for i in range(500)],
             'TotalRecordCount': 700},
            {'Items': [{'Id': str(i)} for i in range(500, 700)],
             'TotalRecordCount': 700},
        ]

        def fake_open(**kwargs):
            page = pages[0] if 'StartIndex=0' in kwargs['url'] else pages[1]
            return _resp(200, page)

        client._request.open.side_effect = fake_open
        items = client.query_items(include_item_types=['Movie', 'Episode'],
                                   fields=['MediaSources', 'Path'])
        self.assertEqual(len(items), 700)
        first_url = client._request.open.call_args_list[0][1]['url']
        self.assertIn('IncludeItemTypes=Movie%2CEpisode', first_url)
        self.assertIn('Fields=MediaSources%2CPath', first_url)
        self.assertIn('Limit=500', first_url)

    def test_query_items_no_pagination(self):
        client = self._client()
        client._request.open.return_value = _resp(200, {'Items': [{'Id': '1'}], 'TotalRecordCount': 1})
        self.assertEqual(client.query_items(paginate=False), [{'Id': '1'}])

    def test_delete_item_true_on_success(self):
        client = self._client()
        client._request.open.return_value = _resp(204)
        self.assertTrue(client.delete_item('abc'))
        kwargs = client._request.open.call_args[1]
        self.assertEqual(kwargs['method'], 'DELETE')
        self.assertEqual(kwargs['url'], 'https://jellyfin.example.com/Items/abc')

    def test_delete_item_false_when_already_gone(self):
        client = self._client()
        client._request.open.side_effect = _http_error(404, 'gone')
        self.assertFalse(client.delete_item('abc'))

    def test_delete_item_raises_on_500(self):
        client = self._client()
        client._request.open.side_effect = _http_error(500, 'boom')
        with self.assertRaises(TVDinnerError) as ctx:
            client.delete_item('abc')
        self.assertEqual(ctx.exception.status_code, 500)

    # --- libraries ---

    def test_create_library_params(self):
        client = self._client()
        client._request.open.return_value = _resp(204)
        client.create_library('Movies', 'movies', ['/media/movies', '/media/more'])
        kwargs = client._request.open.call_args[1]
        self.assertEqual(kwargs['method'], 'POST')
        self.assertIn('/Library/VirtualFolders?', kwargs['url'])
        self.assertIn('name=Movies', kwargs['url'])
        self.assertIn('collectionType=movies', kwargs['url'])
        self.assertIn('refreshLibrary=true', kwargs['url'])
        self.assertIn('paths=%2Fmedia%2Fmovies&paths=%2Fmedia%2Fmore', kwargs['url'])

    def test_delete_library_params(self):
        client = self._client()
        client._request.open.return_value = _resp(204)
        client.delete_library('Movies', refresh_library=False)
        kwargs = client._request.open.call_args[1]
        self.assertEqual(kwargs['method'], 'DELETE')
        self.assertIn('name=Movies', kwargs['url'])
        self.assertIn('refreshLibrary=false', kwargs['url'])


class _ModuleHarness(unittest.TestCase):
    """Runs a module's run_module() with AnsibleModule and the client mocked."""

    mod = None

    def _run(self, params, client, check_mode=False):
        module = MagicMock()
        module.params = dict({'jellyfin_url': 'u', 'jellyfin_api_key': 'k',
                              'validate_certs': True, 'timeout': 30}, **params)
        module.check_mode = check_mode
        results = {}

        def _exit(**kw):
            results['exit'] = kw
            raise SystemExit(0)

        def _fail(**kw):
            results['fail'] = kw
            raise SystemExit(1)

        module.exit_json.side_effect = _exit
        module.fail_json.side_effect = _fail
        with patch.object(self.mod, 'AnsibleModule', return_value=module), \
                patch.object(self.mod, 'get_client_from_module', return_value=client):
            try:
                self.mod.run_module()
            except SystemExit:
                pass
        return results


from ansible_collections.tvdinner.jellyfin.plugins.modules import (  # noqa: E402
    api_key, api_key_info, item, library)


class TestApiKeyModule(_ModuleHarness):
    mod = api_key

    def test_create_when_absent_returns_token(self):
        client = MagicMock()
        client.list_keys.return_value = []
        client.create_key.return_value = {'AppName': 'homepage', 'AccessToken': 'tok'}
        res = self._run({'name': 'homepage', 'state': 'present'}, client)
        self.assertTrue(res['exit']['changed'])
        self.assertEqual(res['exit']['api_key'], {'name': 'homepage', 'token': 'tok'})
        client.create_key.assert_called_once_with('homepage')

    def test_create_check_mode(self):
        client = MagicMock()
        client.list_keys.return_value = []
        res = self._run({'name': 'homepage', 'state': 'present'}, client, check_mode=True)
        self.assertTrue(res['exit']['changed'])
        client.create_key.assert_not_called()

    def test_idempotent_when_present_returns_newest_token(self):
        client = MagicMock()
        client.list_keys.return_value = KEYS['Items']
        res = self._run({'name': 'homepage', 'state': 'present'}, client)
        self.assertFalse(res['exit']['changed'])
        self.assertEqual(res['exit']['api_key']['token'], 'new')
        client.create_key.assert_not_called()

    def test_delete_removes_every_matching_key(self):
        client = MagicMock()
        client.list_keys.return_value = KEYS['Items']
        res = self._run({'name': 'homepage', 'state': 'absent'}, client)
        self.assertTrue(res['exit']['changed'])
        self.assertEqual(sorted(c[0][0] for c in client.delete_key.call_args_list), ['new', 'old'])

    def test_delete_absent_is_noop(self):
        client = MagicMock()
        client.list_keys.return_value = []
        res = self._run({'name': 'homepage', 'state': 'absent'}, client)
        self.assertFalse(res['exit']['changed'])
        client.delete_key.assert_not_called()

    def test_api_error_fails_cleanly(self):
        client = MagicMock()
        client.list_keys.side_effect = TVDinnerError('API error (401): nope', status_code=401)
        res = self._run({'name': 'homepage', 'state': 'present'}, client)
        self.assertIn('401', res['fail']['msg'])


class TestApiKeyInfoModule(_ModuleHarness):
    mod = api_key_info

    def test_filters_by_app_name(self):
        client = MagicMock()
        client.get_system_info.return_value = {'Version': '10'}
        client.list_keys.return_value = KEYS['Items']
        res = self._run({'name': 'homepage'}, client)
        self.assertEqual(len(res['exit']['api_keys']), 2)
        self.assertEqual(res['exit']['system_info'], {'Version': '10'})
        self.assertFalse(res['exit']['changed'])

    def test_no_filter_returns_all(self):
        client = MagicMock()
        client.get_system_info.return_value = {}
        client.list_keys.return_value = KEYS['Items']
        res = self._run({'name': None}, client)
        self.assertEqual(len(res['exit']['api_keys']), 3)


class TestItemModule(_ModuleHarness):
    mod = item

    def test_deletes_each_id_and_tolerates_missing(self):
        client = MagicMock()
        client.delete_item.side_effect = [True, False]
        res = self._run({'ids': ['a', 'b'], 'state': 'absent', 'fail_on_error': True}, client)
        self.assertTrue(res['exit']['changed'])
        self.assertEqual(res['exit']['deleted'], ['a'])
        self.assertEqual(res['exit']['missing'], ['b'])
        self.assertEqual(res['exit']['failed_items'], [])

    def test_only_missing_is_unchanged(self):
        client = MagicMock()
        client.delete_item.return_value = False
        res = self._run({'ids': ['a'], 'state': 'absent', 'fail_on_error': True}, client)
        self.assertFalse(res['exit']['changed'])

    def test_500_fails_by_default_but_reports_others(self):
        client = MagicMock()
        client.delete_item.side_effect = [True, TVDinnerError('API error (500): boom', status_code=500)]
        res = self._run({'ids': ['a', 'b'], 'state': 'absent', 'fail_on_error': True}, client)
        self.assertIn('fail', res)
        self.assertEqual(res['fail']['deleted'], ['a'])
        self.assertEqual(res['fail']['failed_items'][0]['id'], 'b')
        self.assertEqual(res['fail']['failed_items'][0]['status_code'], 500)

    def test_500_tolerated_when_fail_on_error_false(self):
        client = MagicMock()
        client.delete_item.side_effect = [True, TVDinnerError('API error (500): boom', status_code=500)]
        res = self._run({'ids': ['a', 'b'], 'state': 'absent', 'fail_on_error': False}, client)
        self.assertTrue(res['exit']['changed'])
        self.assertEqual([f['id'] for f in res['exit']['failed_items']], ['b'])

    def test_check_mode_deletes_nothing(self):
        client = MagicMock()
        res = self._run({'ids': ['a'], 'state': 'absent', 'fail_on_error': True}, client, check_mode=True)
        self.assertTrue(res['exit']['changed'])
        client.delete_item.assert_not_called()


class TestLibraryModule(_ModuleHarness):
    mod = library

    def _params(self, **over):
        p = {'name': 'Movies', 'collection_type': 'movies', 'paths': ['/media/movies'],
             'refresh_library': True, 'state': 'present'}
        p.update(over)
        return p

    def test_creates_when_missing(self):
        client = MagicMock()
        client.list_libraries.return_value = []
        res = self._run(self._params(), client)
        self.assertTrue(res['exit']['changed'])
        client.create_library.assert_called_once()

    def test_present_is_idempotent(self):
        client = MagicMock()
        client.list_libraries.return_value = [{'Name': 'Movies', 'Locations': ['/media/movies']}]
        res = self._run(self._params(), client)
        self.assertFalse(res['exit']['changed'])
        client.create_library.assert_not_called()

    def test_absent_deletes(self):
        client = MagicMock()
        client.list_libraries.return_value = [{'Name': 'Movies'}]
        res = self._run(self._params(state='absent'), client)
        self.assertTrue(res['exit']['changed'])
        client.delete_library.assert_called_once()


if __name__ == '__main__':
    unittest.main()
