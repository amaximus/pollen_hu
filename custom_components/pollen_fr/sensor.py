import asyncio
import json
import logging
import re
import voluptuous as vol
import aiohttp
from datetime import timedelta

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import async_load_platform

REQUIREMENTS = [ ]

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Data provided by pollens.fr"
CONF_NAME = 'name'

DEFAULT_NAME = 'Pollen FR'
DEFAULT_ICON = 'mdi:blur'

SCAN_INTERVAL = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)

    async_add_devices(
        [PollenFRSensor(hass, name )],update_before_add=True)

async def async_get_pdata(self):
    pjson = {}

    url = 'https://www.pollens.fr/risks/thea/counties/13'
    async with self._session.get(url) as response:
        rsp = await response.text()
        pjson = json.loads(rsp)
    return pjson

class PollenFRSensor(Entity):

    def __init__(self, hass, name):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._state = None
        self._pdata = []
        self._icon = DEFAULT_ICON
        self._session = async_get_clientsession(hass)

    @property
    def device_state_attributes(self):
        attr = {}
        dominant_value = 0

        if 'risks' in self._pdata:
            attr["risks"] = self._pdata.get('risks')

            for item in self._pdata['risks']:
                val = item.get('level')
                if int(val) > dominant_value:
                    attr["dominant_pollen_value"] = int(val)
                    attr["dominant_pollen"] = item.get('pollenName')
                    dominant_value = int(val)

        attr["provider"] = CONF_ATTRIBUTION
        return attr

    @asyncio.coroutine
    async def async_update(self):
        dominant_value = 0

        pdata = await async_get_pdata(self)

        self._pdata = pdata
        if 'risks' in self._pdata:
            for item in self._pdata['risks']:
                val = item.get('level')
                if int(val) > dominant_value:
                    dominant_value = int(val)

        self._state = dominant_value
        return self._state

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return DEFAULT_ICON
