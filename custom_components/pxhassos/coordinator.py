"""DataUpdateCoordinator for Proxmox VE."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ProxmoxClient
from .const import DOMAIN, LOGGER, SCAN_INTERVAL_FAST, SCAN_INTERVAL_SLOW

class ProxmoxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Proxmox VE data."""

    def __init__(self, hass: HomeAssistant, client: ProxmoxClient) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_FAST),
        )
        self.client = client
        self.data: dict[str, Any] = {
            "nodes": {},
            "vms": {},
            "lxcs": {},
            "storage": {},
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # We run the API calls in the executor
            # Fetch nodes first
            nodes = await self.hass.async_add_executor_job(self.client.get_nodes)
            
            new_data = {
                "nodes": {},
                "vms": {},
                "lxcs": {},
                "storage": {},
            }
            
            for node in nodes:
                node_name = node["node"]
                new_data["nodes"][node_name] = node
                
                # Enrich node data with status if needed, but get_nodes returns basic stats
                # Maybe fetch detailed node status?
                # node_status = await self.hass.async_add_executor_job(self.client.get_node_status, node_name)
                
                # Fetch VMs
                vms = await self.hass.async_add_executor_job(self.client.get_vms, node_name)
                for vm in vms:
                    vm["node"] = node_name
                    new_data["vms"][vm["vmid"]] = vm
                    
                # Fetch LXCs
                lxcs = await self.hass.async_add_executor_job(self.client.get_lxcs, node_name)
                for lxc in lxcs:
                    lxc["node"] = node_name
                    new_data["lxcs"][lxc["vmid"]] = lxc

                # Fetch Storage
                storage = await self.hass.async_add_executor_job(self.client.get_storage, node_name)
                for store in storage:
                     # Unique storage ID: node_id + storage_id
                    store_id = f"{node_name}_{store['storage']}"
                    store["node"] = node_name
                    new_data["storage"][store_id] = store

            return new_data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
