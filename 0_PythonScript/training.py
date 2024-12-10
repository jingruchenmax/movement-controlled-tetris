from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import seaborn as sns
import matplotlib.pyplot as plt
from joblib import dump
import pandas as pd

# Input and output files
input_file = "processed_training_data.csv"

# Plot confusion matrix
def plot_confusion_matrix(y_true, y_pred, model_name, labels):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)

    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues")
    plt.title(f"{model_name} Confusion Matrix")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.show()

def train_model():
    data = pd.read_csv(input_file)

    feature_columns = [col for col in data.columns if col.startswith("TotalPower") or col.startswith("DominantFreq")]
    X = data[feature_columns].values
    y = data["MovementLabel"].values

    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("Applying PCA...")
    pca = PCA(n_components=min(12, len(feature_columns)))  # Use the number of features or 12, whichever is smaller
    X_pca = pca.fit_transform(X_scaled)

    X_train, X_test, y_train, y_test = train_test_split(X_pca, y, test_size=0.2, random_state=42)

    print("Training SVM model...")
    svc = SVC(probability=True, random_state=42)
    svc.fit(X_train, y_train)
    svc_predictions = svc.predict(X_test)

    # Save models
    dump(scaler, "scaler_spectral.joblib")
    dump(pca, "pca_spectral.joblib")
    dump(svc, "svm_model_pca_spectral.joblib")
    print("Models saved successfully.")
    print(classification_report(y_test, svc_predictions))
    plot_confusion_matrix(y_test, svc_predictions, "SVC", labels=list(set(y)))


if __name__ == "__main__":
    train_model()
