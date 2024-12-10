import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from mpl_toolkits.mplot3d import Axes3D

def load_resampled_dataset(file_path):
    data = pd.read_csv(file_path)
    grouped = data.groupby("MovementID")
    X = [group[["TotalPower_AccelX","DominantFreq_AccelX","TotalPower_AccelY","DominantFreq_AccelY","TotalPower_AccelZ","DominantFreq_AccelZ","TotalPower_GyroX","DominantFreq_GyroX","TotalPower_GyroY","DominantFreq_GyroY","TotalPower_GyroZ","DominantFreq_GyroZ"]].values.flatten() for _, group in grouped]    
    y = grouped["MovementLabel"].first().values

    return pd.DataFrame(X), pd.Series(y)


def visualize_dataset(X, y, labels):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    pca = PCA()
    X_pca = pca.fit_transform(X_scaled)
    plt.figure(figsize=(10, 7))
    colors = ['blue', 'orange']
    for label, color in zip(labels, colors):
        idx = y == label
        plt.scatter(X_pca[idx, 0], X_pca[idx, 1], color=color, label=label, alpha=0.7)

    plt.title("Visualization of The Dataset (# PCA Features = 2)")
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.legend(title="Movement Label")
    plt.grid()
    plt.show()


if __name__ == "__main__":
    resampled_file = "processed_training_data.csv"
    X, y = load_resampled_dataset(resampled_file)
    y = pd.Series(y).map({"idle": "idle", "shake": "shake"}).astype("category")
    label_names = ["idle", "shake"]
    visualize_dataset(X, y, label_names)