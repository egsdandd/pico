import machine
import dht
import time

# Konfigurera sensorn på GPIO 11
sensor = dht.DHT11(machine.Pin(0))

print("Startar mätning från DHT11...")

while True:
    try:
        # DHT-sensorer är långsamma, vi väntar lite mellan läsningarna
        time.sleep(2)
        
        # Trigga en mätning
        sensor.measure()
        
        # Hämta värdena
        temp = sensor.temperature() # Celsius
        hum = sensor.humidity()    # Luftfuktighet i %
        
        print(f"Temperatur: {temp}°C  Luftfuktighet: {hum}%")
        
    except OSError as e:
        print("Kunde inte läsa från sensorn. Kontrollera kablarna.")
    except Exception as e:
        print(f"Ett fel uppstod: {e}")