"""Sensor platform for Proxmox VE."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTime
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
    """Set up the sensor platform."""
    coordinator: ProxmoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ProxmoxSensor] = []

    # Node Sensors
    for node_name, node_data in coordinator.data["nodes"].items():
        # CPU
        entities.append(ProxmoxSensor(
            coordinator, node_name, "node", node_name, "cpu_usage", "CPU Usage", 
            PERCENTAGE, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("cpu", 0) * 100, 2) if x else 0
        ))
        # RAM Usage
        entities.append(ProxmoxSensor(
            coordinator, node_name, "node", node_name, "memory_usage", "Memory Usage", 
            PERCENTAGE, None, SensorStateClass.MEASUREMENT,
            lambda x: round((x.get("mem", 0) / x.get("maxmem", 1)) * 100, 2) if x and x.get("maxmem", 0) > 0 else 0
        ))
        # Total Memory
        entities.append(ProxmoxSensor(
            coordinator, node_name, "node", node_name, "memory_total", "Memory Total", 
            UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL,
            lambda x: round(x.get("maxmem", 0) / 1073741824, 2) if x else 0
        ))
         # Uptime
        entities.append(ProxmoxSensor(
            coordinator, node_name, "node", node_name, "uptime", "Uptime", 
            UnitOfTime.SECONDS, SensorDeviceClass.DURATION, SensorStateClass.TOTAL,
            lambda x: x.get("uptime", 0) if x else 0
        ))


    # VM Sensors
    for vm_id, vm_data in coordinator.data["vms"].items():
        name = vm_data["name"]
        # CPU
        entities.append(ProxmoxSensor(
            coordinator, name, "qemu", str(vm_id), "cpu", "CPU", 
            PERCENTAGE, None, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("cpu", 0) * 100, 2) if x else 0
        ))
        # Mem
        entities.append(ProxmoxSensor(
            coordinator, name, "qemu", str(vm_id), "memory", "Memory", 
            UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("mem", 0) / 1073741824, 2) if x else 0
        ))
        
    # LXC Sensors
    for vm_id, vm_data in coordinator.data["lxcs"].items():
        name = vm_data["name"]
        # CPU
        entities.append(ProxmoxSensor(
            coordinator, name, "lxc", str(vm_id), "cpu", "CPU", 
            PERCENTAGE, None, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("cpu", 0) * 100, 2) if x else 0
        ))
        # Mem
        entities.append(ProxmoxSensor(
            coordinator, name, "lxc", str(vm_id), "memory", "Memory", 
            UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("mem", 0) / 1073741824, 2) if x else 0
        ))

    # Storage Sensors
    for store_id, store_data in coordinator.data["storage"].items():
        # Store ID is node_storage_name. Let's use a cleaner name if possible or just the combine
        # store_data has 'node' and 'storage' keys
        name = f"{store_data['node']} {store_data['storage']}"
        
        entities.append(ProxmoxSensor(
            coordinator, name, "storage", store_id, "used", "Used", 
            UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT,
            lambda x: round(x.get("used", 0) / 1073741824, 2) if x else 0
        ))
        entities.append(ProxmoxSensor(
            coordinator, name, "storage", store_id, "total", "Total", 
            UnitOfInformation.GIGABYTES, SensorDeviceClass.DATA_SIZE, SensorStateClass.TOTAL,
            lambda x: round(x.get("total", 0) / 1073741824, 2) if x else 0
        ))
         # Usage %
        entities.append(ProxmoxSensor(
            coordinator, name, "storage", store_id, "usage_pct", "Usage %", 
            PERCENTAGE, None, SensorStateClass.MEASUREMENT,
            lambda x: round((x.get("used", 0) / x.get("total", 1)) * 100, 1) if x and x.get("total", 0) > 0 else 0
        ))
    
    async_add_entities(entities)


class ProxmoxSensor(CoordinatorEntity[ProxmoxCoordinator], SensorEntity):
    """Proxmox Sensor."""

    def __init__(
        self,
        coordinator: ProxmoxCoordinator,
        name: str,
        resource_type: str,
        resource_id: str,
        key: str,
        suffix: str,
        native_unit_of_measurement: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        value_fn: callable,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._key = key
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"proxmox_{resource_type}_{resource_id}_{key}"
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._value_fn = value_fn

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        data = None
        if self._resource_type == "node":
            data = self.coordinator.data["nodes"].get(self._resource_id)
        elif self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(int(self._resource_id))
        elif self._resource_type == "lxc":
             data = self.coordinator.data["lxcs"].get(int(self._resource_id))
        elif self._resource_type == "storage":
             data = self.coordinator.data["storage"].get(self._resource_id)
             
        if data:
            return self._value_fn(data)
        return None

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
            
            # For sensors, self._attr_name is "Name Suffix". We want just "Name" for the device name.
            # But wait, device name should be the VM name.
            # We constructed _attr_name as f"{name} {suffix}" in init.
            # So the device name should just be 'name' passed to init? 
            # We don't store 'name' in self.
            # Let's fallback to looking up name from coordinator or just using a cleaner approach.
            
            device_name = "Unknown VM"
            if data:
                device_name = data.get("name", "Unknown")

            return DeviceInfo(
                identifiers={(DOMAIN, self._resource_id)},
                name=device_name,
                manufacturer="Proxmox",
                model="Virtual Machine" if self._resource_type == "qemu" else "LXC Container",
                via_device=(DOMAIN, node) if node else None,
            )
        elif self._resource_type == "storage":
            # self._resource_id is "node_storage"
            # We want to link this to the node device
            data = self.coordinator.data["storage"].get(self._resource_id)
            node = data.get("node") if data else None
            return DeviceInfo(
                identifiers={(DOMAIN, self._resource_id)},
                name=f"Storage {data.get('storage')}" if data else "Storage",
                manufacturer="Proxmox",
                model="ZFS/LVM Storage",
                via_device=(DOMAIN, node) if node else None,
            )
        return None
