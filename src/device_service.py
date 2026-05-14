import json
from time import sleep, time

from .config import (
    timezone_offset,
    wifi_connect_retries,
    SENSOR_PUBLISH_INTERVAL,
    SENSOR_TOPIC,
    COMMAND_TOPIC,
    MQTT_CLIENT_ID,
    SENSOR_POLL_INTERVAL,
)
from .dht_sensor import get_dht_sensor, read_sensor_data
from .led_control import get_led_pin, turn_on, turn_off, toggle
from .mqtt_client import create_client, subscribe, set_callback, check_msg, disconnect as mqtt_disconnect
from .wifi_manager import disconnect as wifi_disconnect
from .time_sync import format_local_time, sync_ntp_utc_time
from .wifi_manager import do_connect


def _connect_wifi():
    print("Connecting to Wi-Fi...")
    # Retry a few times before giving up to avoid crashing the whole program on transient failures.
    max_attempts = wifi_connect_retries if wifi_connect_retries else 3
    backoff_base = 2

    for attempt in range(1, max_attempts + 1):
        try:
            if do_connect():
                print("Wi-Fi connected!")
                return True
        except OSError as exc:
            print(f"Wi-Fi connect attempt {attempt} failed: {exc}")
        except Exception as exc:
            print(f"Unexpected error during Wi-Fi connect attempt {attempt}: {exc}")

        if attempt < max_attempts:
            wait = backoff_base ** attempt
            print(f"Waiting {wait}s before retrying Wi-Fi connect (attempt {attempt + 1}/{max_attempts})...")
            try:
                from time import sleep

                sleep(wait)
            except Exception:
                pass

    print("Failed to connect to Wi-Fi after retries.")
    return False


def _start_sensor_service():
    dht_sensor = initialize_dht_sensor()
    mqtt_client = initialize_mqtt_client()
    publish_sensor_data_loop(dht_sensor, mqtt_client)


def connect_wifi_and_sync_time():
    if not _connect_wifi():
        # Let caller decide how to proceed; return False to indicate failure.
        return False

    sync_ntp_utc_time(timezone_offset)
    return True


def connect_wifi():
    """Connect to Wi‑Fi only. Raises SystemExit on failure."""
    _connect_wifi()


def sync_time_local():
    """Sync RTC in UTC and print local time using timezone_offset."""
    sync_ntp_utc_time(timezone_offset)


def initialize_dht_sensor():
    print("Initializing DHT11 sensor using the configured pin...")
    dht_sensor = get_dht_sensor()
    if dht_sensor is None:
        print("Failed to initialize DHT11 sensor, exiting.")
        raise SystemExit

    print("DHT11 sensor initialized successfully!")
    return dht_sensor


def initialize_mqtt_client():
    print(f"Connecting to MQTT broker, client ID: {MQTT_CLIENT_ID}...")
    try:
        mqtt_client = create_client(MQTT_CLIENT_ID)
        mqtt_client.connect()
        print("MQTT broker connected successfully!")
        return mqtt_client
    except Exception as exc:
        print(f"Failed to connect to MQTT broker: {exc}")
        raise SystemExit


def _handle_led_command(topic, msg):
    """Handle incoming LED command messages from MQTT."""
    try:
        import json
        payload = json.loads(msg.decode("utf-8"))
        action = payload.get("action", "").lower()
        
        if action == "on":
            print("LED command: ON")
            turn_on()
        elif action == "off":
            print("LED command: OFF")
            turn_off()
        elif action == "toggle":
            print("LED command: TOGGLE")
            toggle()
        else:
            print(f"Unknown LED action: {action}")
    except Exception as exc:
        print(f"Error handling LED command: {exc}")


def publish_sensor_data_loop(dht_sensor, mqtt_client):
    print(f"Starting sensor read loop, publishing to {SENSOR_TOPIC}...")
    
    # Subscribe to LED command topic
    set_callback(mqtt_client, _handle_led_command)
    subscribe(mqtt_client, COMMAND_TOPIC)
    print(f"Subscribed to {COMMAND_TOPIC}")

    try:
        last_publish_time = 0
        last_sensor_read_time = 0
        latest_data = None
        get_led_pin()
        turn_off()
        print("LED control is command-driven; default blinking is disabled")

        while True:
            current_time = time()

            # Check for incoming MQTT messages
            check_msg(mqtt_client)

            if current_time - last_sensor_read_time >= SENSOR_POLL_INTERVAL:
                data = read_sensor_data(dht_sensor)
                last_sensor_read_time = current_time
                if data:
                    latest_data = data
                    temperature = data["temperature"]
                    humidity = data["humidity"]
                    print(f"Sensor: Temperature={temperature}°C, Humidity={humidity}%")

            if latest_data and current_time - last_publish_time >= SENSOR_PUBLISH_INTERVAL:
                try:
                    payload = json.dumps(
                        {
                            "temperature": latest_data["temperature"],
                            "humidity": latest_data["humidity"],
                            "timestamp": int(current_time),
                        }
                    )
                    mqtt_client.publish(SENSOR_TOPIC, payload)
                    print(f"Published to {SENSOR_TOPIC}: {payload}")
                    print(f"Local publish time: {format_local_time(int(current_time), timezone_offset)}")
                    last_publish_time = current_time
                except Exception as exc:
                    print(f"Failed to publish to MQTT: {exc}")

            sleep(0.5)
    except Exception as exc:
        print("Publish loop terminated with exception:", exc)
    finally:
        print("Shutting down MQTT client and Wi‑Fi...")
        try:
            mqtt_disconnect(mqtt_client)
        except Exception as exc:
            print("Error disconnecting MQTT client:", exc)

        try:
            wifi_disconnect()
        except Exception as exc:
            print("Error disconnecting Wi‑Fi:", exc)


def run():
    # Try to connect and sync time; if it fails, keep retrying with a delay instead of exiting.
    while True:
        try:
            ok = connect_wifi_and_sync_time()
            if ok:
                break
            else:
                print("connect_wifi_and_sync_time() failed; retrying in 30s...")
                from time import sleep

                sleep(30)
        except Exception as exc:
            print("Error during Wi-Fi connect/sync:", exc)
            from time import sleep

            sleep(30)

    _start_sensor_service()


def start_mqtt_service():
    """Initialize DHT sensor and MQTT client and start the publish loop."""
    _start_sensor_service()