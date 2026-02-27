import time
import Services.drohneService as ds

# RC Werte: a=right/strafe, b=forward, c=up, d=yaw
_state = {"a": 0, "b": 0, "c": 0, "d": 0}

_airborne = False
_in_transition = False
_last_toggle_ts = 0.0
_TOGGLE_DEBOUNCE_S = 0.35


def set_rc(a: int, b: int, c: int, d: int):
    _state["a"] = int(a)
    _state["b"] = int(b)
    _state["c"] = int(c)
    _state["d"] = int(d)


def _apply_rc():
    if ds.ep_drone is None:
        return

    if _in_transition or not _airborne:
        ds.ep_drone.flight.rc(a=0, b=0, c=0, d=0)
        return

    ds.ep_drone.flight.rc(
        a=_state["a"],
        b=_state["b"],
        c=_state["c"],
        d=_state["d"],
    )


def stop_all():
    set_rc(0, 0, 0, 0)
    _apply_rc()


def toggle_takeoff_land() -> bool:
    global _airborne, _in_transition, _last_toggle_ts

    if ds.ep_drone is None:
        return False

    if _in_transition:
        return True

    now = time.time()
    if now - _last_toggle_ts < _TOGGLE_DEBOUNCE_S:
        return True
    _last_toggle_ts = now

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


async def control_loop(stop_event, hz: int = 20):
    import asyncio
    dt = 1.0 / hz
    while not stop_event.is_set():
        _apply_rc()
        await asyncio.sleep(dt)
