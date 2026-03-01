# Websocket Event Filter

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]

![Websocket Event Filter][logoimg]

A Home Assistant custom component that filters entity state changes from the websocket event
stream before they reach connected frontend clients. This dramatically improves frontend
performance when your instance has a large number of high-frequency entities (e.g. energy
monitors, weather sensors) that the UI doesn't need to display in real time.

> **Unsupported modification:** This integration monkey-patches internal Home Assistant
> functions. It may break on any HA update. Run `/check-ha-compat` (see below) before upgrading.

## How it works

Home Assistant broadcasts every `state_changed` event to all connected browser tabs. With
thousands of entities this creates a firehose that makes Lovelace sluggish. This component
intercepts the three internal functions responsible for forwarding those events and drops any
that match your configured filter rules — before they are serialised and sent over the wire.

## Requirements

- Home Assistant 2026.2.3 or newer
- HACS (for easy installation)

## Installation

### HACS (recommended)

1. Add this repository as a custom HACS repository (category: Integration).
2. Install **Websocket Event Filter** from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for
   **Websocket Event Filter**.

### Manual

1. Copy the `custom_components/websocket_event_filter/` folder into your HA
   `custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for
   **Websocket Event Filter**.

```text
custom_components/websocket_event_filter/
├── __init__.py
├── config_flow.py
├── const.py
├── filter.py
├── manifest.json
├── strings.json
└── translations/
    └── en.json
```

## Configuration

Configuration is done entirely in the UI — no `configuration.yaml` changes required.

After adding the integration, click **Configure** on the integration card at any time to
update the rules. Changes take effect immediately after the integration reloads (automatic).

### Filter fields

The setup flow first asks you to choose a mode, then shows only the relevant fields.
All fields are optional — leave blank to skip that rule type. Multiple values are
**comma-separated**.

**Deny list mode** (default) — block matching entities, forward everything else:

| Field | Description |
|---|---|
| **Block by prefix** | Block entities whose IDs start with any of these strings |
| **Block by pattern** | Block entities matching any of these Python regular expressions |

**Allow list mode** — only forward matching entities, block everything else:

| Field | Description |
|---|---|
| **Allow by prefix** | Forward entities whose IDs start with any of these strings |
| **Allow by pattern** | Forward entities matching any of these Python regular expressions |

### Example: block GreenEye Monitor sensors

```
Block by prefix:  sensor.gem_
```

### Example: block multiple high-frequency sensor groups

```
Block by prefix:  sensor.gem_, sensor.emporia_
```

### Example: allow only a specific set of domains

```
Allow by pattern:  ^light\., ^switch\., ^input_boolean\.
```

## Compatibility checking

Before upgrading Home Assistant, verify the patch will still work by running the included
Claude Code skill from any Claude Code session in this project:

```
/check-ha-compat
/check-ha-compat 2026.3.0
```

This fetches the relevant HA source file from GitHub and compares the patched function
signatures against the expected ones, reporting any breaking changes and what to fix.

## Contributions are welcome!

If you want to contribute, please read the [Contribution guidelines](CONTRIBUTING.md).

---

[buymecoffee]: https://www.buymeacoffee.com/ben-j-h
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[commits]: https://github.com/ben-j-h/websocket-event-filter/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[logoimg]: websocket_event_filter.png
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40ben-j-h-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ben-j-h/websocket-event-filter.svg?style=for-the-badge
[releases]: https://github.com/ben-j-h/websocket-event-filter/releases
[user_profile]: https://github.com/ben-j-h
