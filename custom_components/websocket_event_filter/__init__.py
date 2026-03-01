"""Websocket Event Filter — monkey-patches HA websocket forwarding to filter entities."""
from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback

from .const import (
    CONF_ALLOW_PATTERNS,
    CONF_ALLOW_PREFIXES,
    CONF_DENY_PATTERNS,
    CONF_DENY_PREFIXES,
    CONF_MODE,
    DOMAIN,
    EXPECTED_FUNCTIONS,
    MODE_DENY,
    str_to_list,
)
from .filter import EventFilter

_LOGGER: logging.Logger = logging.getLogger(__package__)


def _check_compat(module: Any) -> list[str]:
    issues = []
    for name, expected_params in EXPECTED_FUNCTIONS.items():
        func = getattr(module, name, None)
        if func is None:
            issues.append(f"Function '{name}' not found — patch will be skipped")
            continue
        actual = list(inspect.signature(func).parameters.keys())
        if actual != expected_params:
            issues.append(
                f"'{name}' signature changed: expected {expected_params}, got {actual}"
            )
    return issues


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """YAML setup — configuration is done via the UI."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Apply websocket patches using options from the config entry."""
    import homeassistant.components.websocket_api.commands as _commands

    options = entry.options
    config = {
        CONF_MODE: options.get(CONF_MODE, MODE_DENY),
        CONF_DENY_PREFIXES: str_to_list(options.get(CONF_DENY_PREFIXES, "")),
        CONF_DENY_PATTERNS: str_to_list(options.get(CONF_DENY_PATTERNS, "")),
        CONF_ALLOW_PREFIXES: str_to_list(options.get(CONF_ALLOW_PREFIXES, "")),
        CONF_ALLOW_PATTERNS: str_to_list(options.get(CONF_ALLOW_PATTERNS, "")),
    }
    event_filter = EventFilter(config)

    for issue in _check_compat(_commands):
        _LOGGER.warning("Websocket event filter compat issue: %s", issue)

    if hass.data.get(DOMAIN, {}).get("originals"):
        _LOGGER.warning(
            "Websocket event filter patches already applied — skipping re-patch"
        )
        return True

    originals: dict[str, Callable] = {
        name: func
        for name in EXPECTED_FUNCTIONS
        if (func := getattr(_commands, name, None)) is not None
    }

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["originals"] = originals
    hass.data[DOMAIN]["commands_module"] = _commands

    if "_forward_entity_changes" in originals:
        _orig_entity = originals["_forward_entity_changes"]

        @callback
        def _patched_forward_entity_changes(
            send_message: Callable[[str | bytes | dict[str, Any]], None],
            entity_ids: set[str] | None,
            entity_filter: Callable[[str], bool] | None,
            user: Any,
            message_id_as_bytes: bytes,
            event: Event[EventStateChangedData],
        ) -> None:
            if not event_filter.should_forward(event.data["entity_id"]):
                return
            return _orig_entity(
                send_message, entity_ids, entity_filter, user, message_id_as_bytes, event
            )

        _commands._forward_entity_changes = _patched_forward_entity_changes

    if "_forward_events_check_permissions" in originals:
        _orig_check_perms = originals["_forward_events_check_permissions"]

        @callback
        def _patched_forward_events_check_permissions(
            send_message: Callable[[bytes | str | dict[str, Any]], None],
            user: Any,
            message_id_as_bytes: bytes,
            event: Event,
        ) -> None:
            entity_id = event.data.get("entity_id", "")
            if entity_id and not event_filter.should_forward(entity_id):
                return
            return _orig_check_perms(send_message, user, message_id_as_bytes, event)

        _commands._forward_events_check_permissions = (
            _patched_forward_events_check_permissions
        )

    if "_forward_events_unconditional" in originals:
        _orig_unconditional = originals["_forward_events_unconditional"]

        @callback
        def _patched_forward_events_unconditional(
            send_message: Callable[[bytes | str | dict[str, Any]], None],
            message_id_as_bytes: bytes,
            event: Event,
        ) -> None:
            entity_id = event.data.get("entity_id", "")
            if entity_id and not event_filter.should_forward(entity_id):
                return
            return _orig_unconditional(send_message, message_id_as_bytes, event)

        _commands._forward_events_unconditional = _patched_forward_events_unconditional

    _LOGGER.info(
        "Websocket event filter patches applied (%d functions patched)",
        len(originals),
    )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Restore original websocket functions and clean up."""
    domain_data = hass.data.pop(DOMAIN, {})
    _commands = domain_data.get("commands_module")
    if _commands:
        for name, func in domain_data.get("originals", {}).items():
            setattr(_commands, name, func)
        _LOGGER.info("Websocket event filter patches restored")
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
