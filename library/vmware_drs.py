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
from __future__ import absolute_import, unicode_literals

DOCUMENTATION = '''
---
module: vmware_drs
author: "Brad Gibson, Richard Noble"
version_added: "2.3"
short_description: Create VMWare DRS Rule
requirements:
    - pyvmomi
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
            - Return list of DRS rules for hosts.
    state:
        required: false
        default: present
        choices:
            - present
            - absent
        description:
            - Create or delete the DRS rule.
    name:
        required: false
        description:
            - The name of the DRS rule to create or query.
    hosts:
        required: true
        description:
            - A list of hosts for the DRS rule.
    validate_certs:
        required: false
        default: true
        description:
            - Allows connection when SSL certificates are not valid.
            - Set to false when certificates are not trusted.
'''

EXAMPLES = '''
# gather facts
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    gather_facts: true
    hosts:
        - hosta
        - hostb

# create vmware drs rule
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    name: "hosta-hostb"
    hosts:
        - hosta
        - hostb

# delete vmware drs rule
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    state: "absent"
    name: "hosta-hostb"
    hosts:
        - hosta
        - hostb
'''

REQUIRED_MODULES = dict()
try:
    from ansible.module_utils.basic import AnsibleModule  # noqa
    REQUIRED_MODULES['ansible'] = True
except ImportError:
    REQUIRED_MODULES['ansible'] = False

try:
    from pyVmomi import vim
    from pyVim.connect import SmartConnect, Disconnect
    from pyVim.task import WaitForTask
    REQUIRED_MODULES['pyvmomi'] = True
except ImportError:
    REQUIRED_MODULES['pyvmomi'] = False


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
                        'failed': False}

        self.data = dict()

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
        except IOError:
            self.results['msg'] = "error connecting to vcenter"
            self.module.fail_json(**self.results)

        return vcenter

    def _get_obj(self, content, vimtype, name=None):
        """Get object."""
        # pylint: disable = no-self-use, unused-argument
        return content.viewManager.CreateContainerView(
            content.rootFolder, [vimtype], recursive=True).view

    def delete(self):
        """Delete VMWare DRS rule."""
        deleted = False
        cluster = self.data['cluster_objs'][self.arg.cluster]
        key = self.data['keys'][self.arg.name]
        rule_spec = vim.cluster.RuleSpec(removeKey=key, operation='remove')
        config_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])
        try:
            WaitForTask(cluster.ReconfigureEx(config_spec, modify=True))
        except vim.fault.NoPermission:
            self.module.fail_json(msg="permission denied")

        if not self.check():
            deleted = True
        return deleted

    def create(self):
        """Create VMware DRS rule."""
        created = False
        vms = self.data['vms']
        cluster = self.data['cluster_objs'][self.arg.cluster]
        rule = vim.cluster.AntiAffinityRuleSpec(vm=vms,
                                                enabled=True,
                                                mandatory=True,
                                                name=self.arg.name)
        rule_spec = vim.cluster.RuleSpec(info=rule, operation='add')
        config_spec = vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])
        try:
            WaitForTask(cluster.ReconfigureEx(config_spec, modify=True))
        except vim.fault.NoPermission:
            self.module.fail_json(msg="permission denied")

        if self.check():
            created = True
        return created

    def check(self):
        """Check if rule exists and all hosts are members."""
        check_pass = False
        self.gather_facts()

        rule_exists = False
        hosts_in_rule = False
        rules = 0
        hosts = list()
        for name, vm_info in self.results['ansible_facts']['vms'].iteritems():
            hosts.append(name)
            for _, value in vm_info['cluster'].iteritems():
                for rule in value['rules']:
                    if self.arg.name == rule['name']:
                        rules += 1

        if hosts != self.arg.hosts:
            self.module.fail_json(msg="vm hosts not all found.")

        if rules > 0:
            rule_exists = True

        if rules == len(hosts):
            hosts_in_rule = True

        if rule_exists and hosts_in_rule:
            check_pass = True

        return check_pass

    def gather_facts(self):
        """Gather facts."""
        # create facts dict
        self.results['ansible_facts'] = dict()
        content = self.vcenter.RetrieveContent()

        # initialize resources
        cluster_view = self._get_obj(content, vim.ComputeResource)
        vm_view = self._get_obj(content, vim.VirtualMachine)

        # build vms and drs rules lists
        vms = dict()
        self.data['cluster_objs'] = dict()
        self.data['vms'] = list()
        self.data['keys'] = dict()
        for host in self.arg.hosts:
            vms[host] = {'host': None, 'cluster': dict()}

        for vmobj in vm_view:
            try:
                vm_name = vmobj.summary.config.name
                vm_host = vmobj.summary.runtime.host.name
                if vm_name in self.arg.hosts:
                    vms[vm_name]['host'] = vm_host
                    self.data['vms'].append(vmobj)
                else:
                    raise Exception
            # pylint: disable=broad-except
            except Exception:
                continue

            for cluster in cluster_view:
                if cluster.name != self.arg.cluster:
                    continue
                self.data['cluster_objs'][cluster.name] = cluster
                try:
                    rules_fnd = cluster.FindRulesForVm(vmobj)
                except AttributeError:
                    rules_fnd = list()
                rules = list()
                for rule in rules_fnd:
                    rules.append({'name': rule.name, 'key': rule.key})
                    self.data['keys'][rule.name] = rule.key
                vms[vm_name]['cluster'][cluster.name] = {'rules': rules}
        self.results['ansible_facts']['vms'] = vms
        return


def main():
    """Main."""
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str', required=True),
            port=dict(type='int', default=443),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True),
            gather_facts=dict(type='bool', default=False),
            state=dict(type='str', default='present'),
            name=dict(type='str', required=False),
            cluster=dict(type='str', required=True),
            hosts=dict(type='list', required=True),
            validate_certs=dict(type='bool', default=True),
        ),
        supports_check_mode=True
    )

    # set default results to failed
    results = {'failed': True, 'msg': 'something went wrong'}

    # check dependencies
    for requirement in REQUIRED_MODULES:
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
        with VMWareDRS(module) as vcenter:
            vcenter.gather_facts()
            vcenter.module.exit_json(**vcenter.results)

    # normal run
    with VMWareDRS(module) as vcenter:
        exists = vcenter.check()
        if module.params['state'] == 'present':
            if not exists:
                vcenter.results['changed'] = vcenter.create()
        if module.params['state'] == 'absent':
            if exists:
                vcenter.results['changed'] = vcenter.delete()
        module.exit_json(**vcenter.results)

    module.fail_json(**results)


if __name__ == '__main__':
    main()
