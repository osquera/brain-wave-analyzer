from collections.abc import Sequence
import mne
import matplotlib.pyplot as plt
import os
import tempfile
import shutil
import uuid
from pathlib import Path
import fastapi
from fastapi import File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


def read_mne_file(file_path: str):
    """Read an MNE file and return the raw data."""
    raw = mne.io.read_raw_edf(file_path, preload=True, infer_types=True)
    return raw


def preprocess_mne_file(file_path: str, low_freq: float = 0.1, high_freq: float = 30.0):
    """Read and preprocess an MNE file."""

    # montage = mne.channels.make_standard_montage("standard_1020")

    raw = read_mne_file(file_path)

    # raw.set_montage(montage, match_case=False)

    # Use high-pass filter to remove slow drifts (0.1 Hz)
    # Use low-pass filter to remove high-frequency noise (30 Hz)
    filtered_file = raw.copy().filter(l_freq=low_freq, h_freq=high_freq)

    filtered_cut = filtered_file.crop(tmin=0, tmax=60)  # type: ignore # First 60 seconds

    return filtered_cut


def collect_and_plot_psds(
    data,
    ranges: Sequence[tuple[float | None, float | None]],
    titles: list[str],
    plot: bool = True,
):
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

    for ax, (fmin, fmax), title in zip(axes, ranges, titles):
        if fmin is not None and fmax is not None and fmin >= fmax:
            raise ValueError("fmin must be less than fmax.")

        if fmax is None and fmin is not None:
            spectrum = data.compute_psd(fmin=fmin)

        elif fmin is None and fmax is not None:
            spectrum = data.compute_psd(fmax=fmax)

        elif fmin is None and fmax is None:
            spectrum = data.compute_psd()

        else:
            spectrum = data.compute_psd(fmin=fmin, fmax=fmax)

        psds, freqs = spectrum.get_data(return_freqs=True)
        freqs_list.append(freqs)
        psd_list.append(psds)

        mean_psd = psds.mean(axis=0)
        ax.plot(freqs, mean_psd.T, color="blue")
        ax.set_title(title)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Power/Frequency (dB/Hz)")
        ax.set_xlim(
            fmin if fmin is not None else 0, fmax if fmax is not None else freqs.max()
        )
        ax.grid(True)

    plt.tight_layout()
    if plot:
        plt.show()

    return freqs_list, psd_list


def plot_power_in_bar_chart(freqs_list, psd_list, titles):
    """Plot the average power in each frequency band as a bar chart."""
    avg_psd = [psd.mean() for psd in psd_list]
    plt.bar(titles, avg_psd, color="blue")
    plt.xlabel("Frequency Band")
    plt.ylabel("Average Power (dB/Hz)")
    plt.title("Average Power in Frequency Bands")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_relative_power_bar_chart(freqs_list, psd_list, titles):
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


def process_edf_data(file_path, low_freq=0.1, high_freq=40.0):
    """Process an EDF file and return the analysis results."""
    preproc_data = preprocess_mne_file(
        file_path, low_freq=low_freq, high_freq=high_freq
    )

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

    freqs_list, psd_list = collect_and_plot_psds(
        preproc_data, freq_ranges, titles, plot=False
    )

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
async def root():
    return {"message": "Welcome to Brain Wave Analyzer API"}


@app.post("/analyze-edf/")
async def analyze_edf_file(file: UploadFile = File(...)):
    """
    Upload an EDF file and process it for EEG analysis.
    Returns analysis results and URLs to generated plots.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate file extension
    if not file.filename or not file.filename.endswith(".edf"):
        raise HTTPException(status_code=400, detail="Only .edf files are supported")

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".edf")

    try:
        # Write uploaded file to temp file
        with temp_file as f:
            shutil.copyfileobj(file.file, f)

        # Process the file using our functions
        low_freq = 0.1
        high_freq = 40.0

        # Process data
        results, freqs_list, psd_list, titles = process_edf_data(
            temp_file.name, low_freq=low_freq, high_freq=high_freq
        )

        # Generate a unique ID for this analysis
        analysis_id = str(uuid.uuid4())

        # Save the PSD plot
        plt.figure(figsize=(10, 6))
        for i, (freqs, psd, title) in enumerate(zip(freqs_list, psd_list, titles)):
            plt.subplot(3, 2, i + 1)
            plt.plot(freqs, psd.mean(axis=0), color="blue")
            plt.title(title)
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Power/Frequency (dB/Hz)")
            plt.grid(True)
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
    except Exception as e:
        # Handle any exceptions
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Delete temp file
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def main():
    """Run the example with the sample EDF file."""
    file_path = "eeg_recording.edf"
    results, freqs_list, psd_list, titles = process_edf_data(file_path)
    print("Analysis results:", results)
    plot_power_in_bar_chart(freqs_list, psd_list, titles)
    plot_relative_power_bar_chart(freqs_list, psd_list, titles)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
