"""Test MQTT tracker for Reef-Pi integration."""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.reef_pi.mqtt_tracker import ReefPiMQTTTracker


@pytest.mark.asyncio
async def test_tracker_initialization():
    """Test tracker initialization with defaults."""
    tracker = ReefPiMQTTTracker()
    assert tracker.total_messages == 0
    assert tracker.last_message_time is None
    assert len(tracker.last_update_by_type) == 0
    assert len(tracker.last_update_by_device) == 0
    assert len(tracker.update_source) == 0


@pytest.mark.asyncio
async def test_tracker_initialization_custom_threshold():
    """Test tracker initialization with custom threshold."""
    tracker = ReefPiMQTTTracker(skip_polling_threshold=timedelta(minutes=5))
    assert tracker._skip_threshold == timedelta(minutes=5)


@pytest.mark.asyncio
async def test_record_mqtt_update():
    """Test recording MQTT updates."""
    tracker = ReefPiMQTTTracker()
    now = datetime.now(timezone.utc)

    tracker.record_mqtt_update("temperature", "1", now)

    assert tracker.total_messages == 1
    assert tracker.last_message_time == now
    assert tracker.last_update_by_type["temperature"] == now
    assert tracker.last_update_by_device["temperature"]["1"] == now
    assert tracker.update_source["temperature"]["1"] == "mqtt"


@pytest.mark.asyncio
async def test_record_mqtt_update_default_timestamp():
    """Test recording MQTT updates without explicit timestamp."""
    tracker = ReefPiMQTTTracker()
    before = datetime.now(timezone.utc)

    tracker.record_mqtt_update("temperature", "1")

    after = datetime.now(timezone.utc)
    assert tracker.total_messages == 1
    assert tracker.last_message_time is not None
    assert before <= tracker.last_message_time <= after
    assert "temperature" in tracker.last_update_by_type


@pytest.mark.asyncio
async def test_record_multiple_mqtt_updates():
    """Test recording multiple MQTT updates increments counter."""
    tracker = ReefPiMQTTTracker()

    tracker.record_mqtt_update("temperature", "1")
    tracker.record_mqtt_update("equipment", "2")
    tracker.record_mqtt_update("ph", "3")

    assert tracker.total_messages == 3
    assert "temperature" in tracker.last_update_by_type
    assert "equipment" in tracker.last_update_by_type
    assert "ph" in tracker.last_update_by_type


@pytest.mark.asyncio
async def test_record_polling_update():
    """Test recording polling updates."""
    tracker = ReefPiMQTTTracker()
    now = datetime.now()

    tracker.record_polling_update("temperature", "1", now)

    assert tracker.update_source["temperature"]["1"] == "polling"
    assert tracker.total_messages == 0  # Polling doesn't increment message count


@pytest.mark.asyncio
async def test_should_skip_polling_recent_mqtt():
    """Test that polling is skipped for devices with recent MQTT updates."""
    tracker = ReefPiMQTTTracker(skip_polling_threshold=timedelta(minutes=2))
    now = datetime.now(timezone.utc)

    # Record MQTT update 1 minute ago
    one_minute_ago = now - timedelta(minutes=1)
    tracker.record_mqtt_update("temperature", "1", one_minute_ago)

    # Should skip polling (within 2-minute threshold)
    assert tracker.should_skip_polling("temperature", "1") is True


@pytest.mark.asyncio
async def test_should_skip_polling_old_mqtt():
    """Test that polling is NOT skipped for devices with old MQTT updates."""
    tracker = ReefPiMQTTTracker(skip_polling_threshold=timedelta(minutes=2))
    now = datetime.now(timezone.utc)

    # Record MQTT update 3 minutes ago
    three_minutes_ago = now - timedelta(minutes=3)
    tracker.record_mqtt_update("temperature", "1", three_minutes_ago)

    # Should NOT skip polling (outside 2-minute threshold)
    assert tracker.should_skip_polling("temperature", "1") is False


@pytest.mark.asyncio
async def test_should_skip_polling_no_mqtt_update():
    """Test that polling is NOT skipped when no MQTT update exists."""
    tracker = ReefPiMQTTTracker()

    # No MQTT updates recorded
    assert tracker.should_skip_polling("temperature", "1") is False


@pytest.mark.asyncio
async def test_should_skip_polling_wrong_device():
    """Test that polling is NOT skipped for different device."""
    tracker = ReefPiMQTTTracker(skip_polling_threshold=timedelta(minutes=2))
    now = datetime.now(timezone.utc)

    tracker.record_mqtt_update("temperature", "1", now)

    # Different device ID should not skip
    assert tracker.should_skip_polling("temperature", "2") is False


@pytest.mark.asyncio
async def test_get_update_source_mqtt():
    """Test getting update source for MQTT-updated device."""
    tracker = ReefPiMQTTTracker()
    tracker.record_mqtt_update("temperature", "1")

    assert tracker.get_update_source("temperature", "1") == "mqtt"


@pytest.mark.asyncio
async def test_get_update_source_polling():
    """Test getting update source for polling-updated device."""
    tracker = ReefPiMQTTTracker()
    tracker.record_polling_update("temperature", "1")

    assert tracker.get_update_source("temperature", "1") == "polling"


@pytest.mark.asyncio
async def test_get_update_source_none():
    """Test getting update source for unknown device."""
    tracker = ReefPiMQTTTracker()

    assert tracker.get_update_source("temperature", "1") is None


@pytest.mark.asyncio
async def test_get_last_update_time_by_device():
    """Test getting last update time for specific device."""
    tracker = ReefPiMQTTTracker()
    now = datetime.now(timezone.utc)

    tracker.record_mqtt_update("temperature", "1", now)

    assert tracker.get_last_update_time("temperature", "1") == now


@pytest.mark.asyncio
async def test_get_last_update_time_by_type():
    """Test getting last update time for device type."""
    tracker = ReefPiMQTTTracker()
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(minutes=1)

    tracker.record_mqtt_update("temperature", "1", earlier)
    tracker.record_mqtt_update("temperature", "2", now)

    # Should return most recent update for the type
    assert tracker.get_last_update_time("temperature") == now


@pytest.mark.asyncio
async def test_get_last_update_time_none():
    """Test getting last update time for unknown device."""
    tracker = ReefPiMQTTTracker()

    assert tracker.get_last_update_time("temperature", "1") is None
    assert tracker.get_last_update_time("temperature") is None


@pytest.mark.asyncio
async def test_get_stats():
    """Test getting statistics."""
    tracker = ReefPiMQTTTracker()
    now = datetime.now(timezone.utc)

    tracker.record_mqtt_update("temperature", "1", now)
    tracker.record_mqtt_update("equipment", "2", now)

    stats = tracker.get_stats()

    assert stats["total_messages"] == 2
    assert stats["last_message_time"] == now.isoformat()
    assert "temperature" in stats["device_types_tracked"]
    assert "equipment" in stats["device_types_tracked"]
    assert "temperature" in stats["last_update_by_type"]
    assert "equipment" in stats["last_update_by_type"]


@pytest.mark.asyncio
async def test_get_stats_empty():
    """Test getting statistics with no data."""
    tracker = ReefPiMQTTTracker()

    stats = tracker.get_stats()

    assert stats["total_messages"] == 0
    assert stats["last_message_time"] is None
    assert len(stats["device_types_tracked"]) == 0
    assert len(stats["last_update_by_type"]) == 0
