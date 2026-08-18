# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.tvdinner.core.plugins.module_utils.client import TVDinnerError as JellyfinError  # noqa: F401
from ansible_collections.tvdinner.core.plugins.module_utils.common import (
    client_from_module,
    connection_argument_spec,
)


def jellyfin_argument_spec():
    """Return the common connection argument spec for Jellyfin modules."""
    return connection_argument_spec('jellyfin_url', 'jellyfin_api_key')


def get_client_from_module(module):
    """Create a JellyfinClient from module params."""
    from ansible_collections.tvdinner.jellyfin.plugins.module_utils.client import JellyfinClient
    return client_from_module(module, JellyfinClient, 'jellyfin_url', 'jellyfin_api_key')
