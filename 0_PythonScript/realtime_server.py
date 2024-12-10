import asyncio
from bleak import BleakClient, BleakScanner
from sklearn.preprocessing import StandardScaler
from joblib import load
import pandas as pd
from collections import deque
from scipy.signal import welch, find_peaks
import numpy as np
import socket
import threading

WINDOW_SIZE = 20  
OVERLAP_SIZE = 10  
FS = 20  # Sampling frequency (Hz)
NFFT = 64  # Length of FFT for spectral analysis
THRESHOLD_X = 3  # Threshold for leaning left/right
THRESHOLD_Y = 3  # Threshold for leaning forward/backward
STABILITY_THRESHOLD = 3.0  # Threshold for stability in accelerometer data
TCP_HOST = "127.0.0.1"  
TCP_PORT = 65432  
UART_TX_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" 
CONFIDENCE_THRESHOLD = 0.7

rolling_buffer = deque(maxlen=WINDOW_SIZE) 
current_state = "Neutral" 
svc_model = None 
scaler = None  
pca = None  
tcp_clients = []  

def start_tcp_server():
    global tcp_clients

    def handle_client(client_socket):
        while True:
            try:
                client_socket.recv(1024)
            except:
                tcp_clients.remove(client_socket)
                client_socket.close()
                break

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen(5)
    print(f"TCP server started on {TCP_HOST}:{TCP_PORT}")

    while True:
        client_socket, addr = server.accept()
        print(f"TCP Client connected: {addr}")
        tcp_clients.append(client_socket)
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()


def notification_handler(sender, data):
    global rolling_buffer
    message = data.decode("utf-8").strip()
    try:
        parts = message.split(",")
        current_data = {
            "AccelX": float(parts[0]),
            "AccelY": float(parts[1]),
            "AccelZ": float(parts[2]),
            "GyroX": float(parts[3]),
            "GyroY": float(parts[4]),
            "GyroZ": float(parts[5]),
        }

        rolling_buffer.append(current_data)
        if len(rolling_buffer) == WINDOW_SIZE:
            classify_state()

    except (ValueError, IndexError):
        if "Button Pressed" in message:
            broadcast_tcp("Button Pressed")
            print("Button Pressed")
        elif "Button Released" in message:
            broadcast_tcp("Button Released")
            print("Button Released")

def broadcast_tcp(message):
    global tcp_clients
    for client_socket in tcp_clients:
        try:
            client_socket.sendall((message + "\n").encode())
        except:
            tcp_clients.remove(client_socket)

def update_state(new_state):
    global current_state
    if(current_state=="shake" and new_state=="shake"): 
        print(f"Cannot Shake again until returning to Neutral.")
    elif not(current_state=="Leaning Forward" and new_state=="Leaning Forward"):
        current_state = new_state
        broadcast_tcp(current_state)
        print(f"Updated State: {current_state}")

def compute_spectral_features(df):
    spectral_features = {}
    for axis in ["AccelX", "AccelY", "AccelZ", "GyroX", "GyroY", "GyroZ"]:
        signal = df[axis].values
        freq, psd = welch(signal, fs=FS, nfft=NFFT, nperseg=min(len(signal), NFFT))
        spectral_features[f"TotalPower_{axis}"] = np.sum(psd)
        spectral_features[f"DominantFreq_{axis}"] = freq[np.argmax(psd)]
    return spectral_features

def classify_state():
    global rolling_buffer, svc_model, scaler, pca
    df = pd.DataFrame(list(rolling_buffer))
    spectral_features = compute_spectral_features(df)
    feature_vector = np.array(list(spectral_features.values())).reshape(1, -1)
    X_scaled = scaler.transform(feature_vector)
    X_pca = pca.transform(X_scaled)

    if hasattr(svc_model, "predict_proba"):
        probabilities = svc_model.predict_proba(X_pca)[0]
        max_confidence = max(probabilities)
        prediction = svc_model.classes_[np.argmax(probabilities)]
    else:
        decision_scores = svc_model.decision_function(X_pca)[0]
        max_confidence = abs(decision_scores) / max(abs(decision_scores)) 
        prediction = svc_model.classes_[np.argmax(decision_scores)]

    if max_confidence >= CONFIDENCE_THRESHOLD:
        if prediction == "idle":
            process_threshold_based_detection()
        else:
            update_state("shake")

def process_threshold_based_detection():
    global rolling_buffer
    most_recent = rolling_buffer[-1]
    accel_x = most_recent["AccelX"]
    accel_y = most_recent["AccelY"]
    accel_stability = np.std([d["AccelX"] for d in rolling_buffer]) + \
                      np.std([d["AccelY"] for d in rolling_buffer])
    if accel_stability > STABILITY_THRESHOLD:
        return
    if accel_x < -THRESHOLD_X:
        update_state("Leaning Left")
    elif accel_x > THRESHOLD_X:
        update_state("Leaning Right")
    elif accel_y > THRESHOLD_Y:
        update_state("Leaning Forward")
    elif accel_y < -THRESHOLD_Y:
        update_state("Leaning Backward")
    else:
        update_state("Neutral")

def load_models():
    global svc_model, scaler, pca
    svc_model = load("svm_model_pca_spectral.joblib")
    scaler = load("scaler_spectral.joblib")
    pca = load("pca_spectral.joblib")
    print("Models loaded successfully.")

async def setup_bluetooth():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()

    for i, device in enumerate(devices):
        print(f"[{i}] {device.name} ({device.address})")

    device_index = int(input("Select the device index to connect: "))
    selected_device = devices[device_index]

    print(f"Connecting to {selected_device.name}...")
    async with BleakClient(selected_device.address) as client:
        print("Connected!")

        await client.start_notify(UART_TX_CHARACTERISTIC_UUID, notification_handler)

        print("Receiving data. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping notifications...")
            await client.stop_notify(UART_TX_CHARACTERISTIC_UUID)


# Main function
if __name__ == "__main__":
    load_models()
    tcp_server_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_server_thread.start()
    asyncio.run(setup_bluetooth())
