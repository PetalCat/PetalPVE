"""Switch platform for PetalPVE."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: ProxmoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ProxmoxSwitch] = []

    # VM Switches
    for vm_id, vm_data in coordinator.data["vms"].items():
        name = vm_data["name"]
        entities.append(
            ProxmoxSwitch(coordinator, name, "qemu", str(vm_id), "onboot", "Start on Boot", "mdi:bootstrap")
        )

    # LXC Switches
    for vm_id, vm_data in coordinator.data["lxcs"].items():
        name = vm_data["name"]
        entities.append(
            ProxmoxSwitch(coordinator, name, "lxc", str(vm_id), "onboot", "Start on Boot", "mdi:bootstrap")
        )

    async_add_entities(entities)

class ProxmoxSwitch(CoordinatorEntity[ProxmoxCoordinator], SwitchEntity):
    """Proxmox Switch."""

    def __init__(
        self,
        coordinator: ProxmoxCoordinator,
        name: str,
        resource_type: str,
        resource_id: str,
        key: str,
        suffix: str,
        icon: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._key = key
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"proxmox_{resource_type}_{resource_id}_{key}"
        self._attr_icon = icon
        self._vm_id = int(resource_id)
        # We need to fetch initial state. 
        # CAUTION: The standard 'nodes' list call DOES NOT return 'onboot'.
        # We need to fetch it from config. 
        # Doing this per entity per update is expensive.
        # But we can try to fetch it on init or just lazily? 
        # Better: Add 'onboot' to the coordinator data?
        # That requires N calls in coordinator.py. Not good for performance.
        # Alternative: Fetch on demand? No, HA needs state.
        # Compromise: We will only update this switch state if the coordinator refreshes?
        # Actually, let's assume 'onboot' is stable and we can fetch it once?
        # No, user changes it on PVE side.
        # Let's add a "slow" refresh to coordinator for config data? 
        # Or just trust that users won't have 1000 VMs and we can fetch it?
        # Let's keep it simple for now and maybe fetch it in coordinator if users have few VMs.
        # Actually, let's look at the 'nodes' response again.
        # It does NOT have onboot.
        # We have to query qemu/{vmid}/config.
        
        # DECISION: To avoid spamming API, we will just default to OFF or Unknown until toggled?
        # No, that's bad UX.
        # We will add a 'config' fetching loop to coordinator but run it rarely?
        # Or just fetch it here in `async_update`?
        self._is_on = False

    async def async_update(self) -> None:
        """Update the entity."""
        # This is called by HA.
        # We should probably hook into coordinator, but since coordinator doesn't have this data...
        # We can implement a separate update method.
        # But wait, CoordinatorEntity doesn't use async_update usually, it uses handle_update.
        # If we define async_update, HA will call it based on scan_interval (default 30s).
        
        # Let's fetch the config.
        node = None
        if self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(self._vm_id)
        else:
             data = self.coordinator.data["lxcs"].get(self._vm_id)
             
        if data:
            node = data.get("node")
            
        if node:
             config = await self.hass.async_add_executor_job(
                 self.coordinator.client.get_vm_config, node, self._vm_id, self._resource_type
             )
             if config:
                 self._is_on = bool(config.get("onboot", 0))

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        node = None
        if self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(self._vm_id)
        else:
             data = self.coordinator.data["lxcs"].get(self._vm_id)
        
        if not data: return
        node = data.get("node")

        if await self.hass.async_add_executor_job(
            self.coordinator.client.set_vm_config, node, self._vm_id, self._resource_type, onboot=1
        ):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        node = None
        if self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(self._vm_id)
        else:
             data = self.coordinator.data["lxcs"].get(self._vm_id)
             
        if not data: return
        node = data.get("node")

        if await self.hass.async_add_executor_job(
            self.coordinator.client.set_vm_config, node, self._vm_id, self._resource_type, onboot=0
        ):
            self._is_on = False
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._resource_type in ("qemu", "lxc"):
             # Get VM data
            data = None
            if self._resource_type == "qemu":
                data = self.coordinator.data["vms"].get(self._vm_id)
            else:
                data = self.coordinator.data["lxcs"].get(self._vm_id)
            
            node = data.get("node") if data else None
            device_name = data.get("name", "Unknown") if data else "Unknown"

            return DeviceInfo(
                identifiers={(DOMAIN, str(self._vm_id))},
                name=device_name,
                manufacturer="Proxmox",
                model="Virtual Machine" if self._resource_type == "qemu" else "LXC Container",
                via_device=(DOMAIN, node) if node else None,
            )
        return None
