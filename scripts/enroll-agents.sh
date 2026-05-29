#!/usr/bin/env bash
# RHEL target'larga Wazuh agent + OpenSCAP o'rnatadi (Ansible).
set -euo pipefail
cd "$(dirname "$0")/../ansible"
if [ ! -f inventory.ini ]; then
  echo "XATO: ansible/inventory.ini yo'q." >&2
  echo "  inventory.ini.example'dan nusxa olib, real serverlar + SSH kalit bilan to'ldiring." >&2
  exit 1
fi
ansible-playbook site.yml "$@"
