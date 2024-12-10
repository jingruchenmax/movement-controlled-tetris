import asyncio
from bleak import BleakClient, BleakScanner
import tkinter as tk
from threading import Thread

# https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/libraries/bluetooth/services/nus.html
UART_TX_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" 
imu_data = {"AccelX": 0, "AccelY": 0, "AccelZ": 0, "GyroX": 0, "GyroY": 0, "GyroZ": 0, "Temp": 0}
button_state = "Released"

def update_gui():
    global imu_data, button_state
    accel_label.config(text=f"Accelerometer: X={imu_data['AccelX']} , Y={imu_data['AccelY']}, Z={imu_data['AccelZ']}")
    gyro_label.config(text=f"Gyroscope: X={imu_data['GyroX']}, Y={imu_data['GyroY']}, Z={imu_data['GyroZ']}")
    temp_label.config(text=f"Temperature: {imu_data['Temp']}")
    button_label.config(text=f"Button: {button_state}")
    root.after(100, update_gui)  # Schedule this function to run every 100ms

def notification_handler(sender, data):
    """
    Callback to handle received data.
    """
    global imu_data, button_state
    message = data.decode("utf-8").strip()
    lines = message.split("\n")  # Split multi-line messages
    for line in lines:
        print(f"Raw line: {line}")  # Debugging line
        try:
            if message.startswith("Button"):
                button_state = message
            else:
                parts = message.split(",")
                imu_data = {
                    "AccelX": float(parts[0]),
                    "AccelY": float(parts[1]),
                    "AccelZ": float(parts[2]),
                    "GyroX": float(parts[3]),
                    "GyroY": float(parts[4]),
                    "GyroZ": float(parts[5]),
                    "Temp": float(parts[6]),
                }
        except (ValueError, IndexError):
            print(f"Invalid data received: {message}")

# BLE connection and data handling
async def ble_main():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()

    # List available devices
    for i, device in enumerate(devices):
        print(f"[{i}] {device.name} ({device.address})")

    # Select a device
    device_index = int(input("Select the device index to connect: "))
    selected_device = devices[device_index]

    print(f"Connecting to {selected_device.name}...")
    async with BleakClient(selected_device.address) as client:
        print("Connected!")

        # Subscribe to the RX characteristic
        await client.start_notify(UART_TX_CHARACTERISTIC_UUID, notification_handler)

        print("Receiving data. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)  # Keep the script running
        except KeyboardInterrupt:
            print("Stopping notifications...")
            await client.stop_notify(UART_TX_CHARACTERISTIC_UUID)

    print("Disconnected.")

# Run BLE in a separate thread
def start_ble_thread():
    asyncio.run(ble_main())

# GUI
root = tk.Tk()
root.title("IMU and Button State Panel")

accel_label = tk.Label(root, text="Accelerometer: X=0.0, Y=0.0, Z=0.0", font=("Helvetica", 14))
gyro_label = tk.Label(root, text="Gyroscope: X=0.0, Y=0.0, Z=0.0", font=("Helvetica", 14))
temp_label = tk.Label(root, text="Temperature: 0.0", font=("Helvetica", 14))
button_label = tk.Label(root, text="Button: Released", font=("Helvetica", 14))

accel_label.pack(pady=10)
gyro_label.pack(pady=10)
temp_label.pack(pady=10)
button_label.pack(pady=10)

ble_thread = Thread(target=start_ble_thread, daemon=True)
ble_thread.start()


update_gui()

root.mainloop()
