import mne

def read_mne_file(file_path: str):
    """Read an MNE file and return the raw data."""
    raw = mne.io.read_raw_edf(file_path, preload=True)
    return raw


if __name__ == "__main__":
    file_path = "eeg_recording.edf"
    raw_data = read_mne_file(file_path)
    print(raw_data.info)