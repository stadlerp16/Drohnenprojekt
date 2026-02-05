
import time
import Services.drohneService as ds

_state = {
    "forward": 0,  # b
    "right": 0,    # a
    "up": 0,       # c
}

MOVE_SPEED = 40
UP_SPEED = 40

# interner Flugzustand
_airborne = False
_last_space_ts = 0.0
_SPACE_DEBOUNCE_S = 0.35


def _apply_rc():
    """
    RC an die Drohne:
    flight.rc(a=right, b=forward, c=up, d=yaw)
    """
    if ds.ep_drone is None:
        return

    # Wenn noch nicht abgehoben, keine Bewegung schicken (optional, aber sauber)
    if not _airborne:
        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        return

    ds.ep_drone.flight.rc(
        a=_state["right"],
        b=_state["forward"],
        c=_state["up"],
        d=0
    )


def set_key(key: str, pressed: bool):
    """
    key (Web): 'w','s','a','d','ArrowUp','ArrowDown' (+ optional Varianten)
    pressed: True bei keydown, False bei keyup
    """
    # Vor/Zurück
    if key == "w":
        _state["forward"] = MOVE_SPEED if pressed else 0
    elif key == "s":
        _state["forward"] = -MOVE_SPEED if pressed else 0

    # Links/Rechts (Strafe)
    elif key == "a":
        _state["right"] = -MOVE_SPEED if pressed else 0
    elif key == "d":
        _state["right"] = MOVE_SPEED if pressed else 0

    # Höhe
    elif key in ("ArrowUp", "up"):
        _state["up"] = UP_SPEED if pressed else 0
    elif key in ("ArrowDown", "down"):
        _state["up"] = -UP_SPEED if pressed else 0


def toggle_takeoff_land():
    """
    Leertaste: wenn am Boden -> Takeoff, wenn in der Luft -> Land
    (Debounce, damit es nicht mehrmals triggert)
    """
    global _airborne, _last_space_ts

    if ds.ep_drone is None:
        return False

    now = time.time()
    if now - _last_space_ts < _SPACE_DEBOUNCE_S:
        return True  # ignorieren, aber nicht als Fehler zählen
    _last_space_ts = now

    try:
        # vor jeder Aktion: RC stoppen
        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)

        if not _airborne:
            ds.ep_drone.flight.takeoff().wait_for_completed()
            _airborne = True
        else:
            ds.ep_drone.flight.land().wait_for_completed()
            _airborne = False

        return True
    except Exception:
        # falls was schiefgeht: Zustand konservativ auf "nicht airborne"
        _airborne = False
        try:
            ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        except Exception:
            pass
        return False


def stop_all():
    _state["forward"] = 0
    _state["right"] = 0
    _state["up"] = 0
    _apply_rc()


async def control_loop(stop_event, hz: int = 20):
    import asyncio
    dt = 1.0 / hz
    while not stop_event.is_set():
        _apply_rc()
        await asyncio.sleep(dt)
