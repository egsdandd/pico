try:
    from umqtt.simple import MQTTClient  # pyright: ignore[reportMissingImports]
except ImportError:
    MQTTClient = None

try:
    import usocket as socket
except ImportError:
    import socket

from . import config


def _encode_remaining_length(length):
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        encoded.append(digit)
        if length == 0:
            break
    return encoded


def _encode_string(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return len(value).to_bytes(2, "big") + value


class _FallbackMQTTClient:
    def __init__(self, client_id, server, port=1883, user=None, password=None, keepalive=60):
        self.client_id = client_id.encode("utf-8") if isinstance(client_id, str) else client_id
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.sock = None

    def _recv_exact(self, size):
        if self.sock is None:
            raise OSError("MQTT socket is not connected")

        sock = self.sock
        if hasattr(sock, "settimeout"):
            sock.settimeout(5)
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise OSError("MQTT connection closed by broker")
            data += chunk
        return data

    def connect(self):
        addr_info = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock = socket.socket()
        sock = self.sock
        if hasattr(sock, "settimeout"):
            sock.settimeout(5)
        sock.connect(addr_info)

        variable_header = _encode_string("MQTT")
        variable_header += b"\x04"
        connect_flags = 0x02  # clean session
        if self.user is not None:
            connect_flags |= 0x80
        if self.password is not None:
            connect_flags |= 0x40
        variable_header += bytes([connect_flags])
        variable_header += self.keepalive.to_bytes(2, "big")

        payload = _encode_string(self.client_id)
        if self.user is not None:
            payload += _encode_string(self.user)
        if self.password is not None:
            payload += _encode_string(self.password)

        remaining_length = len(variable_header) + len(payload)
        packet = b"\x10" + _encode_remaining_length(remaining_length) + variable_header + payload
        sock.send(packet)

        try:
            response = self._recv_exact(4)
            if response[0] != 0x20 or response[1] != 0x02 or response[3] != 0x00:
                raise OSError("MQTT connection failed")
        except Exception:
            self.sock.close()
            self.sock = None
            raise

    def publish(self, topic, payload, retain=False, qos=0):
        if qos != 0:
            raise NotImplementedError("Only QoS 0 is supported")

        if isinstance(topic, str):
            topic = topic.encode("utf-8")
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        fixed_header = 0x30 | (0x01 if retain else 0x00)
        variable_header = len(topic).to_bytes(2, "big") + topic
        remaining_length = len(variable_header) + len(payload)
        packet = bytes([fixed_header]) + _encode_remaining_length(remaining_length) + variable_header + payload
        if self.sock is None:
            raise OSError("MQTT socket is not connected")
        self.sock.send(packet)

    def subscribe(self, topic, qos=0):
        # Build SUBSCRIBE packet (packet id 1)
        if isinstance(topic, str):
            topic = topic.encode("utf-8")
        packet_id = 1
        variable_header = packet_id.to_bytes(2, "big")
        payload = len(topic).to_bytes(2, "big") + topic + bytes([qos & 0x03])
        remaining_length = len(variable_header) + len(payload)
        packet = b"\x82" + _encode_remaining_length(remaining_length) + variable_header + payload
        if self.sock is None:
            raise OSError("MQTT socket is not connected")
        self.sock.send(packet)

    def set_callback(self, callback):
        self.callback = callback

    def check_msg(self):
        # Try to non-blocking read incoming PUBLISH messages and call callback(topic, msg)
        if getattr(self, "sock", None) is None:
            return
        sock = self.sock
        # Use a small timeout for non-blocking behavior
        orig_timeout = None
        try:
            if hasattr(sock, "gettimeout"):
                orig_timeout = sock.gettimeout()
            if hasattr(sock, "settimeout"):
                sock.settimeout(0.01)
            # Read first byte of fixed header
            try:
                hdr = sock.recv(1)
            except Exception:
                return
            if not hdr:
                return
            packet_type = hdr[0] >> 4
            # Decode remaining length
            mul = 1
            remaining = 0
            while True:
                b = sock.recv(1)
                if not b:
                    return
                val = b[0]
                remaining += (val & 127) * mul
                mul *= 128
                if (val & 128) == 0:
                    break

            body = b""
            to_read = remaining
            while to_read > 0:
                chunk = sock.recv(to_read)
                if not chunk:
                    break
                body += chunk
                to_read -= len(chunk)

            # If it's a PUBLISH (packet_type == 3), parse topic and payload
            if packet_type == 3 and body:
                # topic length
                if len(body) < 2:
                    return
                topic_len = int.from_bytes(body[0:2], "big")
                if len(body) < 2 + topic_len:
                    return
                topic = body[2:2 + topic_len].decode("utf-8")
                payload = body[2 + topic_len:]
                if hasattr(self, "callback") and callable(getattr(self, "callback")):
                    try:
                        self.callback(topic, payload)
                    except Exception:
                        pass

        finally:
            try:
                if hasattr(sock, "settimeout") and orig_timeout is not None:
                    sock.settimeout(orig_timeout)
            except Exception:
                pass

    def disconnect(self):
        """Close the underlying socket if open."""
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


def subscribe(client, topic, qos=0):
    """Subscribe to a topic with the given client."""
    try:
        client.subscribe(topic, qos)
    except NotImplementedError:
        print(f"Warning: Client does not support subscribe for {topic}")


def set_callback(client, callback):
    """Set a callback function for incoming messages."""
    try:
        client.set_callback(callback)
    except AttributeError:
        pass


def check_msg(client):
    """Check for incoming messages."""
    try:
        client.check_msg()
    except AttributeError:
        pass


def disconnect(client):
    """Disconnect the given MQTT client if it supports disconnect()."""
    try:
        client.disconnect()
    except AttributeError:
        pass
    except Exception as exc:
        print("Error while disconnecting MQTT client:", exc)


def create_client(client_id, server=None, user=None, password=None, port=1883, keepalive=60):
    mqtt_server = server or config.mqtt_server
    mqtt_user = user or config.mqtt_user
    mqtt_password = password or config.mqtt_password

    if MQTTClient is not None:
        return MQTTClient(
            client_id,
            mqtt_server,
            port=port,
            user=mqtt_user,
            password=mqtt_password,
            keepalive=keepalive,
        )

    return _FallbackMQTTClient(
        client_id,
        mqtt_server,
        port=port,
        user=mqtt_user,
        password=mqtt_password,
        keepalive=keepalive,
    )
