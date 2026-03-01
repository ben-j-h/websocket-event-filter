"""Tests for EventFilter."""
from custom_components.websocket_event_filter.const import MODE_ALLOW, MODE_DENY
from custom_components.websocket_event_filter.filter import EventFilter


def test_empty_config_forwards_everything() -> None:
    f = EventFilter({})
    assert f.should_forward("sensor.temperature") is True
    assert f.should_forward("sensor.gem_channel_1") is True
    assert f.should_forward("light.living_room") is True


def test_deny_prefix_blocks_matching_entity() -> None:
    f = EventFilter({"mode": MODE_DENY, "deny_prefixes": ["sensor.gem_"]})
    assert f.should_forward("sensor.gem_channel_1") is False
    assert f.should_forward("sensor.gem_total") is False


def test_deny_prefix_passes_non_matching_entity() -> None:
    f = EventFilter({"mode": MODE_DENY, "deny_prefixes": ["sensor.gem_"]})
    assert f.should_forward("sensor.temperature") is True
    assert f.should_forward("light.living_room") is True
    assert f.should_forward("sensor.gem") is True  # underscore required


def test_deny_pattern_blocks_matching_entity() -> None:
    f = EventFilter({"mode": MODE_DENY, "deny_patterns": [r"^sensor\.high_freq_.*$"]})
    assert f.should_forward("sensor.high_freq_power") is False
    assert f.should_forward("sensor.high_freq_voltage") is False


def test_deny_pattern_passes_non_matching_entity() -> None:
    f = EventFilter({"mode": MODE_DENY, "deny_patterns": [r"^sensor\.high_freq_.*$"]})
    assert f.should_forward("sensor.temperature") is True
    assert f.should_forward("light.high_freq_light") is True


def test_allow_mode_only_passes_matching_entities() -> None:
    f = EventFilter({"mode": MODE_ALLOW, "allow_prefixes": ["light.", "switch."]})
    assert f.should_forward("light.living_room") is True
    assert f.should_forward("switch.fan") is True
    assert f.should_forward("sensor.temperature") is False
    assert f.should_forward("sensor.gem_channel_1") is False


def test_allow_pattern_mode() -> None:
    f = EventFilter({"mode": MODE_ALLOW, "allow_patterns": [r"^(light|switch)\."]})
    assert f.should_forward("light.kitchen") is True
    assert f.should_forward("switch.heater") is True
    assert f.should_forward("sensor.power") is False


def test_deny_mode_ignores_allow_rules() -> None:
    # Explicit deny mode — allow rules present but mode is deny, so deny rules apply
    f = EventFilter(
        {
            "mode": MODE_DENY,
            "deny_prefixes": ["sensor.gem_"],
            "allow_prefixes": ["sensor.gem_"],  # irrelevant in deny mode
        }
    )
    assert f.should_forward("sensor.gem_channel_1") is False
    assert f.should_forward("light.kitchen") is True


def test_multiple_deny_prefixes() -> None:
    f = EventFilter(
        {"mode": MODE_DENY, "deny_prefixes": ["sensor.gem_", "sensor.high_freq_"]}
    )
    assert f.should_forward("sensor.gem_channel_1") is False
    assert f.should_forward("sensor.high_freq_power") is False
    assert f.should_forward("sensor.temperature") is True


def test_multiple_deny_patterns() -> None:
    f = EventFilter(
        {"mode": MODE_DENY, "deny_patterns": [r"^sensor\.gem_", r"^sensor\.high_freq_"]}
    )
    assert f.should_forward("sensor.gem_channel_1") is False
    assert f.should_forward("sensor.high_freq_power") is False
    assert f.should_forward("sensor.temperature") is True


def test_mixed_deny_prefix_and_pattern() -> None:
    f = EventFilter(
        {
            "mode": MODE_DENY,
            "deny_prefixes": ["sensor.gem_"],
            "deny_patterns": [r"^binary_sensor\.door_"],
        }
    )
    assert f.should_forward("sensor.gem_channel_1") is False
    assert f.should_forward("binary_sensor.door_front") is False
    assert f.should_forward("sensor.temperature") is True
    assert f.should_forward("binary_sensor.motion") is True


def test_allow_prefix_and_allow_pattern_combined() -> None:
    f = EventFilter(
        {
            "mode": MODE_ALLOW,
            "allow_prefixes": ["light."],
            "allow_patterns": [r"^switch\.fan"],
        }
    )
    assert f.should_forward("light.kitchen") is True
    assert f.should_forward("switch.fan_bedroom") is True
    assert f.should_forward("switch.heater") is False
    assert f.should_forward("sensor.power") is False


def test_deny_prefix_exact_boundary() -> None:
    f = EventFilter({"mode": MODE_DENY, "deny_prefixes": ["sensor.gem_"]})
    assert f.should_forward("sensor.gem") is True   # no trailing underscore
    assert f.should_forward("sensor.gem_") is False
    assert f.should_forward("sensor.gem_x") is False
