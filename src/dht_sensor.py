import dht
from machine import Pin
# Om ni använder ett riktigt loggpaket, importera det här istället för "print"
import logging
from typing import Optional, Dict # För att hantera typen av returvärde

from .config import DHT_PIN

# Konfigurera basic logger (om du vill använda systemets loggning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_dht_sensor() -> Optional[dht.DHT11]:
    """Initialiserar och returnerar en DHT11-sensor på den konfigurerade pinnen."""
    try:
        pin = Pin(DHT_PIN)
        # Vi tillägger ett tyst loggmeddelande för framgångsindikering
        logging.info(f"Framgångsrik initialisering av DHT11 sensor på pin {DHT_PIN}.")
        sensor = dht.DHT11(pin)
        return sensor
    except Exception as e:
        # Använd logging istället för print() för bättre kontroll
        logging.error(f"MISSLYCKADES med att initialisera DHT11-sensor på pin {DHT_PIN}: {e}")
        return None


def read_sensor_data(sensor: dht.DHT11) -> Optional[Dict[str, float]]:
    """Läser temperatur och fuktighet från DHT11-sensorn.

    Returnerar en dictionary med 'temperature' och 'humidity',
    eller None vid fel.
    """
    try:
        # Försöker mäta först (det är bra praxis)
        logging.info("Försök läsa sensor data...")
        sensor.measure()

        # Läser värdena
        temperature = sensor.temperature()
        humidity = sensor.humidity()

        data = {
            "temperature": temperature,  # Har troligen en float-typ
            "humidity": humidity,      # Har troligen en float-typ
        }
        logging.info(f"Data läst framgångsrikt: T={temperature:.1f}°C, H={humidity:.1f}%")
        return data
    except OSError as e:
        # Detta är det vanligaste felet vid sensorer (Timeout/Dålig signal)
        logging.warning(f"Misslyckades läsa sensor data på grund av OS-fel (timeout eller dålig kontakt): {e}")
        return None
    except Exception as e:
        # Fångar alla andra oväntade fel
        logging.error(f"Fångade ett okänt fel vid läsning av sensordata: {e}")
        return None
