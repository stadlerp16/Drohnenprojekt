import time
import Services.drohneService as ds

_state = {
    "forward": 0,  # b
    "right": 0,    # a
    "up": 0,       # c
    "yaw": 0       # d  <-- NEU
}

YAW_SPEED = 40
MOVE_SPEED = 40
UP_SPEED = 40

_airborne = False
_last_space_ts = 0.0
_SPACE_DEBOUNCE_S = 0.35

# NEU: blockiert RC während takeoff/land läuft
_in_transition = False


def _apply_rc():
    if ds.ep_drone is None:
        return

    # NEU: während Transition immer 0 senden
    if _in_transition or not _airborne:
        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        return

    ds.ep_drone.flight.rc(
        a=_state["right"],
        b=_state["forward"],
        c=_state["up"],
        d=_state["yaw"]  # <-- NEU
    )


def set_key(key: str, pressed: bool):
    if key == "w":
        _state["forward"] = MOVE_SPEED if pressed else 0
    elif key == "s":
        _state["forward"] = -MOVE_SPEED if pressed else 0
    elif key == "a":
        _state["right"] = -MOVE_SPEED if pressed else 0
    elif key == "d":
        _state["right"] = MOVE_SPEED if pressed else 0
    elif key in ("ArrowUp", "up"):
        _state["up"] = UP_SPEED if pressed else 0
    elif key in ("ArrowDown", "down"):
        _state["up"] = -UP_SPEED if pressed else 0
    elif key in ("ArrowLeft", "left"):
        _state["yaw"] = -YAW_SPEED if pressed else 0
    elif key in ("ArrowRight", "right"):
        _state["yaw"] = YAW_SPEED if pressed else 0



def toggle_takeoff_land():
    global _airborne, _last_space_ts, _in_transition

    if ds.ep_drone is None:
        return False

    # NEU: wenn bereits takeoff/land läuft -> ignorieren
    if _in_transition:
        return True

    now = time.time()
    if now - _last_space_ts < _SPACE_DEBOUNCE_S:
        return True
    _last_space_ts = now

    _in_transition = True
    try:
        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)

        if not _airborne:
            ds.ep_drone.flight.takeoff().wait_for_completed()
            _airborne = True
        else:
            ds.ep_drone.flight.land().wait_for_completed()
            _airborne = False

        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        return True

    except Exception:
        _airborne = False
        try:
            ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        except Exception:
            pass
        return False

    finally:
        _in_transition = False


def stop_all():
    _state["forward"] = 0
    _state["right"] = 0
    _state["up"] = 0
    _state["yaw"] = 0
    _apply_rc()



async def control_loop(stop_event, hz: int = 20):
    import asyncio
    dt = 1.0 / hz
    while not stop_event.is_set():
        _apply_rc()
        await asyncio.sleep(dt)
