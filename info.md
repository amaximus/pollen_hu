[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

<p><a href="https://www.buymeacoffee.com/6rF5cQl" rel="nofollow" target="_blank"><img src="https://camo.githubusercontent.com/c070316e7fb193354999ef4c93df4bd8e21522fa/68747470733a2f2f696d672e736869656c64732e696f2f7374617469632f76312e7376673f6c6162656c3d4275792532306d6525323061253230636f66666565266d6573736167653d25463025394625413525413826636f6c6f723d626c61636b266c6f676f3d6275792532306d6525323061253230636f66666565266c6f676f436f6c6f723d7768697465266c6162656c436f6c6f723d366634653337" alt="Buy me a coffee" data-canonical-src="https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&amp;message=%F0%9F%A5%A8&amp;color=black&amp;logo=buy%20me%20a%20coffee&amp;logoColor=white&amp;labelColor=b0c4de" style="max-width:100%;"></a></p>

# Home Assistant custom component for pollen information in Hungary

This custom component gathers pollen information in Hungary from antsz.hu.

The state of the sensor will be the level of most dominant pollen. The name of the pollen with highest concentration level
will also be added into dedicated attributes.

The sensor will also report in an attribute the values of all other pollens.

#### Installation
The easiest way to install it is through [HACS (Home Assistant Community Store)](https://custom-components.github.io/hacs/),
search for <i>Pollen information Hungary</i> in the Integrations.<br />

Sensor of this platform should be configured as per below information.

#### Configuration:
Define sensor with the following configuration parameters:<br />

---
| Name | Optional | `Default` | Description |
| :---- | :---- | :------- | :----------- |
| name | **Y** | `pollen_hu` | name of the sensor |
---

#### Example
```
platform: pollen_hu
name: 'Pollen adatok'
```

#### Lovelace UI
There is a Lovelace custom card related to this component at [https://github.com/amaximus/pollen-hu-card](https://github.com/amaximus/pollen-hu-card).

If you want to show only the dominant pollen you may skip using the pollen-hu-card and use the following:

```
type: conditional
conditions:
  - entity: sensor.pollen
    state_not: '0'
  - entity: sensor.pollen
    state_not: '1'
  - entity: sensor.pollen
    state_not: '2'
card:
  type: custom:button-card
  icon: mdi:blur
  size: 30px
  styles:
    label:
      - font-size: 90%
    card:
      - height: 80px
    icon:
      - color: red
  label: >
    [[[
      var pollen = states['sensor.pollen'].attributes.dominant_pollen;
      return pollen;
    ]]]
  show_label: true
  show_name: false
  entity: sensor.pollen
  color_type: icon
```

#### Custom Lovelace card example:<br />
![Pollen information above medium concentration](https://raw.githubusercontent.com/amaximus/pollen_hu/main/pollen1.png)

## Thanks

Thanks to all the people who have contributed!

[![contributors](https://contributors-img.web.app/image?repo=amaximus/pollen_hu)](https://github.com/amaximus/pollen_hu/graphs/contributors)
