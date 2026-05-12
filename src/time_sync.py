import machine
import ntptime
from time import localtime, mktime


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