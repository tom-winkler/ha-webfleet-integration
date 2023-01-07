"""Support for WEBFLEET platform."""
import logging

from datetime import timedelta
import async_timeout

from typing import Optional
import voluptuous as vol

from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA,
    SOURCE_TYPE_GPS,
)
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_API_KEY,
    CONF_AT,
    CONF_DEVICES,
)
from . import DOMAIN as WF_DOMAIN

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_FORMAT = "webfleet" + ".{}"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_URL, default="https://csv.webfleet.com/extern"): cv.url,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_API_KEY): cv.string,
        vol.Required(CONF_AT): cv.string,
        vol.Optional(CONF_DEVICES): cv.string,
    }
)

OBJECTUID = "objectuid"
POSTEXT = "postext"
OBJECTNAME = "objectname"

ICON_CAR = "mdi:car"
ICON_BUS = "mdi:bus"
ICON_TRUCK = "mdi:truck"


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("async_setup_entry %s", entry)
    config = entry.data

    webfleet_api = hass.data[WF_DOMAIN][entry.entry_id]

    webfleet_api.setAuthentication(
        config.get(CONF_AT),
        config.get(CONF_USERNAME),
        config.get(CONF_PASSWORD),
        config.get(CONF_API_KEY),
    )
    group = config.get(CONF_DEVICES)
    coordinator = WebfleetCoordinator(hass, webfleet_api, group)

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady

    async_add_entities(
        WebfleetEntity(
            coordinator,
            coordinator.data[idx].entity_id,
            coordinator.data[idx].vehicle_data,
        )
        for idx, ent in enumerate(coordinator.data)
    )


class WebfleetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, webfleet_api, group):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Webfleet",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self.api = webfleet_api
        self.hass = hass
        self.vehicle_ids = []
        self.group = group
        self.vehicles = []

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await self.fetch_data()

        except Exception as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err

    #        except ApiError as err:
    #            raise UpdateFailed(f"Error communicating with API: {err}")

    async def get_vehicle_details_api(self):
        def blocking_call():
            return self.api.showObjectReportExtern(objectgroupname=self.group)

        return await self.hass.async_add_executor_job(blocking_call)

    async def fetch_data(self):
        """Update the device info."""
        _LOGGER.debug("Scanning for devices")

        # Update self.devices to collect new devices added
        # to the users account.
        try:
            vehicles = await self.get_vehicle_details_api()
            discovered_vehicle_ids = []
            # newvehicle_ids = []
            for vehicle in vehicles:
                object_uid = vehicle[OBJECTUID]
                discovered_vehicle_ids.append(object_uid)
                existing_vehicle = self.get_device(object_uid)
                if existing_vehicle is None:
                    entity_id = async_generate_entity_id(
                        ENTITY_ID_FORMAT, object_uid, self.vehicle_ids, self.hass
                    )
                    entity = WebfleetEntity(self, entity_id, vehicle)
                    self.vehicles.append(entity)
                else:
                    _LOGGER.debug(
                        "Vehicle already discovered, updating: %s", object_uid
                    )
                    existing_vehicle.update(vehicle)

            # Add new or remove vehicles no longer present
            self.vehicles = [
                vehicle
                for vehicle in self.vehicles
                if vehicle.device_id in discovered_vehicle_ids
            ]
            self.vehicle_ids = [vehicle.device_id for vehicle in self.vehicles]
            return self.vehicles

        except Exception:
            _LOGGER.warning("Update not successful:", exc_info=True)

    def get_device(self, device: str) -> str:
        for vehicle in self.vehicles:
            if vehicle.device_id == device:
                _LOGGER.debug("get_device for " + device + " " + vehicle.name)
                return vehicle
        return None


class WebfleetEntity(CoordinatorEntity, TrackerEntity):
    """Represent a tracked device."""

    def __init__(self, coordinator, entity_id, vehicle_data):
        super().__init__(coordinator)
        self.vehicle_data = (
            vehicle_data  # TODO: Looks like the update call cnanot initate the entity
        )
        self.entity_id = entity_id

    @callback
    def _handle_coordinator_update(self) -> None:

        self.async_write_ha_state()

    def update(self, vehicle_data):
        self.vehicle_data = vehicle_data

    @property
    def name(self) -> Optional[str]:
        return self.vehicle_data[OBJECTNAME]
        # return slugify(self._entity_id)

    @property
    def location_name(self) -> str:
        """Not returning a location to enable HA matching Zones based on GPS"""
        return None

    @property
    def source_type(self):
        return SOURCE_TYPE_GPS

    @property
    def icon(self) -> Optional[str]:
        return ICON_CAR

    @property
    def device_id(self) -> str:
        return self.vehicle_data[OBJECTUID]

    @property
    def latitude(self) -> float:
        if self.vehicle_data is None:
            return None
        lat_mdeg = self.vehicle_data["latitude_mdeg"]
        if not isinstance(lat_mdeg, int):
            return None
        return lat_mdeg / 1000000

    @property
    def longitude(self) -> float:
        lon_mdeg = self.vehicle_data["longitude_mdeg"]
        if not isinstance(lon_mdeg, int):
            return None
        return lon_mdeg / 1000000

    @property
    def extra_state_attributes(self):
        """Overwriting lat lon necessary to avoid ha issues"""
        self.vehicle_data["latitude"] = self.latitude
        self.vehicle_data["longitude"] = self.longitude
        return self.vehicle_data
