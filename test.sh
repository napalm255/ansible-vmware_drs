#!/usr/bin/env bash
#
# Helper script for loading environment variables in order to use test.yml.
#
# This script needs to be sourced.
#
#

if [[ $_ != $0 ]]; then
  export VMDRS_VCENTER_HOSTNAME=$(read -p "Hostname: " && echo $REPLY)
  export VMDRS_VCENTER_USER=$(read -p "Username: " && echo $REPLY)
  export VMDRS_VCENTER_PASS=$(read -p "Password: " -s && echo $REPLY)
  echo
  export VMDRS_CLUSTER_NAME=$(read -p "Cluster Name: " && echo $REPLY)
  export VMDRS_RULE_NAME=$(read -p "DRS Rule Name: " && echo $REPLY)
  export VMDRS_VMS=$(read -p "VMs (comma delim.): " && echo $REPLY)
else
  echo "usage: source $_"
fi
