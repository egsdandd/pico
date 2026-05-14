import machine
import ntptime
import struct
from . import config
from time import localtime, mktime

try:
    import usocket as socket
except ImportError:
    import socket


def _format_time_tuple(value):
    year, month, day, hour, minute, second, _, _ = value
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def _rtc_datetime_to_epoch(value):
    year, month, day, weekday, hour, minute, second, _ = value
    return mktime((year, month, day, hour, minute, second, weekday, 0))


def format_local_time(timestamp, timezone_offset=0):
    local_timestamp = timestamp + (timezone_offset * 3600)
    return _format_time_tuple(localtime(local_timestamp))


def sync_ntp_utc_time(timezone_offset=0):
    """Sync RTC from NTP in UTC and optionally print a local display time."""
    try:
        print("Synchronizing time with NTP server...")
        ntp_host = getattr(config, "ntp_host", None)
        ntp_timeout = getattr(config, "ntp_timeout", 3)

        if ntp_host:
            # Use explicit UDP NTP query with timeout to avoid blocking forever.
            _set_time_via_udp_ntp(ntp_host, ntp_timeout)
        else:
            # Keep backward-compatible behavior if no host override is configured.
            ntptime.settime()
        rtc = machine.RTC()
        rtc_datetime = rtc.datetime()
        print(
            "Current time UTC:",
            _format_time_tuple(
                (
                    rtc_datetime[0],
                    rtc_datetime[1],
                    rtc_datetime[2],
                    rtc_datetime[4],
                    rtc_datetime[5],
                    rtc_datetime[6],
                    0,
                    0,
                )
            ),
        )

        if timezone_offset:
            timestamp = _rtc_datetime_to_epoch(rtc_datetime)
            print("Current time local (display only):", format_local_time(timestamp, timezone_offset))

        return True
    except Exception as exc:
        print("Failed to synchronize time:", exc)
        return False


def _set_time_via_udp_ntp(host, timeout_s=3):
    # NTP timestamp starts at 1900-01-01
    ntp_delta = 2208988800
    query = bytearray(48)
    query[0] = 0x1B

    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if hasattr(s, "settimeout"):
            s.settimeout(timeout_s)
        s.sendto(query, addr)
        msg = s.recv(48)
    finally:
        try:
            s.close()
        except Exception:
            pass

    if not msg or len(msg) < 48:
        raise OSError("Invalid NTP response")

    seconds = struct.unpack("!I", msg[40:44])[0] - ntp_delta
    tm = localtime(seconds)
    # RTC format: (year, month, day, weekday, hour, minute, second, subseconds)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))