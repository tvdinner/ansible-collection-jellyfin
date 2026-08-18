#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: item_info
short_description: Query Jellyfin items
description:
    - Query items by type and field filters, transparently paginating
      (the hand-rolled playbook query pulled Limit=10000 in one request).
    - Read-only; always reports changed=false.
version_added: "1.0.0"
author:
    - Joe Stump (@joestump)
options:
    jellyfin_url:
        description:
            - URL of the Jellyfin instance.
        type: str
        required: true
    jellyfin_api_key:
        description:
            - API key to authenticate with.
        type: str
        required: true
        no_log: true
    validate_certs:
        description:
            - Whether to validate SSL certificates.
        type: bool
        default: true
    timeout:
        description:
            - Request timeout in seconds.
        type: int
        default: 30
    include_item_types:
        description:
            - Item types to include (Movie, Episode, Series, ...).
        type: list
        elements: str
    fields:
        description:
            - Extra fields to request per item (MediaSources, Path, ...).
        type: list
        elements: str
    filters:
        description:
            - Jellyfin item filters (e.g. IsMissing).
        type: list
        elements: str
    recursive:
        description:
            - Recurse into all libraries.
        type: bool
        default: true
'''

EXAMPLES = r'''
- name: Find items with missing media data
  tvdinner.jellyfin.item_info:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    include_item_types: [Movie, Episode]
    fields: [MediaSources, Path]
  register: jellyfin_items
'''

RETURN = r'''
items:
    description: Matching items.
    returned: always
    type: list
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.tvdinner.jellyfin.plugins.module_utils.common import (
    get_client_from_module,
    jellyfin_argument_spec,
)
from ansible_collections.tvdinner.core.plugins.module_utils.client import TVDinnerError


def run_module():
    argument_spec = jellyfin_argument_spec()
    argument_spec.update(
        include_item_types=dict(type='list', elements='str'),
        fields=dict(type='list', elements='str'),
        filters=dict(type='list', elements='str'),
        recursive=dict(type='bool', default=True),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = dict(changed=False)

    try:
        client = get_client_from_module(module)
        result['items'] = client.query_items(
            include_item_types=module.params['include_item_types'],
            fields=module.params['fields'],
            recursive=module.params['recursive'],
            filters=module.params['filters'],
        )
        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
