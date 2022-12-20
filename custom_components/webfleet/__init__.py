"""The webfleet integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


from wfconnect.wfconnect import WfConnect

from .const import DOMAIN

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_API_KEY,
    CONF_AT,
    CONF_DEVICES,
)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up webfleet from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for syour platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
    config = entry.data
    hass.data[DOMAIN][entry.entry_id] = WfConnect(config.get(CONF_URL))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
