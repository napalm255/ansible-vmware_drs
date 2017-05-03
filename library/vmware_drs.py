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
    - Create VMWare DRS Rule.
options:
    hostname:
        required: true
        description:
            - The hostname or IP address of the vSphere vCenter.
    username:
        required: true
        description:
            - The username of the vSphere vCenter.
    password:
        required: true
        description:
            - The password of the vSphere vCenter.
    cluster:
        required: true
        description:
            - The cluster name for the DRS rule.
    gather_facts:
        required: false
        default: "false"
        choices:
            - true
            - false
        description:
            - If set to C(true), fact gather only.
            - Return rules defined on cluster.
            - If vms are defined, return vm facts.
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
            - The name of the DRS rule to manage.
            - Required when gather_facts is C(false)
    vms:
        required: false
        description:
            - A list of vms for the DRS rule.
            - Required when state is C(present)
    keep_together:
        required: false
        choices:
            - true
            - false
        description:
            - Required when state is set to C(present).
            - Set to C(true) will create an Affinity rule.
            - Set to C(false) will create an AntiAffinity rule.
            - Use C(force_update) to change an existing rule.
    force_update:
        required: false
        default: "false"
        choices:
            - true
            - false
        description:
            - Force an update.
            - Performs a delete and create.
            - "Note: Task will always be marked as changed."
    validate_certs:
        required: false
        default: "true"
        choices:
            - true
            - false
        description:
            - Allows connection when SSL certificates are not valid.
            - Set to false when certificates are not trusted.
'''

EXAMPLES = '''
# gather facts on cluster and vms
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    cluster: "Cluster Name"
    gather_facts: true
    vms:
        - vma
        - vmb

# gather facts on just cluster
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    cluster: "Cluster Name"
    gather_facts: true

# create vmware drs rule
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    cluster: "Cluster Name"
    name: "drs-rule-name"
    vms:
        - vma
        - vmb
    keep_together: false

# delete vmware drs rule
- vmware_drs:
    hostname: "vcenter.example.com"
    username: "vcuser"
    password: "vcpass"
    cluster: "vcenter-cluster"
    state: "absent"
    name: "drs-rule-name"
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
        self.rules = None
        self.cluster = None
        self.rule_exists = False
        self.vms_in_rule = False

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

    def _get_drs_rules_by_cluster(self):
        """Find drs rules of the cluster and return object."""
        exclude_properties = ['dynamicType', 'dynamicProperty', 'vm']
        rules = list()
        for rule in self.cluster.configuration.rule:
            rule_obj = dict()
            for attr, value in vars(rule).iteritems():
                if attr in exclude_properties:
                    continue
                rule_obj[attr] = value
            rules.append(rule_obj)
        return rules

    def _get_drs_rules_by_vm(self, vm_obj):
        """Find drs rules of the cluster and return object."""
        exclude_properties = ['dynamicType', 'dynamicProperty', 'vm']
        rules = list()
        for rule in self.cluster.FindRulesForVm(vm_obj):
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

    def _get_rule_key(self):
        """Get key and return integer."""
        key = int()
        for rule in self.rules:
            if rule['name'] == self.arg.name:
                key = int(rule['key'])
        return key

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
        self.results['ansible_facts']['cluster'] = dict()
        self.results['ansible_facts']['vms'] = list()

        self.cluster = self._get_cluster(self.arg.cluster)
        if not self.cluster:
            self.module.fail_json(msg='cluster not found: %s' % self.arg.cluster)
        self.rules = self._get_drs_rules_by_cluster()
        self.results['ansible_facts']['cluster']['name'] = self.cluster.name
        self.results['ansible_facts']['cluster']['rules'] = self.rules

        for vm_name in self.arg.vms:
            vm_obj = self._get_vm(vm_name)
            if not vm_obj:
                self.module.fail_json(msg='vm not found: %s' % vm_name)
            vm_facts = self._get_facts(vm_obj)
            vm_rules = self._get_drs_rules_by_vm(vm_obj)
            ansible_facts = {'name': vm_name,
                             'facts': vm_facts,
                             'rules': vm_rules}
            self.results['ansible_facts']['vms'].append(ansible_facts)
            # add objects to pass along
            ansible_facts_objs = dict(ansible_facts)
            ansible_facts_objs.update({'vm_obj': vm_obj})
            vms.append(ansible_facts_objs)
        self.vms = vms

    def check(self):
        """Check if rule exists and all vms are members."""
        exists = False
        self.rule_exists = False
        self.vms_in_rule = False
        self.gather_facts()

        for rule in self.rules:
            if rule['name'] == self.arg.name:
                self.rule_exists = True
                break

        # FIXME: if vm in rule, but manually added, does not get
        #        updated
        vms = list()
        for vm_obj in self.vms:
            for rule in vm_obj['rules']:
                if rule['name'] == self.arg.name:
                    vms.append(vm_obj['name'])

        if vms == self.arg.vms:
            self.vms_in_rule = True

        if self.rule_exists and self.vms_in_rule:
            exists = True
        return exists

    def delete(self):
        """Delete VMWare DRS rule."""
        deleted = False
        key = self._get_rule_key()
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
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            gather_facts=dict(type='bool', default=False),
            state=dict(type='str', default='present'),
            cluster=dict(type='str', required=True),
            name=dict(type='str', required=False),
            vms=dict(type='list', default=list()),
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

    # gather facts
    if module.params['gather_facts']:
        with VMWareDRS(module) as vcenter:
            vcenter.gather_facts()
            vcenter.module.exit_json(**vcenter.results)

    # check mode
    if module.check_mode:
        with VMWareDRS(module) as vcenter:
            if not vcenter.check():
                vcenter.results['changed'] = True
            vcenter.module.exit_json(**vcenter.results)

    # normal run
    with VMWareDRS(module) as vcenter:
        vcenter.check()
        if vcenter.arg.state == 'present':
            if vcenter.arg.force_update:
                vcenter.results['changed'] = vcenter.update()
            elif not vcenter.rule_exists:
                vcenter.results['changed'] = vcenter.create()
            elif not vcenter.vms_in_rule:
                vcenter.results['changed'] = vcenter.update()
        elif vcenter.arg.state == 'absent':
            if vcenter.rule_exists:
                vcenter.results['changed'] = vcenter.delete()
        vcenter.module.exit_json(**vcenter.results)

    module.fail_json(**results)


if __name__ == '__main__':
    main()
