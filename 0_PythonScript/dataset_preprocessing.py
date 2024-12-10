import pandas as pd
import numpy as np
from scipy.signal import welch

input_file = "movement_data_delta.csv"
output_file = "processed_training_data.csv"

FS = 20  # Sampling frequency (Hz)
NFFT = 64  # Length of FFT for spectral analysis


def calculate_spectral_features(data):
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])
    data = data.sort_values(by=["MovementID", "Timestamp"])

    rows = []
    for movement_id, group in data.groupby("MovementID"):
        spectral_features = compute_group_spectral_features(group)
        spectral_features["MovementID"] = movement_id
        spectral_features["MovementLabel"] = group["MovementLabel"].iloc[0]
        rows.append(spectral_features)
    return pd.DataFrame(rows)


def compute_group_spectral_features(group):
    spectral_features = {}

    for axis in ["AccelX", "AccelY", "AccelZ", "GyroX", "GyroY", "GyroZ"]:
        signal = group[axis].values
        freq, psd = welch(signal, fs=FS, nfft=NFFT, nperseg=min(len(signal), NFFT))

        spectral_features[f"TotalPower_{axis}"] = np.sum(psd)
        spectral_features[f"DominantFreq_{axis}"] = freq[np.argmax(psd)]

    return spectral_features


def preprocess_dataset():
    data = pd.read_csv(input_file)
    processed_data = calculate_spectral_features(data)
    print(f"Saving processed data to {output_file}...")
    processed_data.to_csv(output_file, index=False)


if __name__ == "__main__":
    preprocess_dataset()
