import argparse
import shutil
import sys
import tempfile
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import fastapi
import matplotlib.pyplot as plt
import mne
from fastapi import File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from mne.io.edf.edf import RawEDF

# Argument parser for log level.
parser = argparse.ArgumentParser(description="Brain Wave Analyzer Backend")
parser.add_argument(
    "--log-level",
    type=str,
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Set the logging level",
)

# Only parse arguments when running as main script, not during imports or tests
if __name__ == "__main__":
    args = parser.parse_args()
    log_level = args.log_level
else:
    # Default log level when imported as a module (e.g., during tests)
    log_level = "INFO"

# Set log level.
logger.remove()
logger.add(
    sys.stderr,
    level=log_level,
    format="<green>{time:HH:mm:ss}</green> | "
    "<blue><level>{level: <8}</level></blue> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>",
)
logger.info(f"Log level set to {log_level}.")


def read_mne_file(file_path: str) -> RawEDF:
    """Read an MNE file and return the raw data."""
    return mne.io.read_raw_edf(file_path, preload=True, infer_types=True)


def preprocess_mne_file(
    file_path: str, low_freq: float = 0.1, high_freq: float = 30.0, start_time: float = 0
) -> RawEDF:
    """Read and preprocess an MNE file."""
    # montage = mne.channels.make_standard_montage("standard_1020")

    raw = read_mne_file(file_path)

    if start_time < 0 or start_time + 60 > raw.times[-1]:
        msg = "start_time must be non-negative and within the recording duration."
        raise ValueError(msg)

    # raw.set_montage(montage, match_case=False)

    # Use high-pass filter to remove slow drifts (0.1 Hz)
    # Use low-pass filter to remove high-frequency noise (30 Hz)
    filtered_file = raw.copy().filter(l_freq=low_freq, h_freq=high_freq)

    return filtered_file.crop(tmin=start_time, tmax=start_time + 60)  # pyright: ignore[reportAttributeAccessIssue, reportReturnType]


def collect_and_plot_psds(
    data: RawEDF,
    ranges: Sequence[tuple[float | None, float | None]],
    titles: list[str],
    plot: bool = True,
) -> tuple[list, list]:
    """Plot the Power Spectral Density (PSD) for given frequency ranges."""
    n_ranges = len(ranges)
    fig, axes = plt.subplots(
        n_ranges // 2 + n_ranges % 2,
        2,
        figsize=(12, 4 * (n_ranges // 2 + n_ranges % 2)),
    )
    axes = axes.flatten()

    if n_ranges == 1:
        axes = [axes]

    freqs_list = []
    psd_list = []

    for ax, (fmin, fmax), title in zip(axes, ranges, titles, strict=False):
        if fmin is not None and fmax is not None and fmin >= fmax:
            msg = "fmin must be less than fmax."
            raise ValueError(msg)

        if fmax is None and type(fmin) is float:
            spectrum = data.compute_psd(fmin=fmin)  # pyright: ignore[reportArgumentType]

        elif fmin is None and type(fmax) is float:
            spectrum = data.compute_psd(fmax=fmax)

        elif fmin is None and fmax is None:
            spectrum = data.compute_psd()

        else:
            spectrum = data.compute_psd(fmin=fmin, fmax=fmax)  # pyright: ignore[reportArgumentType]

        psds, freqs = spectrum.get_data(return_freqs=True)
        freqs_list.append(freqs)
        psd_list.append(psds)

        mean_psd = psds.mean(axis=0)
        ax.plot(freqs, mean_psd.T, color="blue")
        ax.set_title(title)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Power/Frequency (dB/Hz)")
        ax.set_xlim(fmin if fmin is not None else 0, fmax if fmax is not None else freqs.max())
        ax.grid(True)  # noqa: FBT003

    plt.tight_layout()
    if plot:
        plt.show()

    return freqs_list, psd_list


def plot_power_in_bar_chart(psd_list: list, titles: list) -> None:
    """Plot the average power in each frequency band as a bar chart."""
    avg_psd = [psd.mean() for psd in psd_list]
    plt.bar(titles, avg_psd, color="blue")
    plt.xlabel("Frequency Band")
    plt.ylabel("Average Power (dB/Hz)")
    plt.title("Average Power in Frequency Bands")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_relative_power_bar_chart(psd_list: list, titles: list) -> None:
    """Plot the relative power in each frequency band as a bar chart."""
    total_power = sum(psd.sum() for psd in psd_list)
    rel_psd = [psd.sum() / total_power for psd in psd_list]
    plt.bar(titles, rel_psd, color="blue")
    plt.xlabel("Frequency Band")
    plt.ylabel("Relative Power")
    plt.title("Relative Power in Frequency Bands")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def process_edf_data(
    file_path: str, low_freq: float = 0.1, high_freq: float = 40.0, start_time: float = 0
) -> tuple[dict[str, list[str] | list[float]], list, list, list]:
    """Process an EDF file and return the analysis results."""
    preproc_data = preprocess_mne_file(file_path, low_freq=low_freq, high_freq=high_freq, start_time=start_time)

    freq_ranges = [
        (0.5, 4.0),
        (4.0, 8.0),
        (8.0, 13.0),
        (13.0, 30.0),
        (30.0, high_freq),
        (low_freq, high_freq),
    ]
    titles = [
        "Delta (0.5-4 Hz)",
        "Theta (4-8 Hz)",
        "Alpha (8-13 Hz)",
        "Beta (13-30 Hz)",
        "Gamma (30+ Hz)",
        "Full Spectrum (0.5+ Hz)",
    ]

    freqs_list, psd_list = collect_and_plot_psds(preproc_data, freq_ranges, titles, plot=False)

    # Prepare the data for return
    avg_psd = [float(psd.mean()) for psd in psd_list]
    total_power = sum(psd.sum() for psd in psd_list)
    rel_psd = [float(psd.sum() / total_power) for psd in psd_list]

    # Create a results dictionary
    results = {
        "freq_bands": titles,
        "average_power": avg_psd,
        "relative_power": rel_psd,
    }

    return results, freqs_list, psd_list, titles


# Create the FastAPI application
app = fastapi.FastAPI(title="Brain Wave Analyzer API")

# Set up CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a directory for static files if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
figures_dir = static_dir / "figures"
figures_dir.mkdir(exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Brain Wave Analyzer API"}


@app.post("/analyze-edf/")
async def analyze_edf_file(
    file: Annotated[UploadFile, File()],
    start_time: float = 0,
) -> dict[str, str | dict[str, list[str] | list[float] | dict[str, str]]]:
    """Upload an EDF file and process it for EEG analysis.

    Args:
        file: The EDF file to analyze
        start_time: The start time in seconds for analysis (default: 0)

    Returns analysis results and URLs to generated plots.

    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate file extension
    if not file.filename or not file.filename.endswith(".edf"):
        raise HTTPException(status_code=400, detail="Only .edf files are supported")

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".edf") as temp_file:
        try:
            # Write uploaded file to temp file
            with temp_file as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e!s}")
            raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {e!s}") from e
    try:
        # Process the file using our functions
        low_freq = 0.1
        high_freq = 40.0

        logger.debug(f"Processing file {temp_file.name} with start_time={start_time}")

        # Process data
        results, freqs_list, psd_list, titles = process_edf_data(
            temp_file.name, low_freq=low_freq, high_freq=high_freq, start_time=start_time
        )

        # Generate a unique ID for this analysis
        analysis_id = str(uuid.uuid4())

        # Save the PSD plot
        plt.figure(figsize=(10, 6))
        for i, (freqs, psd, title) in enumerate(zip(freqs_list, psd_list, titles, strict=False)):
            plt.subplot(3, 2, i + 1)
            plt.plot(freqs, psd.mean(axis=0), color="blue")
            plt.title(title)
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Power/Frequency (dB/Hz)")
            plt.grid(visible=True)
        plt.tight_layout()
        psd_filename = f"{analysis_id}_frequency_bands.png"
        plt.savefig(figures_dir / psd_filename)
        plt.close()

        # Create power bar chart
        plt.figure(figsize=(10, 6))
        plt.bar(titles, results["average_power"], color="blue")
        plt.xlabel("Frequency Band")
        plt.ylabel("Average Power (dB/Hz)")
        plt.title("Average Power in Frequency Bands")
        plt.xticks(rotation=45)
        plt.tight_layout()
        power_filename = f"{analysis_id}_avg_power.png"
        plt.savefig(figures_dir / power_filename)
        plt.close()

        # Create relative power bar chart
        plt.figure(figsize=(10, 6))
        plt.bar(titles, results["relative_power"], color="blue")
        plt.xlabel("Frequency Band")
        plt.ylabel("Relative Power")
        plt.title("Relative Power in Frequency Bands")
        plt.xticks(rotation=45)
        plt.tight_layout()
        rel_power_filename = f"{analysis_id}_rel_power.png"
        plt.savefig(figures_dir / rel_power_filename)
        plt.close()

    except Exception as e:
        # Handle any exceptions
        logger.error(f"Error processing file: {e!s}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Error processing file: {e!s}") from e

    else:
        # Return the results with URLs to the plots
        return {
            "analysis_id": analysis_id,
            "message": "File processed successfully",
            "results": {
                **results,
                "plot_urls": {
                    "frequency_bands_plot": f"/static/figures/{psd_filename}",
                    "average_power_plot": f"/static/figures/{power_filename}",
                    "relative_power_plot": f"/static/figures/{rel_power_filename}",
                },
            },
        }
    finally:
        # Delete temp file
        temp_path = Path(temp_file.name)
        if temp_path.exists():
            temp_path.unlink()


def main() -> None:
    """Run the example with the sample EDF file."""
    file_path = "eeg_recording.edf"
    results, freqs_list, psd_list, titles = process_edf_data(file_path)
    logger.info(f"Analysis results: {results}")
    plot_power_in_bar_chart(psd_list, titles)
    plot_relative_power_bar_chart(psd_list, titles)


if __name__ == "__main__":
    import os

    import uvicorn

    # Default to localhost unless explicitly set to production mode
    host = "0.0.0.0" if os.getenv("PRODUCTION_MODE") == "1" else "127.0.0.1"  # noqa: S104

    logger.info(f"Starting server on {host}:8000")
    uvicorn.run(app, host=host, port=8000)
