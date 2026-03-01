"""Tests for _check_compat."""
import types

from custom_components.websocket_event_filter import _check_compat
from custom_components.websocket_event_filter.const import EXPECTED_FUNCTIONS


def _make_full_module() -> types.ModuleType:
    """Return a module with all three expected functions using correct signatures."""
    mod = types.ModuleType("mock_commands")

    def _forward_entity_changes(
        send_message, entity_ids, entity_filter, user, message_id_as_bytes, event
    ):
        pass

    def _forward_events_check_permissions(
        send_message, user, message_id_as_bytes, event
    ):
        pass

    def _forward_events_unconditional(send_message, message_id_as_bytes, event):
        pass

    mod._forward_entity_changes = _forward_entity_changes
    mod._forward_events_check_permissions = _forward_events_check_permissions
    mod._forward_events_unconditional = _forward_events_unconditional
    return mod


def test_no_issues_when_all_functions_match() -> None:
    mod = _make_full_module()
    issues = _check_compat(mod)
    assert issues == []


def test_issue_reported_for_missing_function() -> None:
    mod = _make_full_module()
    del mod._forward_entity_changes

    issues = _check_compat(mod)

    assert len(issues) == 1
    assert "_forward_entity_changes" in issues[0]
    assert "not found" in issues[0]


def test_issue_reported_for_changed_signature() -> None:
    mod = _make_full_module()

    # Replace _forward_events_unconditional with a different signature
    def _forward_events_unconditional(send_message, message_id_as_bytes, event, extra_param):
        pass

    mod._forward_events_unconditional = _forward_events_unconditional

    issues = _check_compat(mod)

    assert len(issues) == 1
    assert "_forward_events_unconditional" in issues[0]
    assert "signature changed" in issues[0]


def test_multiple_issues_reported() -> None:
    mod = _make_full_module()
    del mod._forward_entity_changes

    def _forward_events_unconditional(send_message, message_id_as_bytes, event, extra):
        pass

    mod._forward_events_unconditional = _forward_events_unconditional

    issues = _check_compat(mod)

    assert len(issues) == 2
    names_in_issues = " ".join(issues)
    assert "_forward_entity_changes" in names_in_issues
    assert "_forward_events_unconditional" in names_in_issues


def test_all_functions_missing() -> None:
    mod = types.ModuleType("empty_commands")

    issues = _check_compat(mod)

    assert len(issues) == len(EXPECTED_FUNCTIONS)
    for name in EXPECTED_FUNCTIONS:
        assert any(name in issue for issue in issues)


def test_check_compat_returns_list() -> None:
    mod = _make_full_module()
    result = _check_compat(mod)
    assert isinstance(result, list)
