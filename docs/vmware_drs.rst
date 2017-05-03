.. _vmware_drs:


vmware_drs - Create VMWare DRS Rule
+++++++++++++++++++++++++++++++++++

.. versionadded:: 2.3


.. contents::
   :local:
   :depth: 2


Synopsis
--------

* Create VMWare DRS Rule.


Requirements (on host that executes module)
-------------------------------------------

  * pyvmomi


Options
-------

.. raw:: html

    <table border=1 cellpadding=4>
    <tr>
    <th class="head">parameter</th>
    <th class="head">required</th>
    <th class="head">default</th>
    <th class="head">choices</th>
    <th class="head">comments</th>
    </tr>
                <tr><td>cluster<br/><div style="font-size: small;"></div></td>
    <td>yes</td>
    <td></td>
        <td></td>
        <td><div>The cluster name for the DRS rule.</div>        </td></tr>
                <tr><td>force_update<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td>false</td>
        <td><ul><li>True</li><li>False</li></ul></td>
        <td><div>Force an update.</div><div>Performs a delete and create.</div><div>Note: Task will always be marked as changed.</div>        </td></tr>
                <tr><td>gather_facts<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td>false</td>
        <td><ul><li>True</li><li>False</li></ul></td>
        <td><div>If set to <code>true</code>, fact gather only.</div><div>Return rules defined on cluster.</div><div>If vms are defined, return vm facts.</div>        </td></tr>
                <tr><td>hostname<br/><div style="font-size: small;"></div></td>
    <td>yes</td>
    <td></td>
        <td></td>
        <td><div>The hostname or IP address of the vSphere vCenter.</div>        </td></tr>
                <tr><td>keep_together<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td></td>
        <td><ul><li>True</li><li>False</li></ul></td>
        <td><div>Required when state is set to <code>present</code>.</div><div>Set to <code>true</code> will create an Affinity rule.</div><div>Set to <code>false</code> will create an AntiAffinity rule.</div><div>Use <code>force_update</code> to change an existing rule.</div>        </td></tr>
                <tr><td>name<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td></td>
        <td></td>
        <td><div>The name of the DRS rule to manage.</div><div>Required when gather_facts is <code>false</code></div>        </td></tr>
                <tr><td>password<br/><div style="font-size: small;"></div></td>
    <td>yes</td>
    <td></td>
        <td></td>
        <td><div>The password of the vSphere vCenter.</div>        </td></tr>
                <tr><td>state<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td>present</td>
        <td><ul><li>present</li><li>absent</li></ul></td>
        <td><div>Create or delete the DRS rule.</div>        </td></tr>
                <tr><td>username<br/><div style="font-size: small;"></div></td>
    <td>yes</td>
    <td></td>
        <td></td>
        <td><div>The username of the vSphere vCenter.</div>        </td></tr>
                <tr><td>validate_certs<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td>true</td>
        <td><ul><li>True</li><li>False</li></ul></td>
        <td><div>Allows connection when SSL certificates are not valid.</div><div>Set to false when certificates are not trusted.</div>        </td></tr>
                <tr><td>vms<br/><div style="font-size: small;"></div></td>
    <td>no</td>
    <td></td>
        <td></td>
        <td><div>A list of vms for the DRS rule.</div><div>Required when state is <code>present</code></div>        </td></tr>
        </table>
    </br>



Examples
--------

 ::

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





Status
~~~~~~

This module is flagged as **preview** which means that it is not guaranteed to have a backwards compatible interface.


Support
~~~~~~~

This module is community maintained without core committer oversight.

For more information on what this means please read :doc:`modules_support`


For help in developing on modules, should you be so inclined, please read :doc:`community`, :doc:`dev_guide/developing_test_pr` and :doc:`dev_guide/developing_modules`.
