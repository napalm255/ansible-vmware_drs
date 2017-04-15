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
author:
    - Brad Gibson (@napalm255)
    - Richard Noble (@nobler1050)
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
            - If set to C(true), fact gather only.
    state:
        required: false
        default: present
        choices:
            - present
            - absent
        description:
            - Create or delete the DRS rule.
    cluster:
        required: true
        description:
            - The cluster name where the DRS rule will be created.
    name:
        required: false
        description:
            - The name of the DRS rule to create or query.
            - Required when gather_facts is C(false)
    hosts:
        required: true
        description:
            - A list of hosts for the DRS rule.
    keep_together:
        required: false
        description:
            - Required when state is set to C(present).
            - Set to C(true) will create an Affinity Rule.
            - Set to C(false) will create an AntiAffinity Rule.
    force_update:
        required: false
        description:
            - Force an update.
            - "Note: Task will always be marked as changed."
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
    keep_together: false
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

# pylint: disable = wrong-import-position
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.vmware import connect_to_api, gather_vm_facts
from ansible.module_utils.vmware import find_vm_by_name, find_cluster_by_name
from ansible.module_utils.vmware import wait_for_task

REQUIRED_MODULES = dict()
try:
    from pyVmomi import vim
    REQUIRED_MODULES['pyvmomi'] = True
except ImportError:
    REQUIRED_MODULES['pyvmomi'] = False


class VMWareDRS(object):
    """VMWare DRS Class."""

    # pylint: disable = too-many-instance-attributes

    def __init__(self, module):
        """Init."""
        self.module = module
        self.arg = lambda: None
        for arg in self.module.params:
            setattr(self.arg, arg, self.module.params[arg])

        self.results = {'changed': False,
                        'failed': False,
                        'ansible_facts': dict()}

        self.content = self._connect()
        self.vms = None
        self.cluster = None
        self.rule_exists = False
        self.hosts_in_rule = False

    def __enter__(self):
        """Enter."""
        return self

    def __exit__(self, type, value, traceback):
        """Exit."""
        # pylint: disable=redefined-builtin
        return

    def _connect(self):
        """Connect to vCenter."""
        return connect_to_api(self.module)

    def _get_cluster(self, name):
        """Find cluster by name and return object."""
        return find_cluster_by_name(self.content, name)

    def _get_drs_rules(self, cluster, vm_obj):
        """Find drs rules for vm and return object."""
        # pylint: disable = no-self-use
        rules_obj = cluster.FindRulesForVm(vm_obj)
        exclude_properties = ['dynamicType', 'dynamicProperty', 'vm']
        rules = list()
        for rule in rules_obj:
            rule_obj = dict()
            for attr, value in vars(rule).iteritems():
                if attr in exclude_properties:
                    continue
                rule_obj[attr] = value
            rules.append(rule_obj)
        return rules

    def _get_vm(self, name):
        """Find vm by name and return object."""
        return find_vm_by_name(self.content, name, self.cluster)

    def _get_facts(self, vm_obj):
        """Gather facts about vm and return object."""
        return gather_vm_facts(self.content, vm_obj)

    def _get_vm_list(self):
        """Get vm names and return list."""
        vms = list()
        for vm_info in self.vms:
            vms.append(vm_info['vm_obj'])
        return vms

    def _get_rule_keys(self):
        """Get keys and return list of keys."""
        keys = set()
        for vm_info in self.vms:
            for rule in vm_info['rules']:
                if rule['name'] == self.arg.name:
                    keys.add(rule['key'])
        return keys

    def _get_create_spec(self, vms, enabled=True, mandatory=False, name=None):
        """Create and return config_spec for creation."""
        if not name:
            name = self.arg.name
        if self.arg.keep_together:
            rule_type = 'AffinityRuleSpec'
        else:
            rule_type = 'AntiAffinityRuleSpec'

        rulespec = getattr(vim.cluster, rule_type)
        rule = rulespec(vm=vms, enabled=enabled, mandatory=mandatory, name=name)
        rule_spec = vim.cluster.RuleSpec(info=rule, operation='add')
        return vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])

    def _get_delete_spec(self, key):
        """Create and return config_spec for deletion."""
        # pylint: disable = no-self-use
        rule_spec = vim.cluster.RuleSpec(removeKey=key, operation='remove')
        return vim.cluster.ConfigSpecEx(rulesSpec=[rule_spec])

    def gather_facts(self):
        """Gather facts."""
        vms = list()
        self.results['ansible_facts']['vms'] = list()

        self.cluster = self._get_cluster(self.arg.cluster)
        if not self.cluster:
            self.module.fail_json(msg='cluster not found: %s' % self.arg.cluster)

        for host in self.arg.hosts:
            vm_obj = self._get_vm(host)
            if not vm_obj:
                self.module.fail_json(msg='host not found: %s' % host)
            vm_facts = self._get_facts(vm_obj)
            vm_rules = self._get_drs_rules(self.cluster, vm_obj)
            ansible_facts = {'name': host,
                             'facts': vm_facts,
                             'cluster': self.cluster.name,
                             'rules': vm_rules}
            self.results['ansible_facts']['vms'].append(ansible_facts)
            # add objects to pass along
            ansible_facts_objs = dict(ansible_facts)
            ansible_facts_objs.update({'vm_obj': vm_obj})
            vms.append(ansible_facts_objs)
        self.vms = vms

    def check(self):
        """Check if rule exists and all hosts are members."""
        exists = False
        self.rule_exists = False
        self.hosts_in_rule = False
        self.gather_facts()

        rules = 0
        hosts = list()
        for host in self.vms:
            for rule in host['rules']:
                if rule['name'] == self.arg.name:
                    hosts.append(host['name'])
                    rules += 1

        if rules > 0:
            self.rule_exists = True

        if hosts == self.arg.hosts:
            self.hosts_in_rule = True

        if self.rule_exists and self.hosts_in_rule:
            exists = True
        return exists

    def delete(self):
        """Delete VMWare DRS rule."""
        deleted = False
        keys = self._get_rule_keys()
        for key in keys:
            try:
                wait_for_task(self.cluster.ReconfigureEx(self._get_delete_spec(key),
                                                         modify=True))
            except vim.fault.NoPermission:
                self.module.fail_json(msg="permission denied")

        if not self.check():
            deleted = True
        return deleted

    def create(self):
        """Create VMware DRS rule."""
        created = False
        vms = self._get_vm_list()
        try:
            wait_for_task(self.cluster.ReconfigureEx(self._get_create_spec(vms),
                                                     modify=True))
        except vim.fault.NoPermission:
            self.module.fail_json(msg="permission denied")

        if self.check():
            created = True
        return created

    def update(self):
        """Update VMWare DRS rule."""
        updated = False
        self.delete()
        self.create()

        if self.check():
            updated = True
        return updated


def main():
    """Main."""
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str', required=True),
            port=dict(type='int', default=443),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            gather_facts=dict(type='bool', default=False),
            state=dict(type='str', default='present'),
            cluster=dict(type='str', required=True),
            name=dict(type='str', required=False),
            hosts=dict(type='list', required=True),
            keep_together=dict(type='bool', required=False),
            force_update=dict(type='bool', default=False),
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
            vcenter.module.exit_json(**vcenter.results)

    # gather facts
    if module.params['gather_facts']:
        with VMWareDRS(module) as vcenter:
            vcenter.gather_facts()
            vcenter.module.exit_json(**vcenter.results)

    # normal run
    with VMWareDRS(module) as vcenter:
        vcenter.check()
        if vcenter.arg.state == 'present':
            if vcenter.arg.force_update:
                vcenter.results['changed'] = vcenter.update()
            elif not vcenter.rule_exists:
                vcenter.results['changed'] = vcenter.create()
            elif not vcenter.hosts_in_rule:
                vcenter.results['changed'] = vcenter.update()
        elif vcenter.arg.state == 'absent':
            if vcenter.rule_exists:
                vcenter.results['changed'] = vcenter.delete()
        vcenter.module.exit_json(**vcenter.results)

    module.fail_json(**results)


if __name__ == '__main__':
    main()
