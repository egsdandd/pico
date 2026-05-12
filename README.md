# Pico DHT11 MQTT Sensor Service

MicroPython project for Raspberry Pi Pico W that:

- connects to Wi-Fi,
- synchronizes time with NTP,
- reads temperature and humidity from a DHT11 sensor,
- publishes sensor data to an MQTT topic,
- listens for LED commands over MQTT.

## Features

- Periodic sensor read and publish loop
- MQTT publish to sensor topic
- MQTT subscribe for command-driven onboard LED control (`on`, `off`, `toggle`)
- Runtime configuration output (without printing secret values)
- Modular structure (`wifi`, `time sync`, `sensor`, `mqtt`, `device service`)

## Tech Stack

- MicroPython (Raspberry Pi Pico W)
- DHT11 sensor
- MQTT broker (port 1883)

## Project Structure

```text
.
|-- main.py
|-- src/
|   |-- config.py
|   |-- device_service.py
|   |-- dht_sensor.py
|   |-- led_control.py
|   |-- mqtt_client.py
|   |-- secrets.py
|   |-- time_sync.py
|   |-- wifi_manager.py
|   `-- __init__.py
`-- test_import.py
```

## Configuration

Set credentials and broker details in `src/secrets.py`:

```python
ssid = "<your-wifi-ssid>"
password = "<your-wifi-password>"
mqtt_user = "<your-mqtt-username>"
mqtt_password = "<your-mqtt-password>"
mqtt_server = "<your-mqtt-broker-ip-or-hostname>"
```

Runtime topics are derived from `src/config.py`:

- Sensor publish topic: `lnu/iot/dd222mk/sensor`
- LED command topic: `lnu/iot/dd222mk/command/led`

## MQTT Message Formats

### Published sensor payload

```json
{
  "temperature": 23,
  "humidity": 55,
  "timestamp": 1778600000
}
```

### LED command payload

```json
{
  "action": "on"
}
```

Valid `action` values: `on`, `off`, `toggle`.

## Run

Example with `mpremote` from your PC:

```bash
python -m mpremote connect COM3 run main.py
```

## Troubleshooting

### `ImportError: no module named 'umqtt'`

Install MQTT library on the Pico W in REPL:

```python
import mip
mip.install("umqtt.simple")
import machine
machine.reset()
```

### `AssertionError: Subscribe callback is not set`

Ensure callback is registered before `subscribe` (already handled in current `src/device_service.py`).

## Security Notes

- Do not commit real credentials.
- Keep `src/secrets.py` and local `.env` files out of version control.

## License (MIT)

Copyright (c) 2026 Dan-Håkan Davall

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Metadata

- Author: Dan-Håkan Davall
- Created: 2026-05-12
- Version: 1.0.0
