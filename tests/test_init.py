"""Tests for __init__.py patch lifecycle."""
import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.websocket_event_filter.const import DOMAIN
from custom_components.websocket_event_filter import async_setup

from .const import MOCK_CONFIG


def _make_mock_commands_module() -> types.ModuleType:
    """Create a mock commands module with the three expected functions."""
    mod = types.ModuleType("homeassistant.components.websocket_api.commands")

    def _forward_entity_changes(
        send_message, entity_ids, entity_filter, user, message_id_as_bytes, event
    ):
        send_message("entity_changed")

    def _forward_events_check_permissions(
        send_message, user, message_id_as_bytes, event
    ):
        send_message("check_perms")

    def _forward_events_unconditional(send_message, message_id_as_bytes, event):
        send_message("unconditional")

    mod._forward_entity_changes = _forward_entity_changes
    mod._forward_events_check_permissions = _forward_events_check_permissions
    mod._forward_events_unconditional = _forward_events_unconditional
    return mod


def _make_event(entity_id: str | None = None) -> MagicMock:
    event = MagicMock()
    if entity_id is not None:
        event.data = {"entity_id": entity_id}
    else:
        event.data = {}
    return event


@pytest.mark.asyncio
async def test_patches_applied_after_setup(hass) -> None:
    """After async_setup, the three functions on the commands module are replaced."""
    mock_mod = _make_mock_commands_module()
    original_entity_fn = mock_mod._forward_entity_changes
    original_check_perms_fn = mock_mod._forward_events_check_permissions
    original_unconditional_fn = mock_mod._forward_events_unconditional

    config = {DOMAIN: MOCK_CONFIG}

    with patch(
        "custom_components.websocket_event_filter.__init__.__import__",
        side_effect=lambda name, *a, **kw: mock_mod if "commands" in name else __import__(name, *a, **kw),
    ):
        # Patch the import inside async_setup
        import sys
        sys.modules["homeassistant.components.websocket_api.commands"] = mock_mod
        try:
            result = await async_setup(hass, config)
        finally:
            del sys.modules["homeassistant.components.websocket_api.commands"]

    assert result is True
    assert mock_mod._forward_entity_changes is not original_entity_fn
    assert mock_mod._forward_events_check_permissions is not original_check_perms_fn
    assert mock_mod._forward_events_unconditional is not original_unconditional_fn


@pytest.mark.asyncio
async def test_originals_restored_after_stop(hass) -> None:
    """After the HA stop event, original functions are restored on the commands module."""
    mock_mod = _make_mock_commands_module()
    original_entity_fn = mock_mod._forward_entity_changes
    original_check_perms_fn = mock_mod._forward_events_check_permissions
    original_unconditional_fn = mock_mod._forward_events_unconditional

    config = {DOMAIN: MOCK_CONFIG}

    import sys
    sys.modules["homeassistant.components.websocket_api.commands"] = mock_mod
    try:
        result = await async_setup(hass, config)
        assert result is True

        # Fire HA stop event to trigger restore
        hass.bus.async_fire("homeassistant_stop")
        await hass.async_block_till_done()
    finally:
        del sys.modules["homeassistant.components.websocket_api.commands"]

    assert mock_mod._forward_entity_changes is original_entity_fn
    assert mock_mod._forward_events_check_permissions is original_check_perms_fn
    assert mock_mod._forward_events_unconditional is original_unconditional_fn


@pytest.mark.asyncio
async def test_double_patch_guard(hass) -> None:
    """If async_setup is called twice, the second call skips patching."""
    mock_mod = _make_mock_commands_module()
    config = {DOMAIN: MOCK_CONFIG}

    import sys
    sys.modules["homeassistant.components.websocket_api.commands"] = mock_mod
    try:
        result1 = await async_setup(hass, config)
        assert result1 is True

        patched_entity_fn = mock_mod._forward_entity_changes

        # Call async_setup again — should detect existing originals and skip
        result2 = await async_setup(hass, config)
        assert result2 is True

        # The patch on the module should not have changed
        assert mock_mod._forward_entity_changes is patched_entity_fn
    finally:
        del sys.modules["homeassistant.components.websocket_api.commands"]


@pytest.mark.asyncio
async def test_no_domain_in_config_returns_true(hass) -> None:
    """If domain is not in config, async_setup returns True immediately."""
    result = await async_setup(hass, {})
    assert result is True
    assert hass.data.get(DOMAIN) is None


@pytest.mark.asyncio
async def test_patched_entity_changes_filters_denied_entity(hass) -> None:
    """The patched _forward_entity_changes drops events for denied entities."""
    mock_mod = _make_mock_commands_module()
    send_message = MagicMock()
    config = {DOMAIN: MOCK_CONFIG}  # deny_prefixes: ["sensor.gem_"]

    import sys
    sys.modules["homeassistant.components.websocket_api.commands"] = mock_mod
    try:
        await async_setup(hass, config)

        # Call the patched function with a denied entity
        denied_event = _make_event("sensor.gem_channel_1")
        mock_mod._forward_entity_changes(
            send_message, None, None, MagicMock(), b"1", denied_event
        )
        send_message.assert_not_called()

        # Call with an allowed entity
        allowed_event = _make_event("sensor.temperature")
        mock_mod._forward_entity_changes(
            send_message, None, None, MagicMock(), b"1", allowed_event
        )
        send_message.assert_called_once_with("entity_changed")
    finally:
        del sys.modules["homeassistant.components.websocket_api.commands"]


@pytest.mark.asyncio
async def test_patched_check_permissions_passes_non_entity_events(hass) -> None:
    """_forward_events_check_permissions passes events without entity_id."""
    mock_mod = _make_mock_commands_module()
    send_message = MagicMock()
    config = {DOMAIN: MOCK_CONFIG}  # deny_prefixes: ["sensor.gem_"]

    import sys
    sys.modules["homeassistant.components.websocket_api.commands"] = mock_mod
    try:
        await async_setup(hass, config)

        # Event with no entity_id should pass through
        event = MagicMock()
        event.data = {}
        mock_mod._forward_events_check_permissions(
            send_message, MagicMock(), b"1", event
        )
        send_message.assert_called_once_with("check_perms")
    finally:
        del sys.modules["homeassistant.components.websocket_api.commands"]
