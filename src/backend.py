import mne

def read_mne_file(file_path: str):
    """Read an MNE file and return the raw data."""
    raw = mne.io.read_raw_edf(file_path, preload=True)
    return raw

def filter_data(raw, l_freq: float | None, h_freq: float | None):
    """Apply a band-pass filter to the raw data."""
    raw.filter(l_freq=l_freq, h_freq=h_freq)
    return raw

def preprocess_mne_file(file_path: str):
    """Read and preprocess an MNE file."""
    raw = read_mne_file(file_path)
    
    # Use high-pass filter to remove slow drifts (0.1 Hz)
    raw = filter_data(raw, l_freq=0.1, h_freq=None)

    # Use low-pass filter to remove high-frequency noise (30 Hz)
    raw = filter_data(raw, l_freq=None, h_freq=30.0)




if __name__ == "__main__":
    file_path = "eeg_recording.edf"
    raw_data = read_mne_file(file_path)
    print(raw_data.info)