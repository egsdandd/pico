# Pico DHT11 MQTT Sensor Service

MicroPython project for Raspberry Pi Pico W that:

- connects to Wi-Fi,
- synchronizes time with NTP,
- reads temperature and humidity from a DHT11 sensor,
- publishes sensor data to an MQTT topic (when available),
- listens for LED commands over MQTT (when available),
- gracefully handles MQTT unavailability - continues sensing without publishing.

## Features

- Periodic sensor read and publish loop (5s poll / 15s publish)
- MQTT publish to sensor topic
- MQTT subscribe for command-driven onboard LED control (`on`, `off`, `toggle`)
- MQTT keep-alive ping every 30 seconds
- Automatic reconnection attempts for Wi-Fi and MQTT
- Runtime configuration output (without printing secret values)
- Modular structure (`wifi`, `time sync`, `sensor`, `mqtt`, `device service`)

### HTTP Web UI

- The Pico W runs a small non-blocking HTTP server on port 80 that serves a simple
  web page with buttons to control the onboard LED (`Turn LED On`, `Turn LED Off`, `Toggle LED`).
- The web page displays the latest sensor measurement (temperature and humidity) and the
  timestamp used in the published MQTT packet. The page is re-rendered on each request,
  so opening the page or pressing a button will show the most recent value.
- The HTTP server is non-blocking and integrated into the main device loop so it
  doesn't interfere with sensor polling or MQTT handling.

## Tech Stack

- MicroPython (Raspberry Pi Pico W)
- DHT11 sensor
- MQTT broker (port 1883)

## Project Structure

```text
.
|-- main.py
|-- lib/
|   |-- ssl.mpy
|   `-- umqtt/
|       `-- simple.mpy
|-- src/
|   |-- config.py
|   |-- device_service.py
|   |-- dht_sensor.py
|   |-- http_server.py
|   |-- led_control.py
|   |-- mqtt_client.py
|   |-- secrets.py
|   |-- time_sync.py
|   |-- wifi_manager.py
|   `-- __init__.py
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

**Note:** The Pico will run continuously even if MQTT is unavailable, logging sensor data to the console. When MQTT comes back online, it automatically reconnects.

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

### MQTT connection failures (`ECONNRESET`, timeouts)

If MQTT broker is unavailable, the Pico will continue operating in offline mode:

- Sensor readings continue every 5 seconds
- Data is logged to console but not published
- The Pico automatically attempts reconnection every 10 seconds
- When MQTT comes back online, it reconnects and resumes publishing

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
