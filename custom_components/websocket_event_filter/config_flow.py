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
    CONF_MODE,
    DOMAIN,
    MODE_ALLOW,
    MODE_DENY,
)

_MODE_OPTIONS = [
    {"value": MODE_DENY, "label": "Deny list — block specific entities"},
    {"value": MODE_ALLOW, "label": "Allow list — only forward specific entities"},
]

_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE, default=MODE_DENY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_MODE_OPTIONS,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
    }
)

_TEXT_MULTILINE = selector.TextSelector(selector.TextSelectorConfig(multiline=True))

_DENY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DENY_PREFIXES, default=""): _TEXT_MULTILINE,
        vol.Optional(CONF_DENY_PATTERNS, default=""): _TEXT_MULTILINE,
    }
)

_ALLOW_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ALLOW_PREFIXES, default=""): _TEXT_MULTILINE,
        vol.Optional(CONF_ALLOW_PATTERNS, default=""): _TEXT_MULTILINE,
    }
)


def _schema_with_defaults(schema: vol.Schema, defaults: dict) -> vol.Schema:
    """Return a copy of schema with default values filled from defaults dict."""
    return vol.Schema(
        {
            vol.Optional(k.schema, default=defaults.get(k.schema, k.default())): v
            for k, v in schema.schema.items()
        }
    )


def _validate_patterns(value: str) -> str | None:
    """Return an error key if any non-empty line is not valid regex, else None."""
    for line in value.splitlines():
        line = line.strip()
        if line:
            try:
                re.compile(line)
            except re.error:
                return "invalid_regex"
    return None


class WebsocketEventFilterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Websocket Event Filter."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str = MODE_DENY

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            if self._mode == MODE_ALLOW:
                return await self.async_step_allow()
            return await self.async_step_deny()

        return self.async_show_form(step_id="user", data_schema=_MODE_SCHEMA)

    async def async_step_deny(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_patterns(user_input.get(CONF_DENY_PATTERNS, ""))
            if err:
                errors[CONF_DENY_PATTERNS] = err
            else:
                return self.async_create_entry(
                    title="Websocket Event Filter",
                    data={},
                    options={CONF_MODE: MODE_DENY, **user_input},
                )

        return self.async_show_form(
            step_id="deny",
            data_schema=_schema_with_defaults(_DENY_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_allow(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_patterns(user_input.get(CONF_ALLOW_PATTERNS, ""))
            if err:
                errors[CONF_ALLOW_PATTERNS] = err
            else:
                return self.async_create_entry(
                    title="Websocket Event Filter",
                    data={},
                    options={CONF_MODE: MODE_ALLOW, **user_input},
                )

        return self.async_show_form(
            step_id="allow",
            data_schema=_schema_with_defaults(_ALLOW_SCHEMA, user_input or {}),
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
        self._mode: str = config_entry.options.get(CONF_MODE, MODE_DENY)

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            if self._mode == MODE_ALLOW:
                return await self.async_step_allow()
            return await self.async_step_deny()

        return self.async_show_form(
            step_id="init",
            data_schema=_schema_with_defaults(
                _MODE_SCHEMA, {CONF_MODE: self._mode}
            ),
        )

    async def async_step_deny(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_patterns(user_input.get(CONF_DENY_PATTERNS, ""))
            if err:
                errors[CONF_DENY_PATTERNS] = err
            else:
                return self.async_create_entry(
                    title="", data={CONF_MODE: MODE_DENY, **user_input}
                )

        current = self.config_entry.options
        defaults = user_input or {
            CONF_DENY_PREFIXES: current.get(CONF_DENY_PREFIXES, ""),
            CONF_DENY_PATTERNS: current.get(CONF_DENY_PATTERNS, ""),
        }
        return self.async_show_form(
            step_id="deny",
            data_schema=_schema_with_defaults(_DENY_SCHEMA, defaults),
            errors=errors,
        )

    async def async_step_allow(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_patterns(user_input.get(CONF_ALLOW_PATTERNS, ""))
            if err:
                errors[CONF_ALLOW_PATTERNS] = err
            else:
                return self.async_create_entry(
                    title="", data={CONF_MODE: MODE_ALLOW, **user_input}
                )

        current = self.config_entry.options
        defaults = user_input or {
            CONF_ALLOW_PREFIXES: current.get(CONF_ALLOW_PREFIXES, ""),
            CONF_ALLOW_PATTERNS: current.get(CONF_ALLOW_PATTERNS, ""),
        }
        return self.async_show_form(
            step_id="allow",
            data_schema=_schema_with_defaults(_ALLOW_SCHEMA, defaults),
            errors=errors,
        )
