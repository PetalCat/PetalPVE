"""API Client for Proxmox VE."""
from __future__ import annotations

import logging
from typing import Any

from proxmoxer import ProxmoxAPI
from requests.exceptions import ConnectionError as RequestsConnectionError, ConnectTimeout, SSLError

from homeassistant.core import HomeAssistant

from .const import LOGGER

class ProxmoxClient:
    """Proxmox API Client wrapper."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        user: str,
        password: str,
        port: int,
        realm: str,
        verify_ssl: bool,
    ) -> None:
        """Initialize the Proxmox Client."""
        self._hass = hass
        # Strip scheme if present, just in case config flow missed it or old config
        self._host = host.replace("https://", "").replace("http://", "").rstrip("/")
        self._user = user
        self._password = password
        self._port = port
        self._realm = realm
        self._verify_ssl = verify_ssl
        self._proxmox: ProxmoxAPI | None = None

    def connect(self) -> bool:
        """Connect to the Proxmox API."""
        try:
            self._proxmox = ProxmoxAPI(
                self._host,
                user=f"{self._user}@{self._realm}",
                password=self._password,
                port=self._port,
                verify_ssl=self._verify_ssl,
            )
            # Test connection
            version = self._proxmox.version.get()
            LOGGER.debug("Connected to Proxmox VE: %s", version)
            return True
        except (RequestsConnectionError, ConnectTimeout, SSLError) as err:
            LOGGER.error("Failed to connect to Proxmox VE: %s", err)
            return False
        except Exception as err:
            LOGGER.exception("Unexpected error connecting to Proxmox VE: %s", err)
            return False

    def get_version(self) -> dict[str, Any] | None:
        """Get Proxmox version."""
        if not self._proxmox:
            return None
        try:
            return self._proxmox.version.get()
        except Exception as err:
            LOGGER.error("Failed to get version: %s", err)
            return None

    def get_nodes(self) -> list[dict[str, Any]]:
        """Get list of nodes."""
        if not self._proxmox:
            return []
        try:
            return self._proxmox.nodes.get()
        except Exception as err:
            # Check for 401 Unauthorized (Ticket Expired)
            if "401" in str(err) or "Unauthorized" in str(err):
                LOGGER.warning("Auth token expired, reconnecting...")
                if self.connect():
                    try:
                         return self._proxmox.nodes.get()
                    except Exception as retry_err:
                        LOGGER.error("Failed to get nodes after reconnect: %s", retry_err)
                else:
                    LOGGER.error("Reconnection failed.")
                    
            LOGGER.error("Failed to get nodes: %s", err)
            return []

    def get_node_status(self, node: str) -> dict[str, Any] | None:
        """Get status of a specific node."""
        if not self._proxmox:
            return None
        try:
            status = self._proxmox.nodes(node).status.get()
            return status
        except Exception as err:
            LOGGER.error("Failed to get node status for %s: %s", node, err)
            return None

    def get_vms(self, node: str) -> list[dict[str, Any]]:
        """Get list of QEMU VMs on a node."""
        if not self._proxmox:
            return []
        try:
            return self._proxmox.nodes(node).qemu.get()
        except Exception as err:
            # Check for 401 Unauthorized (Ticket Expired)
            if "401" in str(err) or "Unauthorized" in str(err):
                LOGGER.warning("Auth token expired, reconnecting...")
                if self.connect():
                    try:
                         return self._proxmox.nodes(node).qemu.get()
                    except Exception as retry_err:
                        LOGGER.error("Failed to get VMs after reconnect: %s", retry_err)
                else:
                    LOGGER.error("Reconnection failed.")
            
            LOGGER.error("Failed to get VMs for node %s: %s", node, err)
            return []

    def get_lxcs(self, node: str) -> list[dict[str, Any]]:
        """Get list of LXC containers on a node."""
        if not self._proxmox:
            return []
        try:
            return self._proxmox.nodes(node).lxc.get()
        except Exception as err:
             # Check for 401 Unauthorized (Ticket Expired)
            if "401" in str(err) or "Unauthorized" in str(err):
                LOGGER.warning("Auth token expired, reconnecting...")
                if self.connect():
                    try:
                         return self._proxmox.nodes(node).lxc.get()
                    except Exception as retry_err:
                        LOGGER.error("Failed to get LXCs after reconnect: %s", retry_err)
                else:
                    LOGGER.error("Reconnection failed.")
            
            LOGGER.error("Failed to get LXCs for node %s: %s", node, err)
            return []
    
    def get_storage(self, node: str) -> list[dict[str, Any]]:
        """Get list of storage on a node."""
        if not self._proxmox:
            return []
        try:
            return self._proxmox.nodes(node).storage.get()
        except Exception as err:
            LOGGER.error("Failed to get storage for node %s: %s", node, err)
            return []
            
    # Power Control Methods

    def start_vm(self, node: str, vm_id: int, vm_type: str = "qemu") -> bool:
        """Start a VM or Container."""
        if not self._proxmox:
            return False
        try:
            if vm_type == "lxc":
                self._proxmox.nodes(node).lxc(vm_id).status.start.post()
            else:
                self._proxmox.nodes(node).qemu(vm_id).status.start.post()
            return True
        except Exception as err:
            LOGGER.error("Failed to start %s %s on %s: %s", vm_type, vm_id, node, err)
            return False

    def stop_vm(self, node: str, vm_id: int, vm_type: str = "qemu") -> bool:
        """Stop (Kill) a VM or Container."""
        if not self._proxmox:
            return False
        try:
            if vm_type == "lxc":
                self._proxmox.nodes(node).lxc(vm_id).status.stop.post()
            else:
                self._proxmox.nodes(node).qemu(vm_id).status.stop.post()
            return True
        except Exception as err:
            LOGGER.error("Failed to stop %s %s on %s: %s", vm_type, vm_id, node, err)
            return False
            
    def shutdown_vm(self, node: str, vm_id: int, vm_type: str = "qemu") -> bool:
        """Gracefully shutdown a VM or Container."""
        if not self._proxmox:
            return False
        try:
            if vm_type == "lxc":
                self._proxmox.nodes(node).lxc(vm_id).status.shutdown.post()
            else:
                self._proxmox.nodes(node).qemu(vm_id).status.shutdown.post()
            return True
        except Exception as err:
            LOGGER.error("Failed to shutdown %s %s on %s: %s", vm_type, vm_id, node, err)
            return False

    def reboot_vm(self, node: str, vm_id: int, vm_type: str = "qemu") -> bool:
        """Reboot a VM or Container."""
        if not self._proxmox:
            return False
        try:
            if vm_type == "lxc":
                self._proxmox.nodes(node).lxc(vm_id).status.reboot.post()
            else:
                self._proxmox.nodes(node).qemu(vm_id).status.reboot.post()
            return True
        except Exception as err:
            LOGGER.error("Failed to reboot %s %s on %s: %s", vm_type, vm_id, node, err)
            return False
