#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for tvdinner.jellyfin client and modules."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import unittest

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from ansible_collections.tvdinner.jellyfin.plugins.module_utils.client import (
    JellyfinClient,
)


class TestJellyfinClient(unittest.TestCase):

    def _client(self):
        client = JellyfinClient('https://jellyfin.example.com/', 'key-123')
        client._request = MagicMock()
        return client

    def test_auth_header(self):
        self.assertEqual(self._client()._auth_headers(), {'X-Emby-Token': 'key-123'})

    def test_system_info(self):
        client = self._client()
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"Version": "10.10.0"}'
        client._request.open.return_value = resp
        self.assertEqual(client.get_system_info(), {'Version': '10.10.0'})

    def test_query_items_paginates(self):
        client = self._client()
        pages = [
            {'Items': [{'Id': str(i)} for i in range(500)],
             'TotalRecordCount': 700},
            {'Items': [{'Id': str(i)} for i in range(500, 700)],
             'TotalRecordCount': 700},
        ]

        def fake_open(**kwargs):
            resp = MagicMock()
            resp.status = 200
            import json
            page = pages[0] if 'StartIndex=0' in kwargs['url'] else pages[1]
            resp.read.return_value = json.dumps(page).encode()
            return resp

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
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"Items": [{"Id": "1"}], "TotalRecordCount": 1}'
        client._request.open.return_value = resp
        items = client.query_items(paginate=False)
        self.assertEqual(items, [{'Id': '1'}])

    def test_delete_items_joins_ids(self):
        client = self._client()
        resp = MagicMock()
        resp.status = 204
        resp.read.return_value = b''
        client._request.open.return_value = resp
        client.delete_items(['a', 'b'])
        url = client._request.open.call_args[1]['url']
        self.assertIn('Ids=a%2Cb', url)

    def test_create_library_params(self):
        client = self._client()
        resp = MagicMock()
        resp.status = 204
        resp.read.return_value = b''
        client._request.open.return_value = resp
        client.create_library('Movies', 'movies', ['/media/movies'])
        kwargs = client._request.open.call_args[1]
        self.assertIn('name=Movies', kwargs['url'])
        self.assertIn('collectionType=movies', kwargs['url'])


class TestApiKeyModule(unittest.TestCase):

    def _run(self, params, client):
        from ansible_collections.tvdinner.jellyfin.plugins.modules import api_key
        module = MagicMock()
        module.params = dict(params, validate_certs=True, timeout=30)
        module.check_mode = False
        module.exit_json.side_effect = lambda **kw: kw.update()
        with patch.object(api_key, 'AnsibleModule', return_value=module), \
                patch.object(api_key, 'get_client_from_module', return_value=client):
            api_key.run_module()
        return module

    def test_create_when_absent(self):
        client = MagicMock()
        client.list_keys.return_value = []
        client.create_key.return_value = {'AccessToken': 'tok'}
        m = self._run({'jellyfin_url': 'u', 'jellyfin_api_key': 'k',
                       'name': 'homepage', 'state': 'present'}, client)
        self.assertTrue(m.exit_json.call_args[1]['changed'])
        client.create_key.assert_called_once_with('homepage')

    def test_idempotent_when_present(self):
        client = MagicMock()
        client.list_keys.return_value = [{'Name': 'homepage', 'AccessToken': 'x'}]
        m = self._run({'jellyfin_url': 'u', 'jellyfin_api_key': 'k',
                       'name': 'homepage', 'state': 'present'}, client)
        self.assertFalse(m.exit_json.call_args[1]['changed'])
        client.create_key.assert_not_called()

    def test_delete(self):
        client = MagicMock()
        client.list_keys.return_value = [{'Name': 'homepage', 'AccessToken': 'x'}]
        m = self._run({'jellyfin_url': 'u', 'jellyfin_api_key': 'k',
                       'name': 'homepage', 'state': 'absent'}, client)
        self.assertTrue(m.exit_json.call_args[1]['changed'])
        client.delete_key.assert_called_once_with('x')


if __name__ == '__main__':
    unittest.main()
