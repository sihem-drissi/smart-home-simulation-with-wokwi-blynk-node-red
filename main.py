import network
import time
import dht
import machine
import ujson
from umqtt.simple import MQTTClient
import urequests

# Blynk Configuration
BLYNK_TEMPLATE_ID = "TMPL2gz5xDKA1"  # Replace with your Blynk Template ID
BLYNK_TEMPLATE_NAME = "smart home"    # Template Name
BLYNK_AUTH_TOKEN = "uxJY5GjNOafQtZnBfN3_R9DRGL5j8Hcc"  # Replace with your Blynk Auth Token
BLYNK_API_URL = "http://blynk.cloud/external/api"

# Pin Definitions
DHTPIN = 15
PIR_PIN = 27
LDR_PIN = 34
LED1_PIN = 16
LED2_PIN = 17
BUZZER_PIN = 26

# WiFi and MQTT Settings
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "sihemesp323FF49FLLKCO399"
MQTT_TOPIC = "sensors/data"

# Initialize Sensors and Outputs
dht_sensor = dht.DHT22(machine.Pin(DHTPIN))
pir_sensor = machine.Pin(PIR_PIN, machine.Pin.IN)
ldr_sensor = machine.ADC(machine.Pin(LDR_PIN))
ldr_sensor.atten(machine.ADC.ATTN_11DB)
led1 = machine.Pin(LED1_PIN, machine.Pin.OUT, value=0)  # Active-high LED (0 = ON, 1 = OFF)
led2 = machine.Pin(LED2_PIN, machine.Pin.OUT, value=0)  # Active-high LED (0 = ON, 1 = OFF)
buzzer = machine.Pin(BUZZER_PIN, machine.Pin.OUT)

# WiFi Connection
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        print("Connecting to WiFi...")
        time.sleep(1)
    print("Connected to WiFi:", wlan.ifconfig())

# MQTT Connection
def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
    try:
        client.connect()
        print("Connected to MQTT broker")
    except Exception as e:
        print("Failed to connect:", e)
        time.sleep(5)
        return connect_mqtt()
    return client

# Read from Blynk Virtual Pins
def blynk_read(pin):
    try:
        url = f"{BLYNK_API_URL}/get?token={BLYNK_AUTH_TOKEN}&{pin}"
        response = urequests.get(url)
        value = int(response.text.strip('[""]'))  # Parse Blynk's response
        response.close()
        return value
    except Exception as e:
        print(f"Error reading from Blynk: {e}")
        return 0

# Update the LED and Buzzer states based on Blynk input
def update_hardware_from_blynk():
    led1_status = blynk_read("V5")  # Virtual pin for LED1
    led2_status = blynk_read("V6")  # Virtual pin for LED2
    buzz_status = blynk_read("V7")  # Virtual pin for Buzzer

    # Update Outputs Based on Blynk
    led1.value(1 if led1_status == 0 else 0)  # Active-high logic (1 = ON, 0 = OFF)
    led2.value(1 if led2_status == 0 else 0)  # Active-high logic (1 = ON, 0 = OFF)
    buzzer.value(buzz_status)

    print(f"LED1: {'ON' if led1_status == 0 else 'OFF'}, LED2: {'ON' if led2_status == 0 else 'OFF'}, Buzzer: {'ON' if buzz_status else 'OFF'}")
    print(f"LED1 GPIO Value: {led1.value()}")
    print(f"LED2 GPIO Value: {led2.value()}")
    print(f"Buzzer GPIO Value: {buzzer.value()}")

# Main Function
def main():
    connect_wifi()
    mqtt_client = connect_mqtt()

    while True:
        # Read Sensor Data
        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
        except Exception as e:
            print("Error reading DHT22:", e)
            temperature = None
            humidity = None

        light_level = ldr_sensor.read()
        motion_detected = pir_sensor.value()

        # Motion Detection Logic
        if motion_detected and light_level < 1000:
            led1.on()  # Turn on LEDs (active-high)
            led2.on()
            buzzer.on()
            time.sleep(5)
            buzzer.off()
        else:
            led1.off()  # Keep LEDs off if no motion or light level is high (active-high)
            led2.off()

        # Update LED and Buzzer from Blynk
        update_hardware_from_blynk()

        # MQTT Payload
        mqtt_payload = {
            "temperature": temperature,
            "humidity": humidity,
            "light": light_level,
            "motion_status": "detected" if motion_detected else "not detected",
            "led1_status": "ON" if led1.value() == 0 else "OFF",  # Status of LED1 (active-high)
            "led2_status": "ON" if led2.value() == 0 else "OFF",  # Status of LED2 (active-high)
            "buzzer_status": "ON" if buzzer.value() else "OFF"
        }
        print("Payload:", ujson.dumps(mqtt_payload))
        try:
            mqtt_client.publish(MQTT_TOPIC, ujson.dumps(mqtt_payload))
        except OSError as e:
            print(f"Error publishing to MQTT: {e}")
            mqtt_client = connect_mqtt()

        time.sleep(5)

if __name__ == "__main__":
    main()
