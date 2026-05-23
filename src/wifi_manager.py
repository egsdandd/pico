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
    # Use the WLAN interface but avoid forcing a re-init if already active.
    wlan = network.WLAN(network.STA_IF)
    activated_here = False
    if not wlan.active():
        wlan.active(True)
        activated_here = True
        time.sleep_ms(150)  # allow radio firmware to initialize
    target_ssid = ssid or config.ssid
    target_password = password or config.password
    connect_timeout = timeout if timeout is not None else getattr(config, "wifi_connect_timeout", 20)

    if wlan.isconnected():
        return True

    try:
        wlan.connect(target_ssid, target_password)

        start_time = time.time()
        while not wlan.isconnected():
            current_status = wlan.status()

            # If we get a definitive immediate failure, abort early
            if current_status in (getattr(network, "STAT_WRONG_PASSWORD", None),
                                  getattr(network, "STAT_NO_AP_FOUND", None),
                                  getattr(network, "STAT_CONNECT_FAIL", None)):
                raise OSError("Wi-Fi connect failed (status={})".format(_status_name(current_status)))

            if time.time() - start_time > connect_timeout:
                raise OSError(
                    "Wi-Fi connection timeout for SSID '{}' (status={})".format(
                        target_ssid,
                        _status_name(wlan.status()),
                    )
                )
            time.sleep(0.25)

    except Exception:
        # If we activated the radio for this attempt, try to power it down to leave hardware in a clean state
        try:
            if activated_here:
                wlan.active(False)
                time.sleep_ms(50)
        except Exception:
            pass
        raise

    print("Connected to Wi-Fi:", wlan.ifconfig())
    return True


def do_connect():
    return connect()


def disconnect():
    wlan = _get_wlan()
    if wlan.isconnected():
        print("Disconnecting from Wi-Fi...")
        try:
            wlan.disconnect()
        except Exception as exc:
            print("Error during wlan.disconnect():", exc)
        time.sleep(1)
        if wlan.isconnected():
            # Try a gentler recovery: attempt to deactivate the radio and log the failure.
            print("Disconnect failed; attempting to power down radio instead of resetting.")
            try:
                wlan.active(False)
                time.sleep_ms(50)
            except Exception as exc:
                print("Failed to deactivate radio:", exc)
            if wlan.isconnected():
                print("Still connected after deactivate attempt.")
                return False
            else:
                print("Radio deactivated; treated as disconnected.")
                return True
        else:
            print("Wi-Fi disconnected.")
            return True
    else:
        print("Not connected to Wi-Fi.")
        return False


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
