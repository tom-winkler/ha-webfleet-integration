from asyncio import exceptions
import logging
from typing import Any
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN as WF_DOMAIN
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_URL,
    CONF_API_KEY,
    CONF_AT,
    CONF_DEVICES,
)

from wfconnect.wfconnect import WfConnect

_LOGGER = logging.getLogger(__name__)


class WebfleetConfigFlow(config_entries.ConfigFlow, domain=WF_DOMAIN):

    VERSION = 1
    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Optional(
                CONF_URL,
                default="https://csv.webfleet.com/extern",
                description="WEBFLEET.connect url to use",
            ): cv.string,
            vol.Required(CONF_AT, description={"suggested_value": ""}): cv.string,
            vol.Required(
                CONF_USERNAME,
                description={
                    "label": "The username to be used in webfleet",
                    "suggested_value": "",
                },
            ): cv.string,
            vol.Required(
                CONF_PASSWORD,
                description={"label": "password"},
            ): cv.string,
            vol.Optional(
                CONF_API_KEY,
                description={"suggested_value": "like 323232332"},
            ): cv.string,
            vol.Optional(
                CONF_DEVICES,
                description="Grooupnmae or objec name to import.",
            ): cv.string,
        }
    )

    def __init__(self):
        """Initialize the config flow."""
        self.username = None
        self.password = None
        self.account = None
        self.url = None
        self.api_key = None
        self.object_name = None
        self.config_schema = self.CONFIG_SCHEMA

    async def connect(self):
        try:
            test_api = WfConnect(self.url)
            test_api.setAuthentication(
                account=self.account,
                username=self.username,
                password=self.password,
                apikey=self.api_key,
            )
            return True
        except Exception:
            _LOGGER.warning("Error parsing config", exc_info=True)
            raise InvalidAccount
        return False

    def validate_user_input(self, user_input=None):
        return True

    async def async_step_user(self, user_input=None):
        """Handle the user configuration step."""
        errors = {}
        if user_input is not None:
            # Validate the user input
            if not self.validate_user_input(user_input):
                errors[CONF_USERNAME] = "Invalid username"
                errors[CONF_PASSWORD] = "Invalid password"
                errors[CONF_URL] = "Invalid URL"
                return self.async_show_form(
                    step_id="user", data_schema=self.config_schema, errors=errors
                )

            # Save the user input
            self.username = user_input[CONF_USERNAME]
            self.password = user_input[CONF_PASSWORD]
            self.url = user_input[CONF_URL]
            self.api_key = user_input.get(CONF_API_KEY)
            self.object_name = user_input.get(CONF_DEVICES)

            # Attempt to connect to the service using the provided credentials
            if not await self.connect():
                errors[CONF_URL] = "Unable to connect to service"
                return self.async_show_form(
                    step_id="user", data_schema=self.config_schema, errors=errors
                )

            # Save the configuration
            return self.async_create_entry(title=self.username, data=user_input)

        return self.async_show_form(step_id="user", data_schema=self.config_schema)


class InvalidAccount(HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
