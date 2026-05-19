import socket
import gc
from time import sleep_ms, ticks_ms, ticks_diff
from . import led_control

# Global server socket och konfiguration
_server_socket = None
_EAGAIN = 11
_latest_measurement = None

# Globala variabler för CPU-load (Idletid-metoden)
_last_cpu_check = ticks_ms()
_idle_ticks = 0
_cpu_load = 0

# Enkel HTML-mall med platshållare för sensorvärden och systemstatus
_HTML_BODY_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }
        h1 {
            color: #333;
        }
        .button-group {
            margin: 20px 0;
        }
        a {
            text-decoration: none;
        }
        button {
            padding: 10px 20px;
            margin: 5px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            color: white;
        }
        .on-button {
            background-color: #4CAF50;
        }
        .on-button:hover {
            background-color: #45a049;
        }
        .off-button {
            background-color: #f44336;
        }
        .off-button:hover {
            background-color: #da190b;
        }
        .toggle-button {
            background-color: #2196F3;
        }
        .toggle-button:hover {
            background-color: #0b7dda;
        }
        .status {
            margin-top: 20px;
            padding: 10px;
            background-color: #e8f4f8;
            border-left: 4px solid #2196F3;
        }
    </style>
</head>
<body>
    <h1>Pico W LED Control</h1>
    <div class="button-group">
        <a href="/led/on"><button class="on-button">Turn LED On</button></a>
        <a href="/led/off"><button class="off-button">Turn LED Off</button></a>
        <a href="/led/toggle"><button class="toggle-button">Toggle LED</button></a>
    </div>
    <div class="status">
        <p>Click a button to control the LED.</p>
        <p><strong>Latest measurement:</strong> __MEASUREMENT__</p>
        <p><strong>System Status:</strong> CPU Load: __CPU__% | RAM: __RAM_USED__KB / __RAM_TOTAL__KB</p>
    </div>
</body>
</html>"""


def report_idle_time(ms):
    """Anropas från main-loopen när processorn sover/idlar för att kunna beräkna CPU-load."""
    global _idle_ticks
    _idle_ticks += ms


def _calculate_cpu_and_mem():
    """Räknar ut aktuell CPU load och RAM-status för MicroPython."""
    global _last_cpu_check, _idle_ticks, _cpu_load
    
    # 1. Beräkna CPU Load baserat på förfluten tid kontra rapporterad idletid
    now = ticks_ms()
    total_elapsed = ticks_diff(now, _last_cpu_check)
    
    if total_elapsed >= 2000:  # Uppdatera bara mätningen varannan sekund
        if total_elapsed > 0:
            active_time = total_elapsed - _idle_ticks
            # Säkra att vi hamnar mellan 0% och 100%
            _cpu_load = max(0, min(100, int((active_time / total_elapsed) * 100)))
        
        # Återställ inför nästa mätperiod
        _last_cpu_check = now
        _idle_ticks = 0
        
    # 2. Hämta RAM-minne (omvandlat till Kilobytes)
    gc.collect()  # Tvinga städning för att få en rättvisande bild av ledigt minne
    mem_free = gc.mem_free() // 1024
    mem_alloc = gc.mem_alloc() // 1024
    mem_total = mem_free + mem_alloc
    
    return _cpu_load, mem_alloc, mem_total


def update_latest_measurement(temperature, humidity, timestamp=None, local_time=None):
    """Sparar senaste sensorvärde för visning i webgränssnittet."""
    global _latest_measurement
    _latest_measurement = {
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": timestamp,
        "local_time": local_time,
    }


def _render_html_body():
    """Renderar HTML med senaste tillgängliga mätvärde och systemstatus."""
    if _latest_measurement is None:
        measurement_text = "No sensor data yet"
    else:
        temperature = _latest_measurement.get("temperature", "?")
        humidity = _latest_measurement.get("humidity", "?")
        local_time = _latest_measurement.get("local_time")
        timestamp = _latest_measurement.get("timestamp")
        if local_time:
            measurement_text = "{} C, {} % RH at {}".format(temperature, humidity, local_time)
        elif timestamp is not None:
            measurement_text = "{} C, {} % RH (ts: {})".format(temperature, humidity, timestamp)
        else:
            measurement_text = "{} C, {} % RH".format(temperature, humidity)

    # Hämta aktuell CPU-load och minnesanvändning
    cpu, mem_used, mem_total = _calculate_cpu_and_mem()

    # Bygg ihop HTML:en genom att ersätta platshållarna
    html = _HTML_BODY_TEMPLATE.replace("__MEASUREMENT__", measurement_text)
    html = html.replace("__CPU__", str(cpu))
    html = html.replace("__RAM_USED__", str(mem_used))
    html = html.replace("__RAM_TOTAL__", str(mem_total))
    
    return html


def _build_http_response(body):
    """Bygger HTTP-svar med rätt Content-Length."""
    body_bytes = body.encode('utf-8')
    header = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(len(body_bytes))
    return header.encode('utf-8') + body_bytes


def _read_request(conn, max_attempts=10, wait_ms=10):
    """Läser en HTTP-request från non-blocking socket och returnerar text eller tom sträng."""
    request = b""
    attempts = 0

    while attempts < max_attempts:
        try:
            chunk = conn.recv(1024)
            if not chunk:
                break
            request += chunk
            attempts = 0
        except OSError as exc:
            if getattr(exc, "errno", None) == _EAGAIN:
                attempts += 1
                sleep_ms(wait_ms)
                continue
            raise

    if not request:
        return ""

    # Tar bort keyword-argumentet 'errors' då MicroPython inte stöder det i alla releaser
    return request.decode('utf-8')


def initialize_server(port=80):
    """Initialisera HTTP-servern på specificerad port."""
    global _server_socket
    
    try:
        _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_socket.bind(('0.0.0.0', port))
        _server_socket.listen(5)
        _server_socket.setblocking(0)  # 0 istället för False (MicroPython standard)
        print(f"HTTP server initialized on port {port}")
        return True
    except Exception as e:
        print(f"Failed to initialize HTTP server on port {port}: {e}")
        _server_socket = None
        return False


def handle_http_requests():
    """Hantera inkommande HTTP-requests non-blocking. Anropas regelbundet från main-loopen."""
    global _server_socket
    
    if _server_socket is None:
        return
    
    try:
        conn, addr = _server_socket.accept()
        conn.setblocking(0)  # 0 istället för False för att undvika Keyword-felet

        try:
            request = _read_request(conn)

            if not request:
                return

            # Hantera LED-kommandon baserat på URL
            if '/led/on' in request:
                led_control.turn_on()
                print("LED ON via HTTP")
            elif '/led/off' in request:
                led_control.turn_off()
                print("LED OFF via HTTP")
            elif '/led/toggle' in request:
                led_control.toggle()
                print("LED TOGGLE via HTTP")

            response = _build_http_response(_render_html_body())
            conn.sendall(response)

        except OSError as e:
            if getattr(e, "errno", None) != _EAGAIN:
                print(f"HTTP request error: {e}")
        except Exception as e:
            print(f"HTTP request error: {e}")
            import traceback
            traceback.print_exc()  # Visar exakt radnummer i konsolen om något ändå skulle krascha
        finally:
            try:
                conn.close()
            except Exception:
                pass

    except OSError as e:
        # Ingen connection väntande - helt normalt för non-blocking socket
        if getattr(e, "errno", None) != _EAGAIN:
            print(f"HTTP server socket error: {e}")
    except Exception as e:
        print(f"HTTP server error: {e}")


def shutdown_server():
    """Stäng ner HTTP-servern."""
    global _server_socket
    
    if _server_socket is not None:
        try:
            _server_socket.close()
            _server_socket = None
            print("HTTP server closed")
        except Exception as e:
            print(f"Error closing HTTP server: {e}")