#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>


#define BUTTON_PIN 3  
bool buttonState = false;
// IMU object
LSM6DS3 myIMU(I2C_MODE, 0x6A); 
#define SAMPLING_INTERVAL_US 20000  // 20ms interval for retriving and sending IMU data
uint64_t last_sample_time = 0;
#define TOTAL_BUFFER_SIZE 600
#define MAX_ACCEPTED_RANGE 16.0
#define CONVERT_G_TO_MS2 9.80665
float buffer[TOTAL_BUFFER_SIZE] = {0};
int buffer_index = 0;
// Bluetooth setup
BLEDis bledis; 
BLEUart bleuart; 
BLEBas blebas;  
BLEDfu bledfu; 

void connect_callback(uint16_t conn_handle) {
    BLEConnection* connection = Bluefruit.Connection(conn_handle);
    char central_name[32] = {0};
    connection->getPeerName(central_name, sizeof(central_name));
    Serial.print("Connected to ");
    Serial.println(central_name);
}

void disconnect_callback(uint16_t conn_handle, uint8_t reason) {
    Serial.print("Disconnected, reason = 0x");
    Serial.println(reason, HEX);
}

void startAdv(void) {
    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addTxPower();
    Bluefruit.Advertising.addService(bleuart);
    Bluefruit.ScanResponse.addName();
    Bluefruit.Advertising.restartOnDisconnect(true);
    Bluefruit.Advertising.setInterval(32, 244);
    Bluefruit.Advertising.setFastTimeout(30);
    Bluefruit.Advertising.start(0);
}

void announce_state_change(String new_state) {
    String message = "State changed to: " + new_state + "\n";
    Serial.print(message);
    bleuart.print(message);  
}

float ei_get_sign(float number) {
    return (number >= 0.0) ? 1.0 : -1.0;
}

void collectIMUData() {
    uint64_t current_time = micros();
    if (current_time - last_sample_time >= SAMPLING_INTERVAL_US) {
        last_sample_time = current_time;

        // Collect IMU data
        buffer[buffer_index] = myIMU.readFloatAccelX();
        buffer[buffer_index + 1] = myIMU.readFloatAccelY();
        buffer[buffer_index + 2] = myIMU.readFloatAccelZ();

        // Apply range clamping and unit conversion
        for (int i = 0; i < 3; i++) {
            if (fabs(buffer[buffer_index + i]) > MAX_ACCEPTED_RANGE) {
                buffer[buffer_index + i] = ei_get_sign(buffer[buffer_index + i]) * MAX_ACCEPTED_RANGE;
            }
            buffer[buffer_index + i] *= CONVERT_G_TO_MS2;
        }

        // Send raw data via Bluetooth
        String dataString = String(buffer[buffer_index], 3) + ',' +
                            String(buffer[buffer_index + 1], 3) + ',' +
                            String(buffer[buffer_index + 2], 3) + ',' +
                            String(myIMU.readFloatGyroX(), 3) + ',' +
                            String(myIMU.readFloatGyroY(), 3) + ',' +
                            String(myIMU.readFloatGyroZ(), 3) + ',' +
                            String(myIMU.readTempC(), 3) + '\n';
        bleuart.print(dataString);
        buffer_index = (buffer_index + 3) % TOTAL_BUFFER_SIZE;
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("Button + IMU + BLE");
    // Bluetooth setup
    Bluefruit.autoConnLed(true);
    Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
    Bluefruit.begin();
    Bluefruit.setTxPower(4);
    Bluefruit.Periph.setConnectCallback(connect_callback);
    Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
    bledfu.begin();
    bledis.setManufacturer("Adafruit Industries");
    Bluefruit.Security.setPIN("123456");
    bledis.begin();
    bleuart.begin();
    blebas.begin();
    blebas.write(100);
    startAdv();
    Serial.println("BLE setup complete. Waiting for connection...");
    // IMU setup
    if (!myIMU.begin()) {
        Serial.println("IMU initialization failed!");
    } else {
        Serial.println("IMU initialized successfully.");
    }
    // Button setup
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    Serial.println("Button initialized.");
}

void loop() {
    // IMU data collection
    collectIMUData();
    // Button state detection
    bool currentState = digitalRead(BUTTON_PIN);
    if (currentState != buttonState) {
        buttonState = currentState;
        if (buttonState == LOW) {
            Serial.println("Button Pressed");
            bleuart.println("Button Pressed");
        } else {
            Serial.println("Button Released");
            bleuart.println("Button Released");
        }
    }
    delay(50);
}
