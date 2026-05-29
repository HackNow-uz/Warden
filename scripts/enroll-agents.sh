#!/usr/bin/env bash
# RHEL target'larga Wazuh agent + OpenSCAP o'rnatadi (Ansible).
set -euo pipefail
cd "$(dirname "$0")/../ansible"
[ -f inventory.ini ] || cp inventory.ini.example inventory.ini
ansible-playbook site.yml
