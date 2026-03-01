"""Config flow for Websocket Event Filter."""
from __future__ import annotations

import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ALLOW_PATTERNS,
    CONF_ALLOW_PREFIXES,
    CONF_DENY_PATTERNS,
    CONF_DENY_PREFIXES,
    DOMAIN,
)


def _validate_patterns(value: str) -> str | None:
    """Return an error key if any line is not a valid regex. None if all are valid."""
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            re.compile(line)
        except re.error:
            return "invalid_regex"
    return None


def _build_schema(defaults: dict) -> vol.Schema:
    text_multiline = selector.TextSelector(
        selector.TextSelectorConfig(multiline=True)
    )
    return vol.Schema(
        {
            vol.Optional(
                CONF_DENY_PREFIXES, default=defaults.get(CONF_DENY_PREFIXES, "")
            ): text_multiline,
            vol.Optional(
                CONF_DENY_PATTERNS, default=defaults.get(CONF_DENY_PATTERNS, "")
            ): text_multiline,
            vol.Optional(
                CONF_ALLOW_PREFIXES, default=defaults.get(CONF_ALLOW_PREFIXES, "")
            ): text_multiline,
            vol.Optional(
                CONF_ALLOW_PATTERNS, default=defaults.get(CONF_ALLOW_PATTERNS, "")
            ): text_multiline,
        }
    )


def _validate_user_input(user_input: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    for field in (CONF_DENY_PATTERNS, CONF_ALLOW_PATTERNS):
        err = _validate_patterns(user_input.get(field, ""))
        if err:
            errors[field] = err
    return errors


class WebsocketEventFilterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Websocket Event Filter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_user_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Websocket Event Filter",
                    data={},
                    options=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return WebsocketEventFilterOptionsFlowHandler(config_entry)


class WebsocketEventFilterOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Websocket Event Filter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_user_input(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(user_input or dict(self.config_entry.options)),
            errors=errors,
        )
