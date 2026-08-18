#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: item
short_description: Delete Jellyfin items
description:
    - Delete items from the Jellyfin library by id. Jellyfin's API has no
      item creation, so only I(state=absent) is supported; use
      L(item_info,./item_info.html) to find the ids (e.g. dead entries whose
      media sources are gone).
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
            - Admin API key.
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
    ids:
        description:
            - Item ids to delete.
        type: list
        elements: str
        required: true
    state:
        description:
            - Only absent is supported; items cannot be created via API.
        type: str
        choices: [absent]
        default: absent
'''

EXAMPLES = r'''
- name: Delete dead items found by item_info
  tvdinner.jellyfin.item:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    ids: "{{ dead_items | map(attribute='Id') | list }}"
    state: absent
'''

RETURN = r'''
deleted:
    description: Item ids requested for deletion.
    returned: always
    type: list
    elements: str
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
        ids=dict(type='list', elements='str', required=True),
        state=dict(type='str', choices=['absent'], default='absent'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = dict(changed=False)

    try:
        client = get_client_from_module(module)
        ids = module.params['ids']

        result['changed'] = bool(ids)
        result['deleted'] = ids
        if ids and not module.check_mode:
            client.delete_items(ids)

        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
