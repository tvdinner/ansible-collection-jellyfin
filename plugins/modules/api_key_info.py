#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Joe Stump <joe@joestump.net>
# MIT License (see LICENSE)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: api_key_info
short_description: List Jellyfin API keys
description:
    - List API keys with their labels. Token values are included as returned
      by the Jellyfin API. Also reports whether the credentials used are valid,
      replacing the validate-by-trial loop in voltron.yaml.
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
    name:
        description:
            - Only return the key with this label.
        type: str
'''

EXAMPLES = r'''
- name: List all API keys
  tvdinner.jellyfin.api_key_info:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
  register: jellyfin_keys

- name: Find the homepage key
  tvdinner.jellyfin.api_key_info:
    jellyfin_url: https://jellyfin.example.com
    jellyfin_api_key: "{{ jellyfin_admin_key }}"
    name: homepage
  register: homepage_key
'''

RETURN = r'''
api_keys:
    description: List of API keys.
    returned: always
    type: list
    elements: dict
system_info:
    description: The /System/Info response, proving the credentials work.
    returned: always
    type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.tvdinner.jellyfin.plugins.module_utils.common import (
    get_client_from_module,
    jellyfin_argument_spec,
)
from ansible_collections.tvdinner.core.plugins.module_utils.client import TVDinnerError


def run_module():
    argument_spec = jellyfin_argument_spec()
    argument_spec.update(name=dict(type='str'))

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = dict(changed=False)

    try:
        client = get_client_from_module(module)
        result['system_info'] = client.get_system_info() or {}
        keys = client.list_keys()
        if module.params['name']:
            keys = [k for k in keys if k.get('AppName') == module.params['name']]
        result['api_keys'] = keys
        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
