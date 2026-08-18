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
    fail_on_error:
        description:
            - Fail the task when any item cannot be deleted. Jellyfin answers
              500 for items whose underlying file has already disappeared;
              set this to false to delete what can be deleted and get the
              rest back in C(failed_items) for DB-level cleanup.
            - Items that are already gone (404) are never an error.
        type: bool
        default: true
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
    description: Item ids that were deleted (all requested ids in check mode).
    returned: always
    type: list
    elements: str
missing:
    description: Item ids that were already gone (404); not counted as a change.
    returned: always
    type: list
    elements: str
failed_items:
    description: Items Jellyfin refused to delete, with the API error.
    returned: always
    type: list
    elements: dict
    contains:
        id:
            description: Item id.
            type: str
        status_code:
            description: HTTP status Jellyfin returned.
            type: int
        msg:
            description: Error message.
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
        ids=dict(type='list', elements='str', required=True),
        state=dict(type='str', choices=['absent'], default='absent'),
        fail_on_error=dict(type='bool', default=True),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    result = dict(changed=False, deleted=[], missing=[], failed_items=[])

    try:
        client = get_client_from_module(module)
        ids = module.params['ids']

        if module.check_mode:
            result['deleted'] = list(ids)
            result['changed'] = bool(ids)
            module.exit_json(**result)

        # One request per item: Jellyfin's batch DELETE /Items?Ids= aborts on
        # the first bad id, and callers need to know which ids failed.
        for item_id in ids:
            try:
                if client.delete_item(item_id):
                    result['deleted'].append(item_id)
                else:
                    result['missing'].append(item_id)
            except TVDinnerError as e:
                result['failed_items'].append(
                    dict(id=item_id, status_code=e.status_code, msg=str(e)))

        result['changed'] = bool(result['deleted'])
        if result['failed_items'] and module.params['fail_on_error']:
            module.fail_json(
                msg='{0} item(s) could not be deleted'.format(len(result['failed_items'])),
                **result)

        module.exit_json(**result)

    except TVDinnerError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
