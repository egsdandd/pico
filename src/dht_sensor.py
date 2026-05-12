import dht
from machine import Pin

from .config import DHT_PIN


def get_dht_sensor():
    """Initialize and return a DHT11 sensor on the configured pin."""
    try:
        pin = Pin(DHT_PIN)
        sensor = dht.DHT11(pin)
        return sensor
    except Exception as e:
        print(f"Failed to initialize DHT11 sensor on pin {DHT_PIN}: {e}")
        return None


def read_sensor_data(sensor):
    """Read both temperature and humidity from DHT11 sensor.
    
    Returns a dictionary with 'temperature' and 'humidity' keys,
    or None if the read fails.
    """
    try:
        sensor.measure()
        return {
            "temperature": sensor.temperature(),
            "humidity": sensor.humidity(),
        }
    except Exception as e:
        print(f"Failed to read sensor data: {e}")
        return None
