try:
    from umqtt.simple import MQTTClient  # pyright: ignore[reportMissingImports]
except ImportError:
    MQTTClient = None

try:
    import usocket as socket
except ImportError:
    import socket

from . import config


def subscribe(client, topic, qos=0):
    """Subscribe to a topic with the given client."""
    try:
        client.subscribe(topic, qos)
    except AttributeError:
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


def ping(client):
    """Ping the MQTT client to keep connection alive."""
    try:
        client.ping()
    except AttributeError:
        pass
    except Exception as exc:
        print("Error while pinging MQTT client:", exc)


def create_client(client_id, server=None, user=None, password=None, port=1883, keepalive=60):
    """Create and return an instance of the official MicroPython MQTTClient."""
    mqtt_server = server or config.mqtt_server
    mqtt_user = user or config.mqtt_user
    mqtt_password = password or config.mqtt_password

    if MQTTClient is None:
        raise RuntimeError(
            "umqtt.simple MQTTClient could not be imported. "
            "Please ensure micropython-umqtt.simple is installed on the Pico."
        )

    return MQTTClient(
        client_id,
        mqtt_server,
        port=port,
        user=mqtt_user,
        password=mqtt_password,
        keepalive=keepalive,
    )