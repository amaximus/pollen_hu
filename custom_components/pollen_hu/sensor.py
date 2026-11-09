import aiohttp
import json
import logging
import re
import time
import unidecode
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
CONF_TOWN = "town"

DEFAULT_ALLDOMINANT = False
DEFAULT_ICON = 'mdi:blur'
DEFAULT_NAME = 'Pollen HU'
DEFAULT_POLLENS = ['parlagfu']
DEFAULT_SSL = True
DEFAULT_TOWN = 'budapest'

HTTP_TIMEOUT = 10 # secs
MAX_RETRIES = 3
POLLEN_API="https://ugyvitel.nngyk.gov.hu/kornyezetegeszsegugy/api/pollen-search/"
SCAN_INTERVAL = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_ALLDOMINANT, default=DEFAULT_ALLDOMINANT): cv.boolean,
    vol.Optional(CONF_POLLENS, default=DEFAULT_POLLENS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
    vol.Optional(CONF_TOWN, default=DEFAULT_TOWN): cv.string,
})

def _get_pollen_id(argument):
    switcher = {
      "alternaria": "26",
      "balvanyfa": "27",
      "bukk": "16",
      "ciprusfelek": "6",
      "tiszafafelek": "6",
      "ciprusfelek/tiszafafelek": "6",
      "csalanfelek": "19",
      "dio": "15",
      "eger": "4",
      "eperfafelek": "17",
      "epicoccum": "28",
      "fenyofelek": "18",
      "fuz": "11",
      "gyertyan": "12",
      "hars": "22",
      "juhar": "10",
      "kenderfelek": "23",
      "koris": "7",
      "libatopfelek": "24",
      "lorom": "21",
      "mogyoro": "5",
      "nyar": "8",
      "nyir": "3",
      "parlagfu": "1",
      "pazsitfufelek": "2",
      "platan": "13",
      "szil": "9",
      "tolgy": "14",
      "utifu": "20",
      "urom": "25",
    }
    return switcher.get(argument)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    alldominant = config.get(CONF_ALLDOMINANT)
    pollens = config.get(CONF_POLLENS)
    ssl = config.get(CONF_SSL)
    town = config.get(CONF_TOWN)

    async_add_devices(
        [PollenHUSensor(hass, name, alldominant, pollens, ssl, town)],update_before_add=True)

def _sleep(secs):
    time.sleep(secs)

async def async_get_pdata(self):
    pjson = {"pollens": []}
    successful_poll = "true"

    dt_today = datetime.now()
    str_today = dt_today.strftime("%Y-%m-%d")

    _session = async_get_clientsession(self._hass, self._ssl)

    for conf_pollen in self._pollens:
        conf_pollen_norm = unidecode.unidecode(conf_pollen).lower()
        pollen_id = _get_pollen_id(conf_pollen_norm)

        _LOGGER.debug(str(type(pollen_id)))
        if pollen_id is None:
            _LOGGER.debug("non-valid " + conf_pollen)
            continue

        _LOGGER.debug(conf_pollen + " " + conf_pollen_norm )

        url = POLLEN_API + 'search?filter=%7B%22datum%22%3A%22' + str_today \
              + '%22%2C%22telepules%22%3A%22' + self._town \
              + '%22%2C%22ertekek.noveny%22%3A%7B%22%24eq%22%3A%22' \
              + pollen_id + '%22%7D%7D&page=1'
        for i in range(MAX_RETRIES):
            try:
                async with _session.get(url, timeout=HTTP_TIMEOUT) as response:

                    rsp1 = await response.text()
                    _LOGGER.debug(url + " " + str(response.status))

                if not response.status // 100 == 2:
                    rsp1 = ""
                    successful_poll = "false"
                    _LOGGER.debug("donwload not successful")
                    await self._hass.async_add_executor_job(_sleep, 10)
                else:
                    _LOGGER.debug("rsp1: " + rsp1)
                    break
                _LOGGER.debug(url + " " + str(response.text()))
            except Exception as err:
                rsp1 = ""
                successful_poll = "false"
                _LOGGER.debug("Fetch attempt " + str(i+1) + " failed for " + url)
                _LOGGER.debug(f'error: {err} of type: {type(err)}')
                await self._hass.async_add_executor_job(_sleep, 10)

        if successful_poll == "true":
            val = json.loads(rsp1)
            if len(val['rows']) > 0:
                n_val = val["rows"][0]["ertekek"]["kategoria"]
                if n_val == "nincs-adat":
                    n_val = -1
                pjson['pollens'].append({"name": conf_pollen_norm, \
                    "value": n_val})
                _LOGGER.debug(str(n_val))

    pjson['successful_poll'] = successful_poll
    _LOGGER.debug(str(pjson))
    return pjson

class PollenHUSensor(Entity):

    def __init__(self, hass, name, alldominant, pollens, ssl, town):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._alldominant = alldominant
        self._state = None
        self._last_poll = ""
        self._pdata = []
        self._pollens = pollens
        self._ssl = ssl
        self._town = unidecode.unidecode(town).lower()
        self._successful_poll = "true"
        self._icon = DEFAULT_ICON

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
