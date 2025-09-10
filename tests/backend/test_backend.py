"""Tests for the backend API and functions."""

import io
import sys
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backend import app, preprocess_mne_file, process_edf_data


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_edf_file() -> io.BytesIO:
    """Create a mock EDF file for testing."""
    return io.BytesIO(b"mock EDF file content")


@pytest.mark.backend
def test_analyze_edf_endpoint_success(test_client: TestClient, mock_edf_file: io.BytesIO) -> None:
    """Test the /analyze-edf/ endpoint with a successful request."""
    # Mock UUID to get consistent filenames
    test_uuid = "test-uuid"

    # Mock the process_edf_data function and all required components
    freq_bands = ["Delta", "Theta", "Alpha", "Beta", "Gamma", "Full"]
    avg_power = [0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006]
    rel_power = [0.1, 0.2, 0.3, 0.2, 0.1, 1.0]

    # Mock return values for the process_edf_data function
    mock_results = {
        "freq_bands": freq_bands,
        "average_power": avg_power,
        "relative_power": rel_power,
    }
    mock_freqs_list = [np.array([1, 2, 3]) for _ in range(6)]
    mock_psd_list = [np.array([[0.1, 0.2, 0.3]]) for _ in range(6)]
    mock_titles = freq_bands

    # Create temporary directory for static files if it doesn't exist
    Path("static/figures").mkdir(parents=True, exist_ok=True)

    # Use multiple patches to control all the test dependencies
    with (
        patch("src.backend.process_edf_data") as mock_process,
        patch("uuid.uuid4") as mock_uuid,
        patch("tempfile.NamedTemporaryFile") as mock_tempfile,
        patch("shutil.copyfileobj"),
        patch("matplotlib.pyplot.savefig"),
        patch("matplotlib.pyplot.figure"),
        patch("matplotlib.pyplot.subplot"),
        patch("matplotlib.pyplot.plot"),
        patch("matplotlib.pyplot.bar"),
        patch("matplotlib.pyplot.title"),
        patch("matplotlib.pyplot.xlabel"),
        patch("matplotlib.pyplot.ylabel"),
        patch("matplotlib.pyplot.grid"),
        patch("matplotlib.pyplot.xticks"),
        patch("matplotlib.pyplot.tight_layout"),
        patch("matplotlib.pyplot.close"),
    ):
        # Configure mocks
        mock_uuid.return_value = test_uuid
        mock_process.return_value = (mock_results, mock_freqs_list, mock_psd_list, mock_titles)

        # Configure the tempfile mock
        mock_temp_file = MagicMock()
        mock_temp_file.name = "test_temp.edf"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file

        # Make the request
        response = test_client.post(
            "/analyze-edf/",
            files={"file": ("test.edf", mock_edf_file, "application/octet-stream")},
            params={"start_time": 0},
        )

    # Check the response
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify the response structure
    assert data["analysis_id"] == str(test_uuid)
    assert data["message"] == "File processed successfully"
    assert "results" in data
    assert "freq_bands" in data["results"]
    assert "average_power" in data["results"]
    assert "relative_power" in data["results"]
    assert "plot_urls" in data["results"]

    # Verify the plot URLs
    assert data["results"]["plot_urls"]["frequency_bands_plot"] == f"/static/figures/{test_uuid}_frequency_bands.png"
    assert data["results"]["plot_urls"]["average_power_plot"] == f"/static/figures/{test_uuid}_avg_power.png"
    assert data["results"]["plot_urls"]["relative_power_plot"] == f"/static/figures/{test_uuid}_rel_power.png"

    # Verify mock was called with expected parameters
    mock_process.assert_called_once()


@pytest.mark.backend
def test_analyze_edf_endpoint_invalid_file(test_client: TestClient) -> None:
    """Test the /analyze-edf/ endpoint with an invalid file type."""
    response = test_client.post(
        "/analyze-edf/",
        files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST  # 400
    assert "Only .edf files are supported" in response.json()["detail"]


@pytest.mark.backend
def test_analyze_edf_endpoint_no_file(test_client: TestClient) -> None:
    """Test the /analyze-edf/ endpoint with no file."""
    response = test_client.post("/analyze-edf/")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # 422


@pytest.mark.backend
@patch("src.backend.read_mne_file")
def test_preprocess_mne_file(mock_read_mne: MagicMock) -> None:
    """Test the preprocess_mne_file function."""
    # Create a mock raw object
    mock_raw = MagicMock()
    mock_raw.times = np.array([0, 30, 60, 90, 120])
    mock_filtered = MagicMock()
    mock_cropped = MagicMock()

    # Set up the mocks
    mock_read_mne.return_value = mock_raw
    mock_raw.copy.return_value = mock_filtered
    mock_filtered.filter.return_value = mock_filtered
    mock_filtered.crop.return_value = mock_cropped

    # Call the function
    result = preprocess_mne_file("test.edf", start_time=30)

    # Check the result
    assert result == mock_cropped
    mock_read_mne.assert_called_once_with("test.edf")
    mock_raw.copy.assert_called_once()
    mock_filtered.filter.assert_called_once_with(l_freq=0.1, h_freq=30.0)
    mock_filtered.crop.assert_called_once_with(tmin=30, tmax=90)


@pytest.mark.backend
@patch("src.backend.preprocess_mne_file")
@patch("src.backend.collect_and_plot_psds")
def test_process_edf_data(mock_collect_psds: MagicMock, mock_preprocess: MagicMock) -> None:
    """Test the process_edf_data function."""
    # Set up the mocks
    mock_preproc_data = MagicMock()
    mock_preprocess.return_value = mock_preproc_data

    mock_freqs_list = [np.array([1, 2, 3]) for _ in range(6)]
    mock_psd_list = [np.array([[0.1, 0.2, 0.3]]) for _ in range(6)]
    mock_collect_psds.return_value = (mock_freqs_list, mock_psd_list)

    # Call the function
    results, freqs_list, psd_list, titles = process_edf_data("test.edf", start_time=30)

    # Check the results
    mock_preprocess.assert_called_once_with("test.edf", low_freq=0.1, high_freq=40.0, start_time=30)
    mock_collect_psds.assert_called()

    # Check the structure of the results
    assert "freq_bands" in results
    assert "average_power" in results
    assert "relative_power" in results
    assert len(results["freq_bands"]) == 6  # noqa: PLR2004
    assert len(results["average_power"]) == 6  # noqa: PLR2004
    assert len(results["relative_power"]) == 6  # noqa: PLR2004

    # Check that the lists were passed through
    assert freqs_list == mock_freqs_list
    assert psd_list == mock_psd_list
    assert len(titles) == 6  # noqa: PLR2004
