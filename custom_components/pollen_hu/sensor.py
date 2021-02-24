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

CONF_ATTRIBUTION = "Data provided by antsz.hu"
CONF_NAME = 'name'

DEFAULT_NAME = 'Pollen HU'
DEFAULT_ICON = 'mdi:blur'

SCAN_INTERVAL = timedelta(hours=3)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)

    session = async_get_clientsession(hass)

    async_add_devices(
        [PollenHUSensor(hass, name )],update_before_add=True)

async def async_get_pdata(self):
    pjson = {}

    session = async_get_clientsession(self._hass)

    url = 'https://efop180.antsz.hu/polleninformaciok/'
    async with session.get(url) as response:
        rsp1 = await response.text()

    rsp = rsp1.replace("\n","").replace("\r","")

    p0 = re.findall(r"contentpagetitle\">.*</a></div><div class=\"ertek\">\d+",rsp)
    if len(p0) > 0:
        p1 = p0[0].replace(" </a>","</a>") \
             .replace("contentpagetitle\">",">\"name\":\"") \
             .replace("ertek\">",">\"value\":\"")
        clean = re.compile('<.*?>')
        p2 = re.sub(clean, ' ', p1)
        p3 = re.sub(r"([0-9])",r"\1 ",p2) \
             .replace("contentpagetitle\">", '') \
             .replace("  ","") \
             .replace(" \"","\",\"") \
             .replace("\",\"name","\"},{\"name") \
             .replace(" ","") \
             .replace(">", "{\"pollens\":[{") + "\"}]}"
        pjson = json.loads(p3)
    return pjson

class PollenHUSensor(Entity):

    def __init__(self, hass, name):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._state = None
        self._pdata = []
        self._icon = DEFAULT_ICON

    @property
    def device_state_attributes(self):
        attr = {}
        dominant_value = 0

        if 'pollens' in self._pdata:
            attr["pollens"] = self._pdata.get('pollens')

            for item in self._pdata['pollens']:
                val = item.get('value')
                if int(val) > dominant_value:
                    attr["dominant_pollen_value"] = val
                    attr["dominant_pollen"] = item.get('name')
                    dominant_value = int(val)

        attr["provider"] = CONF_ATTRIBUTION
        return attr

    @asyncio.coroutine
    async def async_update(self):
        dominant_value = 0

        pdata = await async_get_pdata(self)

        self._pdata = pdata
        if 'pollens' in self._pdata:
            for item in self._pdata['pollens']:
                val = item.get('value')
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
