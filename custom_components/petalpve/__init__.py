"""The PetalPVE integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant

from .api import ProxmoxClient
from .const import CONF_REALM, DOMAIN, LOGGER
from .coordinator import ProxmoxCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.BUTTON,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxmox VE from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})

    client = ProxmoxClient(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_PORT],
        entry.data.get(CONF_REALM, "pam"),
        entry.data.get(CONF_VERIFY_SSL, True),
    )
    
    # Verify connection again (optional, but good practice if startup is delayed)
    if not await hass.async_add_executor_job(client.connect):
        LOGGER.error("Could not connect to Proxmox VE at startup")
        return False

    coordinator = ProxmoxCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
