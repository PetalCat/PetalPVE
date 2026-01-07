"""Constants for the Proxmox VE (pxhassos) integration."""

import logging

DOMAIN = "pxhassos"
LOGGER = logging.getLogger(__package__)

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USER = "username"
CONF_PASSWORD = "password"
CONF_REALM = "realm"
CONF_VERIFY_SSL = "verify_ssl"
CONF_NODE_EXCLUDE = "node_exclude"
CONF_VM_EXCLUDE = "vm_exclude"
CONF_LXC_EXCLUDE = "lxc_exclude"

DEFAULT_PORT = 8006
DEFAULT_REALM = "pam"
DEFAULT_VERIFY_SSL = True

# Update intervals
SCAN_INTERVAL_FAST = 30 # seconds (for sensors that change often)
SCAN_INTERVAL_SLOW = 300 # seconds (for resources that rarely change)

# Services
SERVICE_REBOOT_NODE = "reboot_node"
SERVICE_SHUTDOWN_NODE = "shutdown_node"
SERVICE_START_VM = "start_vm"
SERVICE_STOP_VM = "stop_vm"
SERVICE_SHUTDOWN_VM = "shutdown_vm"
SERVICE_REBOOT_VM = "reboot_vm"

ATTR_NODE = "node"
ATTR_VM_ID = "vm_id"
ATTR_VM_TYPE = "vm_type" # qemu or lxc
