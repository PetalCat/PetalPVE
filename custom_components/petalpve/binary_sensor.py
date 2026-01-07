"""Binary Sensor platform for Proxmox VE."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
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
    """Set up the binary sensor platform."""
    coordinator: ProxmoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ProxmoxBinarySensor] = []

    # Node Status
    for node_name, node_data in coordinator.data["nodes"].items():
        entities.append(
            ProxmoxBinarySensor(
                coordinator,
                node_name,
                "node",
                node_name,
                "online",
                "Status",
                BinarySensorDeviceClass.CONNECTIVITY,
            )
        )

    # VM Status
    for vm_id, vm_data in coordinator.data["vms"].items():
        entities.append(
            ProxmoxBinarySensor(
                coordinator,
                vm_data["name"],
                "qemu",
                str(vm_id),
                "status",
                "Status",
                BinarySensorDeviceClass.RUNNING,
            )
        )

    # LXC Status
    for vm_id, vm_data in coordinator.data["lxcs"].items():
        entities.append(
            ProxmoxBinarySensor(
                coordinator,
                vm_data["name"],
                "lxc",
                str(vm_id),
                "status",
                "Status",
                BinarySensorDeviceClass.RUNNING,
            )
        )
    
    async_add_entities(entities)

class ProxmoxBinarySensor(CoordinatorEntity[ProxmoxCoordinator], BinarySensorEntity):
    """Proxmox Binary Sensor."""

    def __init__(
        self,
        coordinator: ProxmoxCoordinator,
        name: str,
        resource_type: str,
        resource_id: str,
        key: str,
        suffix: str,
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._key = key
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"proxmox_{resource_type}_{resource_id}_{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        data = None
        if self._resource_type == "node":
            data = self.coordinator.data["nodes"].get(self._resource_id)
            if data:
                 # Nodes use 'online' 1 or 0 usually, or status 'online'
                status = data.get("status")
                return status == "online"
        
        elif self._resource_type == "qemu":
            data = self.coordinator.data["vms"].get(int(self._resource_id))
            if data:
                return data.get("status") == "running"
        
        elif self._resource_type == "lxc":
            data = self.coordinator.data["lxcs"].get(int(self._resource_id))
            if data:
                return data.get("status") == "running"
                
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        data = None
        if self._resource_type == "node":
            data = self.coordinator.data["nodes"].get(self._resource_id)
        elif self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(int(self._resource_id))
        elif self._resource_type == "lxc":
             data = self.coordinator.data["lxcs"].get(int(self._resource_id))
             
        if data:
            for k, v in data.items():
                if k in ["tags", "cpus", "name", "uptime", "pid"]:
                    attrs[k] = v
                if k == "maxmem":
                    attrs["memory_size"] = f"{round(v / 1073741824, 2)} GB"
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        if self._resource_type == "node":
            return DeviceInfo(
                identifiers={(DOMAIN, self._resource_id)},
                name=self._resource_id,
                manufacturer="Proxmox",
                model="Proxmox VE Node",
                configuration_url=f"https://{self.coordinator.client._host}:{self.coordinator.client._port}",
            )
        elif self._resource_type in ("qemu", "lxc"):
            # Get VM data to find the node it's on for "via_device"
            data = None
            if self._resource_type == "qemu":
                data = self.coordinator.data["vms"].get(int(self._resource_id))
            else:
                data = self.coordinator.data["lxcs"].get(int(self._resource_id))
            
            node = data.get("node") if data else None
            
            return DeviceInfo(
                identifiers={(DOMAIN, self._resource_id)},
                name=self._attr_name.replace(f" {self._key.capitalize()}", "").replace(f" {self._key}", ""), # Try to get back to just the VM Name
                manufacturer="Proxmox",
                model="Virtual Machine" if self._resource_type == "qemu" else "LXC Container",
                via_device=(DOMAIN, node) if node else None,
            )
        return None
