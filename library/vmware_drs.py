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
    hostname:
        required: true
        description:
            - The hostname or IP address of the vSphere vCenter.
    port:
        required: false
        default: 443
        description:
            - The port to connect to vSphere vCenter.
    username:
        required: true
        description:
            - The username of the vSphere vCenter.
    password:
        required: true
        description:
            - The password of the vSphere vCenter.
    gather_facts:
        required: false
        default: false
        description:
            - Return list of DRS rules.
    name:
        required: false
        description:
            - The name of the DRS rule to create or query. Required when
            creating DRS rule.
    hosts:
        required: false
        description:
            - A list of hosts for the DRS rule. Required when creating DRS
            rule.
    validate_certs:
        required: false
        default: true
        description:
            - Allows connection when SSL certificates are not valid. Set to
            false when certificates are not trusted.
'''

EXAMPLES = '''
# gather facts
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    gather_facts: true

# create vmware drs rule
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    name: "hosta-hostb"
    hosts:
        - hosta
        - hostb
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
    from pyVim.connect import SmartConnect, Disconnect
    from pyVim.task import WaitForTask
    REQUIREMENTS['pyvmomi'] = True
except ImportError:
    REQUIREMENTS['pyvmomi'] = False


class VMWareDRS(object):
    """VMWare DRS Class."""

    def __init__(self, module):
        """Init."""
        self.module = module
        self.arg = lambda: None
        for arg in self.module.params:
            setattr(self.arg, arg, self.module.params[arg])

        # redact password for security
        if 'password' in module.params:
            module.params['password'] = 'REDACTED'

        self.results = {'changed': False,
                        'failed': False,
                        'args': module.params}

        self.vcenter = None

    def __enter__(self):
        """Initiate connection."""
        self.vcenter = self._connect()
        return self

    def __exit__(self, type, value, traceback):
        """Disconnect."""
        # pylint: disable=redefined-builtin
        Disconnect(self.vcenter)
        return

    def _connect(self):
        """Connect to vCenter."""
        try:
            vcenter = SmartConnect(host=self.arg.hostname,
                                   port=self.arg.port,
                                   user=self.arg.username,
                                   pwd=self.arg.password)
            self.results['connected'] = True
        except IOError:
            self.results['connected'] = False
            self.results['msg'] = "error connecting to vcenter"
            self.module.fail_json(**self.results)

        return vcenter

    def _get_obj(self, content, vimtype, name=None):
        """Get object."""
        return content.viewManager.CreateContainerView(
            content.rootFolder, [vimtype], recursive=True).view

    def create(self):
        """Create VMware DRS rule."""
        # TODO: Add Creation. Return changed status or fail.
        return True

    def check(self):
        """Check if rule exists and all hosts are members."""
        check_pass = False
        facts = self.gather_facts(self.arg.name)
        rule_exists = False
        hosts_in_rule = False
        for cluster in facts['facts']['clusters']:
            if self.arg.name in cluster['rules']:
                rule_exists = True
                if sorted(self.arg.hosts) == sorted(cluster['rules'][self.arg.name]):
                    hosts_in_rule = True

        self.results['rule_exists'] = rule_exists
        self.results['hosts_in_rule'] = hosts_in_rule
        if rule_exists and hosts_in_rule:
            check_pass = True
        return check_pass

    def gather_facts(self, name=None):
        """Gather facts."""

        # create facts dict
        self.results['facts'] = dict()
        content = self.vcenter.RetrieveContent()

        # initialize clusters variable
        clusters = list()

        # clusters
        cluster_view = self._get_obj(content, vim.ComputeResource)

        # virtual machines
        vm_view = self._get_obj(content, vim.VirtualMachine)

        # build vms and drs rules lists
        for idx, cluster in enumerate(cluster_view):
            clusters.append({'name': cluster.name, 'rules': {}, 'vms': {}})
            for machine in vm_view:
                machine_name = machine.summary.config.name
                rules_results = cluster.FindRulesForVm(machine)
                for rule in rules_results:
                    if name is not None and name != rule.name:
                        continue

                    if rule.name not in clusters[idx]['rules']:
                        clusters[idx]['rules'][rule.name] = list()
                    clusters[idx]['rules'][rule.name].append(machine_name)
                    if machine_name not in clusters[idx]['vms']:
                        clusters[idx]['vms'][machine_name] = list()
                    clusters[idx]['vms'][machine_name].append(rule.name)
            if len(clusters[idx]['vms']) == 0 and len(clusters[idx]['rules']) == 0:
                clusters.pop(idx)

        if len(clusters) == 0:
            self.results['msg'] = "rule name not found"
            self.module.fail_json(**self.results)
        self.results['facts']['clusters'] = clusters

        return self.results


def main():
    """Main."""
    # pylint: disable = too-many-branches
    # pylint: disable = fixme
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str', required=True),
            port=dict(type='int', default=443),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True),
            gather_facts=dict(type='bool', default=False),
            name=dict(type='str', required=False),
            hosts=dict(type='list', required=False),
            validate_certs=dict(type='bool', default=True),
        ),
        supports_check_mode=True
    )

    # set default results to failed
    results = {'failed': True, 'msg': 'something went wrong'}

    # check dependencies
    for requirement in REQUIREMENTS:
        if not requirement:
            module.fail_json(msg='%s not installed.' % (requirement))

    # check mode
    if module.check_mode:
        with VMWareDRS(module) as vcenter:
            if not vcenter.check():
                vcenter.results['changed'] = True
            module.exit_json(**vcenter.results)

    # gather facts
    if module.params['gather_facts']:
        name = None
        if 'name' in module.params:
            name = module.params['name']
        with VMWareDRS(module) as vcenter:
            module.exit_json(**vcenter.gather_facts(name))

    # normal run
    with VMWareDRS(module) as vcenter:
        if not vcenter.check():
            vcenter.results['changed'] = vcenter.create()
        module.exit_json(**vcenter.results)

    module.fail_json(**results)


if __name__ == '__main__':
    main()
