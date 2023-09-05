import aiohttp
import json
import logging
import re
import voluptuous as vol
from datetime import datetime
from datetime import timedelta

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import async_load_platform

REQUIREMENTS = [ ]

_LOGGER = logging.getLogger(__name__)

CONF_ALLDOMINANT = 'all_dominant'
CONF_ATTRIBUTION = "Data provided by antsz.hu"
CONF_NAME = 'name'
CONF_POLLENS = 'pollens'
CONF_SSL = 'ssl'

DEFAULT_ALLDOMINANT = False
DEFAULT_ICON = 'mdi:blur'
DEFAULT_NAME = 'Pollen HU'
DEFAULT_SSL = True

SCAN_INTERVAL = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_ALLDOMINANT, default=DEFAULT_ALLDOMINANT): cv.boolean,
    vol.Optional(CONF_POLLENS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
})

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    alldominant = config.get(CONF_ALLDOMINANT)
    pollens = config.get(CONF_POLLENS)
    ssl = config.get(CONF_SSL)

    async_add_devices(
        [PollenHUSensor(hass, name, alldominant, pollens, ssl)],update_before_add=True)

async def async_get_pdata(self):
    pjson = {"pollens": []}
    pjson1 = {}
    successful_poll = "true"

    url = 'https://efop180.antsz.hu/polleninformaciok/'
    try:
        async with self._session.get(url) as response:
            rsp1 = await response.text()
        if response.status != 200:
            rsp1 = ""
            successful_poll = "false"
    except(aiohttp.client_exceptions.ClientConnectorError):
            rsp1 = ""
            successful_poll = "false"

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
             .replace(">", "{\"pollens\":[{") + "\"}]}"
        pjson1 = json.loads(p3)
        if len(self._pollens) != 0:
            i = 0
            for item in pjson1['pollens']:
                if item.get('name') not in self._pollens:
                    continue
                else:
                    pjson['pollens'].append({"name": item.get('name'),"value": item.get('value')})
                    i += 1;
        else:
            pjson = pjson1
    pjson['successful_poll'] = successful_poll
    return pjson

class PollenHUSensor(Entity):

    def __init__(self, hass, name, alldominant, pollens, ssl):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._alldominant = alldominant
        self._state = None
        self._last_poll = ""
        self._pdata = []
        self._pollens = pollens
        self._ssl = ssl
        self._successful_poll = "true"
        self._icon = DEFAULT_ICON
        self._session = async_get_clientsession(hass, ssl)

    @property
    def extra_state_attributes(self):
        attr = {}
        dominant_value = -1

        if 'pollens' in self._pdata:
            attr["pollens"] = self._pdata.get('pollens')

            for item in self._pdata['pollens']:
                val = item.get('value')
                if int(val) > dominant_value:
                    attr["dominant_pollen_value"] = int(val)
                    attr["dominant_pollen"] = item.get('name')
                    dominant_value = int(val)
                    attr["dominant_pollens_nr"] = 1
                elif int(val) == dominant_value and self._alldominant:
                    if 'dominant_pollen' in attr:
                        attr["dominant_pollen"] = attr["dominant_pollen"] + "|" + item.get('name')
                        attr["dominant_pollens_nr"] = attr["dominant_pollens_nr"] + 1
                    else:
                        attr["dominant_pollen"] = item.get('name')
                        attr["dominant_pollens_nr"] = 1
                    attr["dominant_pollen_value"] = int(val)
                    dominant_value = int(val)

        attr["provider"] = CONF_ATTRIBUTION
        attr["last_poll"] = self._last_poll
        attr["successful_poll"] = self._successful_poll
        return attr

    async def async_update(self):
        dominant_value = 0

        self._pdata = await async_get_pdata(self)

        if 'pollens' in self._pdata:
            for item in self._pdata['pollens']:
                val = item.get('value')
                if int(val) > dominant_value:
                    dominant_value = int(val)

        dt_now = datetime.now()
        self._last_poll = dt_now.strftime("%Y/%m/%d %H:%M")
        self._state = dominant_value
        self._successful_poll = self._pdata['successful_poll']
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
