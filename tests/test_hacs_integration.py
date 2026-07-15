"""Unit tests for the Home Assistant HACS custom component."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Define mock classes that can be subclassed
class MockSensorEntity:
    @property
    def extra_state_attributes(self):
        return None

class MockBinarySensorEntity:
    pass

class MockCamera:
    def __init__(self) -> None:
        self.hass = MagicMock()

class MockCoordinatorEntity:
    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator

class MockConfigFlow:
    def __init__(self, *args, **kwargs) -> None:
        self.hass = None
        self.context = {}
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        # Consume any keyword arguments (like domain=DOMAIN) passed during subclassing
        pass

    async def async_set_unique_id(self, unique_id, *, raise_on_progress=True):
        return unique_id
    def _abort_if_unique_id_configured(self, *args, **kwargs):
        pass
    def async_create_entry(self, *, title, data, description_placeholders=None):
        return {"type": "create_entry", "title": title, "data": data}
    def async_show_form(self, *, step_id, data_schema, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "errors": errors or {}, "data_schema": data_schema}

# Setup sys.modules mocks before importing the custom component
ha_mock = MagicMock()
sys.modules["homeassistant"] = ha_mock

config_entries = MagicMock()
config_entries.ConfigFlow = MockConfigFlow
ha_mock.config_entries = config_entries
sys.modules["homeassistant.config_entries"] = config_entries

ha_mock.const = MagicMock()
sys.modules["homeassistant.const"] = ha_mock.const
sys.modules["homeassistant.const"].Platform = MagicMock()

ha_mock.core = MagicMock()
sys.modules["homeassistant.core"] = ha_mock.core

ha_mock.helpers = MagicMock()
sys.modules["homeassistant.helpers"] = ha_mock.helpers
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()

# Update coordinator mocks
update_coord = MagicMock()
update_coord.CoordinatorEntity = MockCoordinatorEntity
class UpdateFailedException(Exception):
    pass
update_coord.UpdateFailed = UpdateFailedException
ha_mock.helpers.update_coordinator = update_coord
sys.modules["homeassistant.helpers.update_coordinator"] = update_coord

# Components mocks
ha_mock.components = MagicMock()
sys.modules["homeassistant.components"] = ha_mock.components
sys.modules["homeassistant.components.sensor"] = MagicMock()
sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity
sys.modules["homeassistant.components.binary_sensor"] = MagicMock()
sys.modules["homeassistant.components.binary_sensor"].BinarySensorEntity = MockBinarySensorEntity
sys.modules["homeassistant.components.camera"] = MagicMock()
sys.modules["homeassistant.components.camera"].Camera = MockCamera
sys.modules["homeassistant.components.camera"].CameraEntityFeature = MagicMock()
sys.modules["homeassistant.components.ffmpeg"] = MagicMock()
sys.modules["homeassistant.components.panel_custom"] = MagicMock()

# Now import the custom component modules
from custom_components.baby_monitor import async_setup_entry, async_unload_entry
from custom_components.baby_monitor.binary_sensor import BabyBinary, BabySceneBinary
from custom_components.baby_monitor.camera import BabyCamera
from custom_components.baby_monitor.config_flow import BabyMonitorConfigFlow
from custom_components.baby_monitor.sensor import BabySensor, BabySceneSensor


def test_sensor_entities():
    coordinator = MagicMock()
    coordinator.data = {
        "respiration_rate": 45.0,
        "sleep_state": "asleep",
        "cry_reason": "none",
        "scene": {
            "description": "Baby is sleeping peacefully",
            "position": "back",
            "items": [{"item": "pacifier", "hazard": False}],
        },
        "health": {
            "llm": "ok",
            "llm_source": "litellm",
        }
    }
    entry = MagicMock()
    entry.entry_id = "test_entry"

    # Test standard sensor
    sensor = BabySensor(coordinator, entry, "respiration_rate", "Respiration rate [ML]", "bpm")
    assert sensor.native_value == 45.0
    assert sensor.extra_state_attributes is None

    # Test scene sensor
    scene_sensor = BabySceneSensor(coordinator, entry, "scene", "Latest status [LLM]", "description", "mdi:cctv")
    assert scene_sensor.native_value == "Baby is sleeping peacefully"
    assert scene_sensor.extra_state_attributes == coordinator.data["scene"]

    # Test items list mapping
    items_sensor = BabySceneSensor(coordinator, entry, "scene", "Crib items [LLM]", "items", "mdi:cube-scan")
    assert items_sensor.native_value == "pacifier"

    # Test health mapping
    health_sensor = BabySceneSensor(coordinator, entry, "health", "Sys LLM health", "llm", "mdi:robot-outline")
    assert health_sensor.native_value == "litellm"


def test_binary_sensor_entities():
    coordinator = MagicMock()
    coordinator.data = {
        "present": True,
        "crying": False,
        "scene": {
            "face_covered": False,
            "baby_visible": True,
        }
    }
    entry = MagicMock()
    entry.entry_id = "test_entry"

    # Test standard binary sensor
    binary = BabyBinary(coordinator, entry, "present", "Baby present [ML]", "occupancy")
    assert binary.is_on is True

    # Test scene binary sensor
    scene_binary = BabySceneBinary(coordinator, entry, "scene", "Face covered [LLM]", "face_covered", "problem")
    assert scene_binary.is_on is False


def test_camera_entity():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "host": "https://192.168.1.10",
        "stream_url": ""
    }

    # Default AAC stream URL fallback
    camera = BabyCamera(entry)
    assert asyncio.run(camera.stream_source()) == "rtsp://192.168.1.10:8554/cam?video=copy&audio=aac"

    # Custom stream URL
    entry.data["stream_url"] = "rtsp://custom:8554/live"
    camera_custom = BabyCamera(entry)
    assert asyncio.run(camera_custom.stream_source()) == "rtsp://custom:8554/live"


@patch("custom_components.baby_monitor.config_flow.async_create_clientsession")
def test_config_flow_success(mock_session_factory):
    hass = MagicMock()
    flow = BabyMonitorConfigFlow()
    flow.hass = hass

    # Mock success response
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    user_input = {
        "host": "https://192.168.1.10",
        "token": "valid_token",
        "stream_url": ""
    }

    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "create_entry"
    assert result["title"] == "Baby Monitor"
    assert result["data"]["host"] == "https://192.168.1.10"
    assert result["data"]["token"] == "valid_token"


@patch("custom_components.baby_monitor.config_flow.async_create_clientsession")
def test_config_flow_auth_failure(mock_session_factory):
    hass = MagicMock()
    flow = BabyMonitorConfigFlow()
    flow.hass = hass

    # Mock 401 Unauthorized response
    mock_resp = AsyncMock()
    mock_resp.status = 401
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    user_input = {
        "host": "https://192.168.1.10",
        "token": "invalid_token"
    }

    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_auth"


@patch("custom_components.baby_monitor.config_flow.async_create_clientsession")
def test_config_flow_connection_error(mock_session_factory):
    hass = MagicMock()
    flow = BabyMonitorConfigFlow()
    flow.hass = hass

    # Mock exception during request
    mock_session = AsyncMock()
    mock_session.get.side_effect = Exception("Connection refused")
    mock_session_factory.return_value = mock_session

    user_input = {
        "host": "https://192.168.1.10",
        "token": "token"
    }

    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


@patch("custom_components.baby_monitor.config_flow.async_create_clientsession")
def test_config_flow_non_200_failure(mock_session_factory):
    hass = MagicMock()
    flow = BabyMonitorConfigFlow()
    flow.hass = hass

    mock_resp = AsyncMock()
    mock_resp.status = 500
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    result = asyncio.run(
        flow.async_step_user({"host": "https://192.168.1.10", "token": "token"})
    )
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


class FakeCoordinator:
    def __init__(self, *args, update_method=None, **kwargs) -> None:
        self._update_method = update_method
        self.data = {}

    async def async_config_entry_first_refresh(self):
        self.data = await self._update_method()


@patch("custom_components.baby_monitor._async_register_panel", new_callable=AsyncMock)
@patch("custom_components.baby_monitor.async_create_clientsession")
@patch("custom_components.baby_monitor.DataUpdateCoordinator", new=FakeCoordinator)
def test_setup_unload_entry_lifecycle(mock_session_factory, _mock_panel):
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "entry_1"
    entry.data = {"host": "https://192.168.1.10", "token": "token"}

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json = AsyncMock(return_value={"baby/status/present": {"value": True}})
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    assert asyncio.run(async_setup_entry(hass, entry)) is True
    assert hass.data["baby_monitor"][entry.entry_id].data["present"] is True

    assert asyncio.run(async_unload_entry(hass, entry)) is True
    assert entry.entry_id not in hass.data["baby_monitor"]
