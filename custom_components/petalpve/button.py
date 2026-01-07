"""Button platform for Proxmox VE."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: ProxmoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ProxmoxButton] = []

    # VM Buttons
    for vm_id, vm_data in coordinator.data["vms"].items():
        name = vm_data["name"]
        entities.extend([
            ProxmoxButton(coordinator, name, "qemu", str(vm_id), "start", "Start", "mdi:play", "start_vm"),
            ProxmoxButton(coordinator, name, "qemu", str(vm_id), "stop", "Stop", "mdi:stop", "stop_vm"),
            ProxmoxButton(coordinator, name, "qemu", str(vm_id), "shutdown", "Shutdown", "mdi:power", "shutdown_vm"),
            ProxmoxButton(coordinator, name, "qemu", str(vm_id), "reboot", "Reboot", "mdi:restart", "reboot_vm"),
        ])

    # LXC Buttons
    for vm_id, vm_data in coordinator.data["lxcs"].items():
        name = vm_data["name"]
        entities.extend([
            ProxmoxButton(coordinator, name, "lxc", str(vm_id), "start", "Start", "mdi:play", "start_vm"),
            ProxmoxButton(coordinator, name, "lxc", str(vm_id), "stop", "Stop", "mdi:stop", "stop_vm"),
            ProxmoxButton(coordinator, name, "lxc", str(vm_id), "shutdown", "Shutdown", "mdi:power", "shutdown_vm"),
            ProxmoxButton(coordinator, name, "lxc", str(vm_id), "reboot", "Reboot", "mdi:restart", "reboot_vm"),
        ])

    async_add_entities(entities)

class ProxmoxButton(CoordinatorEntity[ProxmoxCoordinator], ButtonEntity):
    """Proxmox Button."""

    def __init__(
        self,
        coordinator: ProxmoxCoordinator,
        name: str,
        resource_type: str,
        resource_id: str,
        key: str,
        suffix: str,
        icon: str,
        method_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._key = key
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"proxmox_{resource_type}_{resource_id}_{key}"
        self._attr_icon = icon
        self._method_name = method_name
        self._vm_id = int(resource_id)

    async def async_press(self) -> None:
        """Press the button."""
        node = None
        # Find the node for this VM/LXC
        if self._resource_type == "qemu":
             data = self.coordinator.data["vms"].get(self._vm_id)
        elif self._resource_type == "lxc":
             data = self.coordinator.data["lxcs"].get(self._vm_id)
             
        if not data:
             return

        node = data.get("node") # API returns 'node' in the list view? It usually does not on single node view, but cluster view yes.
        # Wait, the get_vms calls were per node. The coordinator stores them flat by ID? 
        # If IDs are unique across cluster? Yes usually. 
        # But wait, our coordinator structure is:
        # vms[vmid] = vm_data
        # We need to make sure we store the node name in the vm_data in the coordinator!
        # Checking coordinator.py...
        # "new_data["vms"][vm["vmid"]] = vm" -> api.get_vms() returns list of dicts.
        # proxmoxer nodes(node).qemu.get() returns objects. Does it include 'node'?
        # Usually it does NOT include the node name if queried from /nodes/{node}/qemu
        # It DOES if queried from /cluster/resources but that is different endpoint.
        # We queried per node. So we need to inject the node name in coordinator.py.
        
        # Let's double check coordinator.py logic or rely on injection.
        # I better fix coordinator.py to inject 'node' into the vm/lxc data.
        
        # Assuming we fix coordinator.py, here is the call:
        method = getattr(self.coordinator.client, self._method_name)
        await self.hass.async_add_executor_job(
            method,
            node,
            self._vm_id,
            self._resource_type
        )
        # Request update
        await self.coordinator.async_request_refresh()
