"""Constants for Websocket Event Filter."""
from __future__ import annotations


def str_to_list(value: str) -> list[str]:
    """Convert a newline-separated string to a cleaned list, ignoring blank lines."""
    return [line.strip() for line in value.splitlines() if line.strip()]


DOMAIN = "websocket_event_filter"

CONF_DENY_PREFIXES = "deny_prefixes"
CONF_DENY_PATTERNS = "deny_patterns"
CONF_ALLOW_PREFIXES = "allow_prefixes"
CONF_ALLOW_PATTERNS = "allow_patterns"

EXPECTED_FUNCTIONS: dict[str, list[str]] = {
    "_forward_entity_changes": [
        "send_message",
        "entity_ids",
        "entity_filter",
        "user",
        "message_id_as_bytes",
        "event",
    ],
    "_forward_events_check_permissions": [
        "send_message",
        "user",
        "message_id_as_bytes",
        "event",
    ],
    "_forward_events_unconditional": [
        "send_message",
        "message_id_as_bytes",
        "event",
    ],
}
