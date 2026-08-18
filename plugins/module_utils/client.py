# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.tvdinner.core.plugins.module_utils.client import (
    AUTH_HEADER,
    RESTClient,
    TVDinnerError,
    TVDinnerNotFoundError,
)

PAGE_SIZE = 500


class JellyfinClient(RESTClient):
    """Jellyfin API client built on the shared tvdinner.core RESTClient.

    Auth uses the X-Emby-Token header, which Jellyfin accepts for API-key
    authentication on every endpoint these methods touch.
    """

    def __init__(self, url, token, **kwargs):
        # `token` (not api_key): client_from_module passes token= by keyword.
        super(JellyfinClient, self).__init__(
            url, token, auth_style=AUTH_HEADER,
            auth_header_name='X-Emby-Token', **kwargs)

    # ========== System Methods ==========

    def get_system_info(self):
        """Return authenticated /System/Info — also validates the API key."""
        return self.request('GET', '/System/Info')

    # ========== API Key Methods ==========

    def list_keys(self):
        """List API keys.

        GET /Auth/Keys returns a QueryResult: C({"Items": [...],
        "TotalRecordCount": n}). Each item is an AuthenticationInfo whose label
        is C(AppName) and whose token is C(AccessToken).
        """
        result = self.request('GET', '/Auth/Keys')
        if isinstance(result, dict):
            return result.get('Items', []) or []
        return result or []

    def create_key(self, name):
        """Create an API key labelled C(name) and return its AuthenticationInfo.

        POST /Auth/Keys answers 204 with no body, so the new key is found by
        re-listing and taking the newest entry with that AppName.
        """
        self.request('POST', '/Auth/Keys', params={'app': name})
        matches = [k for k in self.list_keys() if k.get('AppName') == name]
        if not matches:
            raise TVDinnerError(
                'API key {0!r} was accepted but does not appear in /Auth/Keys'.format(name))
        return sorted(matches, key=lambda k: k.get('DateCreated') or '')[-1]

    def delete_key(self, access_token):
        """Delete an API key by its token value."""
        self.request('DELETE', '/Auth/Keys/{0}'.format(access_token))

    # ========== Item Methods ==========

    def query_items(self, include_item_types=None, fields=None,
                    recursive=True, filters=None, paginate=True):
        """Query items, transparently paginating.

        Args:
            include_item_types: list of item types (Movie, Episode, ...).
            fields: list of extra fields to request (MediaSources, Path, ...).
            recursive: recurse into all libraries.
            filters: list of Jellyfin item filters (e.g. IsMissing).
            paginate: when True, follow StartIndex paging until exhausted;
                when False, issue a single unbounded request (legacy shape).

        Returns:
            List of item objects.
        """
        params = {
            'Recursive': 'true' if recursive else 'false',
        }
        if include_item_types:
            params['IncludeItemTypes'] = ','.join(include_item_types)
        if fields:
            params['Fields'] = ','.join(fields)
        if filters:
            params['Filters'] = ','.join(filters)

        if not paginate:
            result = self.request('GET', '/Items', params=params)
            return (result or {}).get('Items', [])

        items = []
        start_index = 0
        while True:
            page = self.request('GET', '/Items', params=dict(
                params, StartIndex=start_index, Limit=PAGE_SIZE))
            batch = (page or {}).get('Items', [])
            items.extend(batch)
            total = (page or {}).get('TotalRecordCount', 0)
            start_index += len(batch)
            if not batch or start_index >= total:
                return items

    def delete_item(self, item_id):
        """Delete one item by id.

        Returns C(True) when the item was deleted, C(False) when it was
        already gone (404). Any other API error propagates so the caller can
        decide per item — Jellyfin answers 500 for items whose file is
        missing, and playbooks use that to schedule DB-level cleanup.
        """
        try:
            self.request('DELETE', '/Items/{0}'.format(item_id))
        except TVDinnerNotFoundError:
            return False
        return True

    # ========== Library Methods ==========

    def list_libraries(self):
        """List virtual folders (media libraries)."""
        return self.request('GET', '/Library/VirtualFolders') or []

    def create_library(self, name, collection_type, paths,
                       refresh_library=True):
        """Create a media library."""
        return self.request(
            'POST', '/Library/VirtualFolders',
            params={
                'name': name,
                'collectionType': collection_type,
                'refreshLibrary': 'true' if refresh_library else 'false',
                'paths': paths,
            },
        )

    def delete_library(self, name, refresh_library=True):
        """Delete a media library by name."""
        return self.request(
            'DELETE', '/Library/VirtualFolders',
            params={
                'name': name,
                'refreshLibrary': 'true' if refresh_library else 'false',
            },
        )
