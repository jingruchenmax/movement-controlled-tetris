import asyncio
from bleak import BleakClient, BleakScanner
import csv
import os
from datetime import datetime


UART_TX_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" 
SAMPLE_RATE = 20 
WINDOW_SIZE = SAMPLE_RATE 
OVERLAP_FRAMES = 10 
OUTPUT_FILE = "movement_data.csv"

is_recording = False
movement_label = None
initial_orientation = None
current_movement_data = []
movement_id = 0
previous_imu = None

def initialize_movement_id():
    if not os.path.exists(OUTPUT_FILE):
        return 0
    try:
        with open(OUTPUT_FILE, mode="r") as file:
            reader = csv.DictReader(file)
            ids = [int(row["MovementID"]) for row in reader if "MovementID" in row]
            return max(ids) + 1 if ids else 0
    except Exception as e:
        print(f"Error reading {OUTPUT_FILE}: {e}")
        return 0

def save_to_csv(data):
    write_header = not os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Timestamp",
                "AccelX",
                "AccelY",
                "AccelZ",
                "GyroX",
                "GyroY",
                "GyroZ",
                "MovementID",
                "MovementLabel"
            ],
        )
        if write_header:
            writer.writeheader()
        writer.writerows(data)

def chop_into_windows(data, window_size, overlap_frames):
    global movement_id
    num_frames = len(data)
    windows = []

    for start_idx in range(0, num_frames - window_size + 1, window_size - overlap_frames):
        window = data[start_idx : start_idx + window_size]
        for frame in window:
            frame["MovementID"] = movement_id
        windows.extend(window)
        movement_id += 1

    return windows

def start_recording():
    global is_recording, current_movement_data
    is_recording = True
    current_movement_data = [] 
    print(f"Started recording movement {movement_label} with initial orientation {initial_orientation}.")

def stop_recording():
    global is_recording, current_movement_data
    is_recording = False
    print("Stopping recording...")
    if current_movement_data:
        print("Processing recorded data...")
        windows = chop_into_windows(current_movement_data, WINDOW_SIZE, OVERLAP_FRAMES)
        save_to_csv(windows)
        print(f"Saved {len(windows)} frames to {OUTPUT_FILE}.")
        current_movement_data = []

def notification_handler(sender, data):
    global is_recording, current_movement_data, previous_imu
    message = data.decode("utf-8").strip()

    try:
        if not message.startswith("Button"):
            parts = message.split(",")
            imu_data = {
                "AccelX": float(parts[0]),
                "AccelY": float(parts[1]),
                "AccelZ": float(parts[2]),
                "GyroX": float(parts[3]),
                "GyroY": float(parts[4]),
                "GyroZ": float(parts[5]),
            }

            imu_data["Timestamp"] = datetime.now().isoformat()
            if is_recording:
                imu_data["MovementID"] = movement_id
                imu_data["MovementLabel"] = movement_label
                imu_data["InitialOrientation"] = initial_orientation
                current_movement_data.append(imu_data)
                print(f"Recording: {imu_data}")

        elif message.startswith("Button"):
            if "Pressed" in message:
                if is_recording:
                    stop_recording()  
                else:
                    start_recording()  

    except (ValueError, IndexError):
        print(f"Invalid data received: {message}")


async def setup_bluetooth():
    global movement_label, initial_orientation, movement_id

    print("Define the movement label for this session: ")
    movement_label = input("Movement Label: ").strip()

    movement_id = initialize_movement_id()

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

def main():
    asyncio.run(setup_bluetooth())

if __name__ == "__main__":
    main()
