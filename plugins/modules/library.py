#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: library
short_description: Manage Jellyfin media libraries
description:
    - Create or delete media libraries (virtual folders) by name.
    - Idempotent by library name.
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
    name:
        description:
            - Library name.
        type: str
        required: true
    collection_type:
        description:
            - Library content type (movies, tvshows, music, books, ...).
              Required when I(state=present).
        type: str
    paths:
        description:
            - Host paths backing the library.
        type: list
        elements: str
    state:
        description:
            - Whether the library should exist.
        type: str
        choices: [present, absent]
        default: present
'''

EXAMPLES = r'''
- name: Ensure the movies library exists
  tvdinner.jellyfin.library:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    name: Movies
    collection_type: movies
    paths: ["/media/movies"]

- name: Remove a stale library
  tvdinner.jellyfin.library:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    name: Old Library
    state: absent
'''

RETURN = r'''
library:
    description: The library name.
    returned: always
    type: str
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
        name=dict(type='str', required=True),
        collection_type=dict(type='str'),
        paths=dict(type='list', elements='str'),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['collection_type', 'paths'])],
        supports_check_mode=True,
    )
    result = dict(changed=False, library=module.params['name'])

    try:
        client = get_client_from_module(module)
        name = module.params['name']
        state = module.params['state']

        existing = next(
            (l for l in client.list_libraries() if l.get('Name') == name), None)

        if state == 'absent':
            if existing is not None:
                result['changed'] = True
                if not module.check_mode:
                    client.delete_library(name)
        else:
            if existing is None:
                result['changed'] = True
                if not module.check_mode:
                    client.create_library(
                        name=name,
                        collection_type=module.params['collection_type'],
                        paths=module.params['paths'],
                    )

        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
