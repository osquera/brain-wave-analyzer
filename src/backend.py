from collections.abc import Sequence
from tkinter import N
import mne
import matplotlib.pyplot as plt


def read_mne_file(file_path: str):
    """Read an MNE file and return the raw data."""
    raw = mne.io.read_raw_edf(file_path, preload=True)
    return raw


def preprocess_mne_file(file_path: str):
    """Read and preprocess an MNE file."""
    raw = read_mne_file(file_path)

    # Use high-pass filter to remove slow drifts (0.1 Hz)
    # Use low-pass filter to remove high-frequency noise (30 Hz)
    filtered_file = raw.copy().filter(l_freq=0.1, h_freq=30.0)

    filtered_cut = filtered_file.crop(tmin=0, tmax=60)  # type: ignore # First 60 seconds

    return filtered_cut


def plot_psds(
    data, ranges: Sequence[tuple[float | None, float | None]], titles: list[str]
):
    """Plot the Power Spectral Density (PSD) for given frequency ranges."""

    n_ranges = len(ranges)
    fig, axes = plt.subplots(1, n_ranges, figsize=(5 * n_ranges, 4))

    if n_ranges == 1:
        axes = [axes]

    for ax, (fmin, fmax), title in zip(axes, ranges, titles):
        if fmin is None and fmax is None:
            raise ValueError("At least one of fmin or fmax must be specified.")
        if fmin is not None and fmax is not None and fmin >= fmax:
            raise ValueError("fmin must be less than fmax.")
        
        if fmax is None:
            spectrum = data.compute_psd(fmin=fmin)

        elif fmin is None:
            spectrum = data.compute_psd(fmax=fmax)

        else:
            spectrum = data.compute_psd(fmin=fmin, fmax=fmax)

            
        psds, freqs = spectrum.get_data(return_freqs=True)

        mean_psd = psds.mean(axis=0)
        ax.plot(freqs, mean_psd.T, color="blue")
        ax.set_title(title)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Power/Frequency (dB/Hz)")
        ax.set_xlim(fmin if fmin is not None else 0, fmax if fmax is not None else freqs.max())
        ax.grid(True)

    plt.tight_layout()
    plt.show()


def main():
    file_path = "eeg_recording.edf"
    preproc_data = preprocess_mne_file(file_path)

    freq_ranges = [(0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, None)]
    titles = [
        "Delta (0.5-4 Hz)",
        "Theta (4-8 Hz)",
        "Alpha (8-13 Hz)",
        "Beta (13-30 Hz)",
        "Gamma (30+ Hz)",
    ]

    plot_psds(preproc_data, freq_ranges, titles)


if __name__ == "__main__":
    main()
