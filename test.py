import machine
import time

# Definiera pinnen
led_test = machine.Pin(0, machine.Pin.OUT)

print("Blinkar på GPIO 0... Om din LED lyser har du rätt pinne!")

for i in range(10):
    led_test.value(1) # På
    time.sleep(1)
    led_test.value(0) # Av
    time.sleep(1)

print("Test klart. Koppla nu ur LED-lampan och sätt dit DHT11.")