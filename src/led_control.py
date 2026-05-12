from machine import Pin


_led_pin = None


def get_led_pin():
    global _led_pin
    if _led_pin is None:
        try:
            _led_pin = Pin("LED", Pin.OUT)
        except Exception:
            _led_pin = Pin(25, Pin.OUT)
    return _led_pin


def turn_on():
    """Turn on the LED."""
    pin = get_led_pin()
    pin.on()


def turn_off():
    """Turn off the LED."""
    pin = get_led_pin()
    pin.off()


def toggle():
    """Toggle the LED state."""
    pin = get_led_pin()
    pin.toggle()
