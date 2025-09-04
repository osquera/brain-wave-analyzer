from collections.abc import Sequence
import mne
import matplotlib.pyplot as plt


def read_mne_file(file_path: str):
    """Read an MNE file and return the raw data."""
    raw = mne.io.read_raw_edf(file_path, preload=True)
    return raw


def preprocess_mne_file(file_path: str, low_freq: float = 0.1, high_freq: float = 30.0):
    """Read and preprocess an MNE file."""
    raw = read_mne_file(file_path)

    # Use high-pass filter to remove slow drifts (0.1 Hz)
    # Use low-pass filter to remove high-frequency noise (30 Hz)
    filtered_file = raw.copy().filter(l_freq=low_freq, h_freq=high_freq)

    filtered_cut = filtered_file.crop(tmin=0, tmax=60)  # type: ignore # First 60 seconds

    return filtered_cut


def collect_and_plot_psds(
    data, ranges: Sequence[tuple[float | None, float | None]], titles: list[str], plot: bool = True
):
    """Plot the Power Spectral Density (PSD) for given frequency ranges."""

    n_ranges = len(ranges)
    fig, axes = plt.subplots(n_ranges // 2 + n_ranges % 2, 2, figsize=(12, 4 * (n_ranges // 2 + n_ranges % 2)))
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
        ax.set_xlim(fmin if fmin is not None else 0, fmax if fmax is not None else freqs.max())
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

def main():
    file_path = "eeg_recording.edf"

    low_freq = 0.1
    high_freq = 40.0

    preproc_data = preprocess_mne_file(file_path, low_freq=low_freq, high_freq=high_freq)

    freq_ranges = [(0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, high_freq), (low_freq, high_freq)]
    titles = [
        "Delta (0.5-4 Hz)",
        "Theta (4-8 Hz)",
        "Alpha (8-13 Hz)",
        "Beta (13-30 Hz)",
        "Gamma (30+ Hz)",
        "Full Spectrum (0.5+ Hz)",
    ]

    freqs_list, psd_list = collect_and_plot_psds(preproc_data, freq_ranges, titles)
    plot_power_in_bar_chart(freqs_list, psd_list, titles)
    plot_relative_power_bar_chart(freqs_list, psd_list, titles)



if __name__ == "__main__":
    main()
