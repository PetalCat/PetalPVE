"""Global fixtures for petalpve integration."""
from unittest.mock import patch
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield

@pytest.fixture
def mock_proxmox_client():
    """Mock the ProxmoxClient."""
    with patch("custom_components.petalpve.config_flow.ProxmoxClient") as mock_client:
        instance = mock_client.return_value
        instance.connect.return_value = True
        yield mock_client
