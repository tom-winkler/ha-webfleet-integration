"""Support for WEBFLEET platform."""
import logging

from wfconnect.wfconnect import WfConnect
from typing import Optional
import voluptuous as vol

from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA,
    DeviceScanner,
    SOURCE_TYPE_GPS,
)

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import (
    DOMAIN as DEVICE_TRACKER_DOMAIN,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify


from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.const import (
    ATTR_ICON,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_API_KEY,
    CONF_AT,
    CONF_DEVICES,
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
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


async def async_setup_entry(hass, entry, async_add_devices):
    _LOGGER.debug("async_setup_entry %s", entry)


def setup_scanner(hass, config, see, discovery_info=None):
    """Set up WEBFLEET tracker"""
    _LOGGER.debug("Connecting to webfleet with config %s", config)
    scanner = WebfleetDeviceScanner(hass, config, see)
    track_utc_time_change(
        hass,
        scanner.scan_devices,
        second=range(0, 60, 30),
    )
    return True


class WebfleetDeviceScanner(DeviceScanner):
    def __init__(self, hass, config, see) -> None:
        """Initialize WEBFLEET connection"""
        _LOGGER.debug("Scanner for WEBFLEET devices")
        if self.parseConfigAndConnect(config):
            _LOGGER.debug("Connection established")
        else:
            _LOGGER.debug("Cannot establish connection to WEBFLEET, missing config.")
        self.hass = hass
        self.vehicles = []
        self.vehicle_ids = []
        self.see = see
        self._update_info()

    def parseConfigAndConnect(self, config):
        try:
            self.url = config.get(CONF_URL)
            self.username = config.get(CONF_USERNAME)
            self.account = config.get(CONF_AT)
            self.password = config.get(CONF_PASSWORD)
            self.group = config.get(CONF_DEVICES)
            self.apikey = config.get(CONF_API_KEY)
            self.api = WfConnect(self.url)
            self.api.setAuthentication(
                self.account, self.username, self.password, self.apikey
            )
        except Exception:
            _LOGGER.warning("Error parsing config", exc_info=True)
            return False
        return True

    def scan_devices(self, now=None) -> None:
        """Scan for new devices and return a list with found device IDs."""
        self._update_info(now)

    def get_attached_devices(self):
        _LOGGER.debug("Send attached devices %s", self.vehicles)
        return self.vehicles

    def _update_info(self, now=None) -> None:
        """Update the device info."""
        _LOGGER.debug("Scanning for devices %s", now)

        # Update self.devices to collect new devices added
        # to the users account.
        try:
            vehicles = self.api.showObjectReportExtern(objectgroupname=self.group)
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
                    entity = WebfleetEntity(vehicle, entity_id)
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

            _LOGGER.debug("Reporting %s vehicle(s).", len(self.vehicles))
            for vehicle in self.vehicles:
                try:
                    self.see(
                        dev_id=vehicle.name,
                        gps=(vehicle.latitude, vehicle.longitude),
                        location_name=vehicle.location_name,
                        attributes=vehicle.extras,
                        gps_accuracy=5,
                        host_name=vehicle.device_name,
                        icon=vehicle.icon,
                    )
                    _LOGGER.debug(f"Send: {vehicle.name}, {vehicle.extras}")
                except Exception:
                    _LOGGER.warning("Could not update vehicle", exc_info=True)

        except Exception:
            _LOGGER.warning("Update not successful:", exc_info=True)

    def get_device(self, device: str) -> str:
        for vehicle in self.vehicles:
            if vehicle.device_id == device:
                _LOGGER.debug("get_device for " + device + " " + vehicle.device_name)
                return vehicle
        return None


class WebfleetEntity(TrackerEntity):
    """Represent a tracked device."""

    def __init__(self, vehicle, entity_id):
        self._vehicle_data = vehicle
        self._entity_id = entity_id

    def update(self, vehicle_data):
        self._vehicle_data = vehicle_data

    @property
    def name(self) -> Optional[str]:
        return slugify(self._entity_id)

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
    def device_name(self) -> str:
        return self._vehicle_data[OBJECTNAME]

    @property
    def device_id(self) -> str:
        return self._vehicle_data[OBJECTUID]

    @property
    def latitude(self) -> float:
        lat_mdeg = self._vehicle_data["latitude_mdeg"]
        if not isinstance(lat_mdeg, int):
            return None
        return lat_mdeg / 1000000

    @property
    def longitude(self) -> float:
        lon_mdeg = self._vehicle_data["longitude_mdeg"]
        if not isinstance(lon_mdeg, int):
            return None
        return lon_mdeg / 1000000

    @property
    def extras(self):
        """Overwriting lat lon necessary to avoid ha issues"""
        self._vehicle_data["latitude"] = self.latitude
        self._vehicle_data["longitude"] = self.longitude
        return self._vehicle_data
