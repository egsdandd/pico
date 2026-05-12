from .secrets import mqtt_password, mqtt_server, mqtt_user, password, ssid

timezone_offset = 2
wifi_connect_timeout = 10

# Application-specific configuration
# Student identifier used in MQTT topic namespace
STUDENT_ID = "dd222mk"

# MQTT
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "lnu/iot"

# Sensor / publishing
SENSOR_PUBLISH_INTERVAL = 15  # seconds between published sensor readings
DHT_PIN = 11

# Computed defaults (can be overridden by code if needed)
SENSOR_TOPIC = f"{MQTT_TOPIC_PREFIX}/{STUDENT_ID}/sensor"
COMMAND_TOPIC = f"{MQTT_TOPIC_PREFIX}/{STUDENT_ID}/command/led"
MQTT_CLIENT_ID = f"dht11-sensor-{STUDENT_ID}"
SENSOR_POLL_INTERVAL = 5  # seconds between sensor polls (sleep time in loop)


def print_config():
	"""Print selected runtime configuration (avoid printing secrets)."""
	try:
		from .secrets import mqtt_server, mqtt_user, ssid
	except Exception:
		mqtt_server = None
		mqtt_user = None
		ssid = None

	print("--- Runtime configuration ---")
	print("STUDENT_ID:", STUDENT_ID)
	if mqtt_server:
		print("MQTT server:", mqtt_server)
	print("MQTT port:", MQTT_PORT)
	if mqtt_user:
		print("MQTT user:", mqtt_user)
	if ssid:
		print("Wi-Fi SSID:", ssid)
	print("SENSOR_TOPIC:", SENSOR_TOPIC)
	print("MQTT_CLIENT_ID:", MQTT_CLIENT_ID)
	print("SENSOR_PUBLISH_INTERVAL:", SENSOR_PUBLISH_INTERVAL)
	print("SENSOR_POLL_INTERVAL:", SENSOR_POLL_INTERVAL)
	print("DHT_PIN:", DHT_PIN)
	print("-----------------------------")