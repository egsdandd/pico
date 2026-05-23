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
from .mqtt_client import (
    create_client,
    subscribe,
    set_callback,
    check_msg,
    disconnect as mqtt_disconnect,
    ping as mqtt_ping,
)
from .time_sync import format_local_time, sync_ntp_utc_time
from .wifi_manager import do_connect, get_wifi_info
from . import http_server
def _connect_wifi(log_success=False):
    """Ansluter till Wi-Fi med exponential backoff vid misslyckande."""
    print("Connecting to Wi-Fi...")
    max_attempts = wifi_connect_retries if wifi_connect_retries else 3
    backoff_base = 2

    for attempt in range(1, max_attempts + 1):
        try:
            if do_connect():
                if log_success:
                    wifi_info = get_wifi_info()
                    if wifi_info:
                        print("Wi-Fi connected:", wifi_info)
                    else:
                        print("Wi-Fi connected!")
                return True
        except Exception as exc:
            print(f"Wi-Fi connect attempt {attempt} failed: {exc}")

        if attempt < max_attempts:
            wait = backoff_base**attempt
            print(f"Waiting {wait}s before retrying Wi-Fi connect (attempt {attempt + 1}/{max_attempts})...")
            sleep(wait)

    print("Failed to connect to Wi-Fi after retries.")
    return False


def initialize_dht_sensor():
    """Initierar DHT11-sensorn. Avbryter programmet om det misslyckas."""
    print("Initializing DHT11 sensor using the configured pin...")
    dht_sensor = get_dht_sensor()
    if dht_sensor is None:
        print("Failed to initialize DHT11 sensor, exiting.")
        raise SystemExit

    print("DHT11 sensor initialized successfully!")
    return dht_sensor


def initialize_mqtt_client():
    """Skapar och ansluter MQTT-klienten samt sätter prenumerationer."""
    print(f"Connecting to MQTT broker, client ID: {MQTT_CLIENT_ID}...")
    max_retries = 3
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            mqtt_client = create_client(MQTT_CLIENT_ID)
            set_callback(mqtt_client, _handle_led_command)
            mqtt_client.connect()
            print("MQTT broker connected successfully!")

            # Registrera prenumeration direkt vid uppstart
            subscribe(mqtt_client, COMMAND_TOPIC)
            print(f"Subscribed to {COMMAND_TOPIC} at startup!")

            return mqtt_client
        except Exception as exc:
            print(f"MQTT connect attempt {attempt}/{max_retries} failed: {exc}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay}s...")
                sleep(retry_delay)

    print(f"MQTT broker connection failed after {max_retries} attempts - continuing without MQTT")
    return None


def _handle_led_command(topic, msg):
    """Hanterar inkommande LED-kommandon (ON/OFF/TOGGLE) från Mosquitto."""
    try:
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


def _ensure_connections(mqtt_client):
    """Säkerställer att både Wi-Fi och MQTT är uppkopplade. Återansluter vid behov."""
    # Om Wi-Fi har dött, återanslut och synka tid
    if not do_connect():
        print("Wi-Fi connection lost! Reconnecting...")
        if _connect_wifi():
            try:
                sync_ntp_utc_time(timezone_offset)
            except Exception as exc:
                print(f"Failed to resync time: {exc}")
        else:
            return None

    # Om vi vill ha MQTT men klienten saknas eller har dött
    if mqtt_client is None:
        mqtt_client = initialize_mqtt_client()
    else:
        # Ett snabbt ping-test avslöjar om socketen har dött i bakgrunden
        try:
            mqtt_ping(mqtt_client)
        except Exception:
            print("MQTT connection verified dead. Attempting reconnect...")
            mqtt_disconnect(mqtt_client)
            mqtt_client = initialize_mqtt_client()

    return mqtt_client


def publish_sensor_data_loop(dht_sensor, mqtt_client):
    """Huvudloop för att läsa sensorer, ta emot kommandon och skicka data."""
    print("Starting sensor read loop...")
    get_led_pin()
    turn_off()
    print("LED control is command-driven; default blinking is disabled")

    last_publish_time = 0
    last_sensor_read_time = 0
    last_connection_check_time = 0  # Håller koll på Wi-Fi-kontroller (var 10:e sekund)
    last_ping_time = time()
    latest_data = None

    while True:
        current_time = time()

        # 1. Kontrollera nätverksanslutningar mer sällan för att slippa logg-spam
        if current_time - last_connection_check_time >= 10:
            mqtt_client = _ensure_connections(mqtt_client)
            last_connection_check_time = current_time
        
        # 1.5 Hantera inkommande HTTP-requests (non-blocking)
        try:
            http_server.handle_http_requests()
        except Exception as exc:
            print(f"Error handling HTTP request: {exc}")

        # 2. Lyssna efter inkommande LED-kommandon (körs snabbt varje varv)
        if mqtt_client is not None:
            try:
                check_msg(mqtt_client)
            except Exception as exc:
                print(f"Error checking MQTT messages: {exc}")
                mqtt_disconnect(mqtt_client)
                mqtt_client = None

            # Skicka Keep-Alive (Ping) var 30:e sekund
            if current_time - last_ping_time >= 30:
                try:
                    mqtt_ping(mqtt_client)
                    last_ping_time = current_time
                    print("MQTT ping sent")
                except Exception:
                    mqtt_disconnect(mqtt_client)
                    mqtt_client = None

        # 3. Läs av sensordata baserat på SENSOR_POLL_INTERVAL
        if current_time - last_sensor_read_time >= SENSOR_POLL_INTERVAL:
            data = read_sensor_data(dht_sensor)
            last_sensor_read_time = current_time
            if data:
                latest_data = data
                print(f"Sensor: Temperature={data['temperature']}°C, Humidity={data['humidity']}%")

        # 4. Publicera data till mäklaren baserat på SENSOR_PUBLISH_INTERVAL
        if latest_data and current_time - last_publish_time >= SENSOR_PUBLISH_INTERVAL:
            packet_timestamp = int(current_time)
            packet_local_time = format_local_time(packet_timestamp, timezone_offset)
            http_server.update_latest_measurement(
                latest_data["temperature"],
                latest_data["humidity"],
                timestamp=packet_timestamp,
                local_time=packet_local_time,
            )

            if mqtt_client is not None:
                try:
                    payload = json.dumps(
                        {
                            "temperature": latest_data["temperature"],
                            "humidity": latest_data["humidity"],
                            "timestamp": packet_timestamp,
                        }
                    )
                    mqtt_client.publish(SENSOR_TOPIC, payload)
                    print(f"Published to {SENSOR_TOPIC}: {payload}")
                    print(
                        f"Local publish time: {packet_local_time} - "
                        f"Packet Time {packet_local_time} ({packet_timestamp})"
                    )
                    last_publish_time = current_time
                except Exception as exc:
                    print(f"MQTT publish failed: {exc}")
                    mqtt_disconnect(mqtt_client)
                    mqtt_client = None
            else:
                print("MQTT not available - offline data:", latest_data)
                last_publish_time = current_time  # Förhindrar logg-spamming i offline-läge

        # Behåll denna kort (0.05) för att Picon ska höra LED-kommandona direkt när de skickas
        http_server.report_idle_time(50)
        sleep(0.05)


def run():
    """Programmets startpunkt."""
    # Säkerställ Wi-Fi och tid vid absolut första uppstart
    while not _connect_wifi(log_success=True):
        print("Initial Wi-Fi connection failed. Retrying in 30s...")
        sleep(30)

    try:
        sync_ntp_utc_time(timezone_offset)
    except Exception as exc:
        print(f"Initial time sync failed: {exc}")

    # Starta HTTP-servern
    http_server.initialize_server(port=80)

    # Starta tjänsterna
    dht_sensor = initialize_dht_sensor()
    mqtt_client = initialize_mqtt_client()

    # Gå in i den oändliga loopen
    publish_sensor_data_loop(dht_sensor, mqtt_client)