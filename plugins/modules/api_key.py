#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: api_key
short_description: Manage Jellyfin API keys
description:
    - Create or delete Jellyfin API keys by label. Idempotent by name —
      creating a key whose label already exists is a no-op.
    - Replaces the validate-by-trial loops playbooks use to find a working key.
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
            - Admin API key used to manage other keys.
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
            - Label of the API key.
        type: str
        required: true
    state:
        description:
            - Whether the key should exist.
        type: str
        choices: [present, absent]
        default: present
'''

EXAMPLES = r'''
- name: Ensure a Homepage widget API key exists
  tvdinner.jellyfin.api_key:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    name: homepage

- name: Remove an old key
  tvdinner.jellyfin.api_key:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    name: homepage-old
    state: absent
'''

RETURN = r'''
api_key:
    description: The key's label and token (token only available on creation).
    returned: when state is present
    type: dict
    contains:
        name:
            description: Key label.
            type: str
        token:
            description: Access token value, returned only for newly created keys.
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
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = dict(changed=False)

    try:
        client = get_client_from_module(module)
        name = module.params['name']
        state = module.params['state']

        existing = next(
            (k for k in client.list_keys() if k.get('Name') == name), None)

        if state == 'absent':
            if existing is not None:
                result['changed'] = True
                if not module.check_mode:
                    client.delete_key(existing['AccessToken'])
        else:
            if existing is None:
                result['changed'] = True
                if not module.check_mode:
                    created = client.create_key(name) or {}
                    result['api_key'] = {'name': name, 'token': created.get('AccessToken')}
                else:
                    result['api_key'] = {'name': name}
            else:
                result['api_key'] = {'name': name}

        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
