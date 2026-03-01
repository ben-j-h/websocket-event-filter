"""Event filter logic for Websocket Event Filter."""
import re

from .const import (
    CONF_ALLOW_PATTERNS,
    CONF_ALLOW_PREFIXES,
    CONF_DENY_PATTERNS,
    CONF_DENY_PREFIXES,
    CONF_MODE,
    MODE_ALLOW,
    MODE_DENY,
)


class EventFilter:
    def __init__(self, config: dict) -> None:
        self._allow_mode: bool = config.get(CONF_MODE, MODE_DENY) == MODE_ALLOW
        self._deny_prefixes: tuple[str, ...] = tuple(config.get(CONF_DENY_PREFIXES, []))
        self._allow_prefixes: tuple[str, ...] = tuple(config.get(CONF_ALLOW_PREFIXES, []))
        self._deny_patterns: list[re.Pattern] = [
            re.compile(p) for p in config.get(CONF_DENY_PATTERNS, [])
        ]
        self._allow_patterns: list[re.Pattern] = [
            re.compile(p) for p in config.get(CONF_ALLOW_PATTERNS, [])
        ]

    def should_forward(self, entity_id: str) -> bool:
        """Return True if this entity_id should be forwarded to the client."""
        if self._allow_mode:
            return (
                bool(self._allow_prefixes and entity_id.startswith(self._allow_prefixes))
                or any(p.search(entity_id) for p in self._allow_patterns)
            )
        return not (
            (self._deny_prefixes and entity_id.startswith(self._deny_prefixes))
            or any(p.search(entity_id) for p in self._deny_patterns)
        )
