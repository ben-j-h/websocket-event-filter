# Tech Spec: Websocket Event Filter — HA Custom Component

## Problem

Home Assistant's websocket API broadcasts every `state_changed` event to all connected frontend
clients. With ~6000 entities — particularly high-frequency sensor entities such as GreenEye Monitor
(`sensor.gem_*`) energy sensors updating every few seconds — the frontend receives a firehose of
events that makes the Lovelace UI unusably slow.

**Root cause:** HA broadcasts every event unconditionally; filtering only occurs at render time in
the frontend.

**Temporary fix applied:** Manual edits to
`homeassistant/components/websocket_api/commands.py` to hard-code prefix guards. This is wiped on
every HA update.

---

## Goal

A HACS-compatible custom component that:

1. **Monkey-patches** the three HA websocket forwarding functions to inject configurable filtering.
2. Supports **deny-list** (block matching entities) and **allow-list** (only pass matching entities)
   modes, configurable from `configuration.yaml`.
3. Accepts **entity ID prefixes** and **regular expressions** as filter rules.
4. Restores original functions cleanly on component unload.
5. Logs a **compatibility warning** on startup if the patched functions have moved or changed
   signature.
6. Ships with a **Claude Code skill** (`/check-ha-compat`) for validating compatibility before
   upgrading HA.

---

## Affected HA Module

**Module:** `homeassistant.components.websocket_api.commands`

**File path in HA core:**
`homeassistant/components/websocket_api/commands.py`

Verified against HA `dev` branch commit `0aa66ed` (2026-03-01).

### Target Functions

| Function | Approximate line | Used in | Purpose |
|---|---|---|---|
| `_forward_events_check_permissions` | ~148 | `handle_subscribe_events` | Legacy `subscribe_events` for non-admin users with `event_type == EVENT_STATE_CHANGED` |
| `_forward_events_unconditional` | ~168 | `handle_subscribe_events` | Legacy `subscribe_events` for admins / non-state events |
| `_forward_entity_changes` | ~408 | `handle_subscribe_entities` | Modern Lovelace `subscribe_entities` (primary path) |

### Signatures (current)

```python
@callback
def _forward_events_check_permissions(
    send_message: Callable[[bytes | str | dict[str, Any]], None],
    user: User,
    message_id_as_bytes: bytes,
    event: Event,
) -> None: ...

@callback
def _forward_events_unconditional(
    send_message: Callable[[bytes | str | dict[str, Any]], None],
    message_id_as_bytes: bytes,
    event: Event,
) -> None: ...

@callback
def _forward_entity_changes(
    send_message: Callable[[str | bytes | dict[str, Any]], None],
    entity_ids: set[str] | None,
    entity_filter: Callable[[str], bool] | None,
    user: User,
    message_id_as_bytes: bytes,
    event: Event[EventStateChangedData],
) -> None: ...
```

### How They Are Bound

Both `handle_subscribe_events` and `handle_subscribe_entities` create `functools.partial` objects
that capture the function **by object reference** at the time a client subscribes. Python's global
name lookup in `handle_subscribe_entities` resolves `_forward_entity_changes` from the module's
`__globals__` dict at *call time*. Therefore, replacing the attribute on the module object before
any client subscribes is sufficient — all future subscriptions will use the patched version.

**Assumption:** The custom component loads at HA startup, before any frontend client establishes a
websocket connection and issues a `subscribe_entities` / `subscribe_events` command. This is
consistent with how HA loads integrations.

---

## Monkey Patch Strategy

```python
import homeassistant.components.websocket_api.commands as _commands
import inspect

# 1. Verify compatibility
_assert_compat(_commands)

# 2. Store originals
_originals = {
    "_forward_entity_changes":           _commands._forward_entity_changes,
    "_forward_events_check_permissions": _commands._forward_events_check_permissions,
    "_forward_events_unconditional":     _commands._forward_events_unconditional,
}

# 3. Replace with filtered wrappers
_commands._forward_entity_changes           = _make_entity_wrapper(_filter, _originals["_forward_entity_changes"])
_commands._forward_events_check_permissions = _make_event_wrapper(_filter, _originals["_forward_events_check_permissions"])
_commands._forward_events_unconditional     = _make_event_wrapper(_filter, _originals["_forward_events_unconditional"])
```

The wrappers are thin: they inspect `event.data.get("entity_id")` and bail early if the entity is
filtered, otherwise delegate to the original.

**Restore on unload:**
```python
for name, func in _originals.items():
    setattr(_commands, name, func)
```

---

## File Structure

```
custom_components/websocket_event_filter/
├── __init__.py          # async_setup, async_setup_entry (YAML-based), applies/removes patches
├── manifest.json        # domain, name, version, iot_class
├── const.py             # DOMAIN, config keys, defaults
├── filter.py            # EventFilter class: compiled regex + prefix logic
└── strings.json         # UI strings (minimal — no config flow)
```

The existing boilerplate files (`api.py`, `binary_sensor.py`, `sensor.py`, `switch.py`,
`config_flow.py`, `entity.py`) should be **deleted** — this component has no entities, no
platforms, and no config flow.

---

## Configuration Schema

Configured in `configuration.yaml` under the component domain. No UI config flow.

```yaml
websocket_event_filter:
  # Optional list of entity_id prefixes to deny (block).
  # Entities whose IDs start with any of these strings are filtered out.
  deny_prefixes:
    - "sensor.gem_"

  # Optional list of Python regex patterns to deny.
  # Evaluated against the full entity_id string.
  deny_patterns:
    - "^sensor\\.high_freq_.*$"

  # Optional list of entity_id prefixes to allow.
  # When non-empty, ONLY entities matching an allow rule are forwarded.
  allow_prefixes: []

  # Optional list of Python regex patterns to allow.
  allow_patterns: []
```

**Logic:**

1. If `allow_prefixes` or `allow_patterns` are non-empty, run in **allow-list mode**: an entity
   passes only if it matches at least one allow rule.
2. Otherwise run in **deny-list mode**: an entity is blocked if it matches any deny rule.
3. If neither set has rules, all entities pass (no-op — useful for temporarily disabling without
   removing the component).

**Validation:**
- Regex patterns are compiled at startup; malformed patterns raise `vol.Invalid` during config
  validation and prevent HA from starting.
- Duplicate rules are silently de-duplicated.

---

## `EventFilter` Class (`filter.py`)

```python
class EventFilter:
    def __init__(self, config: dict) -> None:
        self._deny_prefixes: tuple[str, ...] = tuple(config.get(CONF_DENY_PREFIXES, []))
        self._allow_prefixes: tuple[str, ...] = tuple(config.get(CONF_ALLOW_PREFIXES, []))
        self._deny_patterns: list[re.Pattern] = [re.compile(p) for p in config.get(CONF_DENY_PATTERNS, [])]
        self._allow_patterns: list[re.Pattern] = [re.compile(p) for p in config.get(CONF_ALLOW_PATTERNS, [])]
        self._allow_mode: bool = bool(self._allow_prefixes or self._allow_patterns)

    def should_forward(self, entity_id: str) -> bool:
        """Return True if this entity_id should be forwarded to the client."""
        if self._allow_mode:
            return (
                entity_id.startswith(self._allow_prefixes)
                or any(p.search(entity_id) for p in self._allow_patterns)
            )
        return not (
            (self._deny_prefixes and entity_id.startswith(self._deny_prefixes))
            or any(p.search(entity_id) for p in self._deny_patterns)
        )
```

---

## `__init__.py` Lifecycle

### `async_setup(hass, config)`

1. Extract component config from `config[DOMAIN]` (returns `True` immediately if not present).
2. Build `EventFilter` from config.
3. Import `homeassistant.components.websocket_api.commands`.
4. Run compatibility check; log `WARNING` if signatures changed but proceed.
5. Apply monkey patches.
6. Store originals and filter in `hass.data[DOMAIN]`.

### Component Unload / HA Shutdown

HA calls `async_unload_entry` if using config entries, but since we use YAML setup, we register a
`hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, ...)` listener to restore originals on
shutdown.

For hot-reload (e.g., `homeassistant.reload_config_entry`), `async_setup` is called again. The
code must detect if patches are already applied (compare current module function to stored wrapper)
and skip double-patching.

---

## Compatibility Check

```python
EXPECTED_FUNCTIONS = {
    "_forward_entity_changes": [
        "send_message", "entity_ids", "entity_filter", "user",
        "message_id_as_bytes", "event",
    ],
    "_forward_events_check_permissions": [
        "send_message", "user", "message_id_as_bytes", "event",
    ],
    "_forward_events_unconditional": [
        "send_message", "message_id_as_bytes", "event",
    ],
}

def _check_compat(module) -> list[str]:
    """Return list of warning strings. Empty = compatible."""
    issues = []
    for name, expected_params in EXPECTED_FUNCTIONS.items():
        func = getattr(module, name, None)
        if func is None:
            issues.append(f"Function '{name}' not found in module.")
            continue
        actual_params = list(inspect.signature(func).parameters.keys())
        if actual_params != expected_params:
            issues.append(
                f"Function '{name}' signature changed: "
                f"expected {expected_params}, got {actual_params}"
            )
    return issues
```

Warnings are logged at `WARNING` level. The component still loads and applies whatever patches it
can (skipping any function that has disappeared).

---

## Manifest

```json
{
  "domain": "websocket_event_filter",
  "name": "Websocket Event Filter",
  "version": "1.0.0",
  "documentation": "https://github.com/ben-j-h/websocket-event-filter",
  "issue_tracker": "https://github.com/ben-j-h/websocket-event-filter/issues",
  "dependencies": ["websocket_api"],
  "codeowners": ["@ben-j-h"],
  "iot_class": "local_push",
  "requirements": []
}
```

---

## Testing Strategy

Tests live in `tests/` using `pytest-homeassistant-custom-component`.

| Test file | What it tests |
|---|---|
| `test_filter.py` | `EventFilter.should_forward()` — prefix, regex, allow/deny modes, edge cases |
| `test_init.py` | Patch applied on setup, originals restored on teardown, double-patch guard |
| `test_compat.py` | `_check_compat()` with mock modules — detects missing/changed functions |
| `test_integration.py` | End-to-end: mock HA state_changed event → verify filtered entity not sent, non-filtered entity is sent |

---

## Compatibility Validation Skill

A Claude Code skill stored at `~/.claude/commands/check-ha-compat.md` that can be invoked as
`/check-ha-compat` from any Claude Code session.

### Purpose

Before upgrading Home Assistant, run `/check-ha-compat` to:
- Fetch the current `commands.py` from the HA GitHub repo (`dev` or a specified branch/tag).
- Verify the three patched functions still exist with expected parameter signatures.
- Report any changes that would break the monkey patch.
- Suggest specific code changes to `__init__.py` or `filter.py` if the signatures differ.

### Implementation

The skill fetches the file via the GitHub API (`gh api` or `WebFetch`), decodes it, and uses
`inspect`-style analysis to extract function signatures. It compares against the expected signatures
recorded in `TECH_SPEC.md` and reports a compatibility verdict.

### Skill File Location

`~/.claude/commands/check-ha-compat.md`

### Skill File Content Schema

```markdown
---
name: check-ha-compat
description: "Check if the websocket-event-filter monkey patch is compatible with a given HA version"
---

[Prompt content that Claude expands when /check-ha-compat is invoked]
```

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| HA moves functions to different module | Medium | Compat check warns; `/check-ha-compat` catches before upgrade |
| HA changes function signatures | Medium | Compat check warns; wrappers use `*args/**kwargs` passthrough as last resort |
| Patch applied after some clients subscribed | Low | Component loads at HA startup before frontend connects |
| Double-patch on reload | Low | Guard checks if current module attr is already a wrapper |
| Filter bug blocks ALL entities | Low | No-op configuration (empty rules) passes everything |

---

## Out of Scope

- Filtering non-`state_changed` event types.
- Per-user or per-connection filter rules.
- A Lovelace card or UI for managing rules.
- Automatic HA version detection (handled by the companion skill).
