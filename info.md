[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]

Filter entity state changes from the Home Assistant websocket event stream before they reach
connected frontend clients. Dramatically improves Lovelace performance when your instance has
thousands of high-frequency sensor entities.

**Note:** This integration monkey-patches internal HA functions and may require an update after
each Home Assistant upgrade. See the README for the included compatibility check tool.

{% if not installed %}

## Installation

1. Click **Install**.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for
   **Websocket Event Filter**.

{% endif %}

## Configuration

Configuration is done in the UI — no `configuration.yaml` changes required. All four filter
fields accept one item per line:

| Field | Behaviour |
|---|---|
| **Deny prefixes** | Block entities whose IDs start with these strings |
| **Deny patterns** | Block entities matching these Python regular expressions |
| **Allow prefixes** | Allow-list mode: only forward matching entities |
| **Allow patterns** | Allow-list mode: only forward matching entities |

When any allow rule is set, the integration switches to allow-list mode and deny rules are
ignored.

---

[buymecoffee]: https://www.buymeacoffee.com/ben-j-h
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[commits]: https://github.com/ben-j-h/websocket-event-filter/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: https://github.com/ben-j-h/websocket-event-filter/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40ben-j-h-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[releases]: https://github.com/ben-j-h/websocket-event-filter/releases
[user_profile]: https://github.com/ben-j-h
