"""
Tests for the autoinput functionality.
"""
import pytest
from unittest.mock import Mock, patch
from src.core.autoinput import AutoInput
from src.data.sandi import default_user_input
from src.utils.logger import get_logger

logger = get_logger(__name__)

@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = Mock()
    page.locator = Mock(return_value=Mock())
    page.get_by_role = Mock(return_value=Mock())
    page.get_by_label = Mock(return_value=Mock())
    page.wait_for_load_state = Mock()
    return page

@pytest.fixture
def sample_user_input():
    """Create a complete user input dictionary using defaults as base."""
    return default_user_input.copy()

@pytest.fixture
def mock_weather_codes():
    """Create mock weather code mappings."""
    return {
        'obs': {'zulkifli ramadhan': 'Zulkifli Ramadhan'},
        'ww': {'cerah': '00'},
        'w1w2': {'hujan ringan': '1'},
        'awan_lapisan': {'CU': '1'},
        'arah_angin': {'NE': '45'},
        'ci': {'1': '1'},
        'cm': {'0': '0'},
        'ch': {'0': '0'},
    }

def test_autoinput_initialization(mock_page, sample_user_input, mock_weather_codes):
    """Test AutoInput class initialization."""
    autoinput = AutoInput(
        mock_page,
        sample_user_input,
        mock_weather_codes['obs'],
        mock_weather_codes['ww'],
        mock_weather_codes['w1w2'],
        mock_weather_codes['awan_lapisan'],
        mock_weather_codes['arah_angin'],
        mock_weather_codes['ci'],
        mock_weather_codes['cm'],
        mock_weather_codes['ch']
    )
    
    assert autoinput.page == mock_page
    assert autoinput.user_input == sample_user_input
    assert autoinput.obs == mock_weather_codes['obs']

@patch('src.core.autoinput.AutoInput.fill_form')
def test_autoinput_fill_form(mock_fill_form, mock_page, sample_user_input, mock_weather_codes):
    """Test form filling functionality."""
    autoinput = AutoInput(
        mock_page,
        sample_user_input,
        mock_weather_codes['obs'],
        mock_weather_codes['ww'],
        mock_weather_codes['w1w2'],
        mock_weather_codes['awan_lapisan'],
        mock_weather_codes['arah_angin'],
        mock_weather_codes['ci'],
        mock_weather_codes['cm'],
        mock_weather_codes['ch']
    )
    
    autoinput.fill_form()
    mock_fill_form.assert_called_once()

def test_autoinput_error_handling(mock_page, sample_user_input, mock_weather_codes):
    """Test error handling in AutoInput."""
    mock_page.locator.side_effect = Exception("Test error")
    
    autoinput = AutoInput(
        mock_page,
        sample_user_input,
        mock_weather_codes['obs'],
        mock_weather_codes['ww'],
        mock_weather_codes['w1w2'],
        mock_weather_codes['awan_lapisan'],
        mock_weather_codes['arah_angin'],
        mock_weather_codes['ci'],
        mock_weather_codes['cm'],
        mock_weather_codes['ch']
    )
    
    with pytest.raises(Exception) as exc_info:
        autoinput.fill_form()
    
    assert "Test error" in str(exc_info.value)

def test_autoinput_input_validation(mock_page, sample_user_input, mock_weather_codes):
    """Test that Playwright errors surface instead of being swallowed."""
    mock_page.locator.side_effect = RuntimeError("selector not found")

    autoinput = AutoInput(
        mock_page,
        sample_user_input,
        mock_weather_codes['obs'],
        mock_weather_codes['ww'],
        mock_weather_codes['w1w2'],
        mock_weather_codes['awan_lapisan'],
        mock_weather_codes['arah_angin'],
        mock_weather_codes['ci'],
        mock_weather_codes['cm'],
        mock_weather_codes['ch']
    )

    with pytest.raises(RuntimeError, match="selector not found"):
        autoinput.fill_form() 