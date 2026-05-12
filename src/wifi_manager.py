import machine
import network
import time

from . import config


def _status_name(status_code):
    status_map = {
        getattr(network, "STAT_IDLE", None): "STAT_IDLE",
        getattr(network, "STAT_CONNECTING", None): "STAT_CONNECTING",
        getattr(network, "STAT_GOT_IP", None): "STAT_GOT_IP",
        getattr(network, "STAT_NO_AP_FOUND", None): "STAT_NO_AP_FOUND",
        getattr(network, "STAT_CONNECT_FAIL", None): "STAT_CONNECT_FAIL",
        getattr(network, "STAT_WRONG_PASSWORD", None): "STAT_WRONG_PASSWORD",
    }
    return status_map.get(status_code, str(status_code))

def _get_wlan():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return wlan

def connect(ssid=None, password=None, timeout=None):
    wlan = _get_wlan()
    target_ssid = ssid or config.ssid
    target_password = password or config.password
    connect_timeout = timeout if timeout is not None else getattr(config, "wifi_connect_timeout", 20)

    if wlan.isconnected():
        print("Already connected to Wi-Fi:", wlan.ifconfig())
        return True

    print("Connecting to network {}...".format(target_ssid))
    wlan.connect(target_ssid, target_password)

    start_time = time.time()
    last_status = None
    while not wlan.isconnected():
        current_status = wlan.status()
        if current_status != last_status:
            print("Wi-Fi status:", _status_name(current_status))
            last_status = current_status

        if time.time() - start_time > connect_timeout:
            raise OSError(
                "Wi-Fi connection timeout for SSID '{}' (status={})".format(
                    target_ssid,
                    _status_name(wlan.status()),
                )
            )
        time.sleep(0.1)

    print("Connected to Wi-Fi:", wlan.ifconfig())
    return True


def do_connect():
    return connect()


def disconnect():
    wlan = _get_wlan()
    if wlan.isconnected():
        print("Disconnecting from Wi-Fi...")
        wlan.disconnect()
        time.sleep(1)
        if wlan.isconnected():
            print("Disconnect failed, resetting device.")
            machine.reset()
        else:
            print("Wi-Fi disconnected.")
    else:
        print("Not connected to Wi-Fi.")


def is_connected():
    return _get_wlan().isconnected()


def get_ip_address():
    wlan = _get_wlan()
    if wlan.isconnected():
        return wlan.ifconfig()[0]
    return None


def get_signal_strength():
    wlan = _get_wlan()
    if wlan.isconnected():
        return wlan.status("rssi")
    return None


def get_mac_address():
    wlan = _get_wlan()
    if wlan.isconnected():
        return wlan.config("mac")
    return None


def _build_network_info(include_mac=False):
    wlan = _get_wlan()
    if not wlan.isconnected():
        return None

    info = {
        "ssid": wlan.config("essid"),
        "ip": wlan.ifconfig()[0],
        "subnet": wlan.ifconfig()[1],
        "gateway": wlan.ifconfig()[2],
        "dns": wlan.ifconfig()[3],
    }
    if include_mac:
        info["mac"] = wlan.config("mac")
        info["signal_strength"] = wlan.status("rssi")
    return info


def get_network_status():
    wlan = _get_wlan()
    if wlan.isconnected():
        return {
            "status": "connected",
            "ip": wlan.ifconfig()[0],
            "signal_strength": wlan.status("rssi"),
        }
    return {"status": "disconnected"}


def get_wifi_info():
    return _build_network_info(include_mac=True)


def get_network_info():
    return _build_network_info(include_mac=False)


def scan_networks():
    wlan = _get_wlan()
    networks = wlan.scan()
    return [{"ssid": net[0].decode("utf-8"), "rssi": net[3]} for net in networks]
