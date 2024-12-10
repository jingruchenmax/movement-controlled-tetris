import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Load the resampled dataset
def load_resampled_dataset(file_path):
    data = pd.read_csv(file_path)
    grouped = data.groupby("MovementID")
    X = [group[["AccelX", "AccelY", "AccelZ"]].mean(axis=0).values for _, group in grouped]
    y = grouped["MovementLabel"].first().values

    return pd.DataFrame(X, columns=["AccelX", "AccelY", "AccelZ"]), pd.Series(y)

def visualize_dataset_3d(X, y):
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    labels = y.unique()
    colors = ['blue', 'orange'] 
    
    for label, color in zip(labels, colors):
        idx = y == label
        ax.scatter(X.loc[idx, "AccelX"], 
                   X.loc[idx, "AccelY"], 
                   X.loc[idx, "AccelZ"], 
                   label=label, color=color, alpha=0.7)

    ax.set_title("3D Visualization of The Dataset")
    ax.set_xlabel("Accelerometer X")
    ax.set_ylabel("Accelerometer Y")
    ax.set_zlabel("Accelerometer Z")
    ax.legend(title="Movement Label")
    plt.show()

if __name__ == "__main__":
    file = "movement_data_delta.csv"
    X, y = load_resampled_dataset(file)
    y = y.replace({"idle": "idle", "shake": "shake"})  # Ensure correct label names
    visualize_dataset_3d(X, y)
