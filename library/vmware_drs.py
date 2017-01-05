#!/usr/bin/env python
# -*- coding: utf-8 -*-

# (c) 2016, Brad Gibson <napalm255@gmail.com>,
#           Richard Noble <nobler1050@gmail.com>
#
# This file is a 3rd Party module for Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

"""Ansible VMWare DRS Module."""

DOCUMENTATION = '''
---
module: vmware_drs
author: "Brad Gibson, Richard Noble"
version_added: "2.2"
short_description: Create VMWare DRS Rule
requires: [ pyvmomi==6.5.0 ]
description:
    - Create VMWare DRS Rule
options:
    datacenter:
        required: true
        description:
            - VMWare Datacenter Name
    cluster:
        required: true
        description:
            - VMWare Cluster Name
    user:
        required: true
        description:
            - VMWare User
    password:
        required: true
        description:
            - VMWare Password
    vm_host_a:
        required: true
        description:
            - VMWare Host A
    vm_host_b:
        required: true
        description:
            - VMWare Host B
    validate_certs:
        required: false
        default: true
        description:
            - Validate SSL certificate.
'''

EXAMPLES = '''
# create vmware drs rule
- vmware_drs:
    datacenter: datacenter_name
    cluster: cluster_name
    user: username
    password: password
    vm_host_a: host1
    vm_host_b: host2
'''
# pylint: disable = wrong-import-position

REQUIREMENTS = dict()
try:
    from ansible.module_utils.basic import AnsibleModule  # noqa
    REQUIREMENTS['ansible'] = True
except ImportError:
    REQUIREMENTS['ansible'] = False

try:
    from pyVmomi import vim
    REQUIREMENTS['pyvmomi'] = True
except ImportError:
    REQUIREMENTS['pyvmomi'] = False


def main():
    """Main."""
    # pylint: disable = too-many-branches
    module = AnsibleModule(
        argument_spec=dict(
            datacenter=dict(type='str', required=True),
            cluster=dict(type='str', required=True),
            user=dict(type='str', required=True),
            password=dict(type='str', required=True),
            vm_host_a=dict(type='str', required=True),
            vm_host_b=dict(type='str', required=True),
            validate_certs=dict(type='bool', default=True),
        ),
        supports_check_mode=True
    )

    # check dependencies
    for requirement in REQUIREMENTS:
        if not requirement:
            module.fail_json(msg='%s not installed.' % ('requirement'))

    # initiate module
    results = {'failed': True, 'msg': 'something went wrong'}

    # check mode
    if module.check_mode:
        results = {'failed': False,
                   'msg': 'Check mode not implemented. Variable debug only.',
                   'params': module.params,
                   'requirements': REQUIREMENTS,
                   'pyVmomi_dir': dir(vim.vm)}
        module.exit_json(**results)

    # pylint: disable = fixme
    # TODO: Add Code Here
    # Create results json.
    # Needs either 'failed' or 'changed' set to True or False accordingly.
    # Include any other data to show up with debug verbosity.
    results = {'failed': False, 'requirements_installed': REQUIREMENTS}

    module.exit_json(**results)


if __name__ == '__main__':
    main()
