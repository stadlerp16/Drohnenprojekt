
import asyncio
import Services.drohneService as ds

# Aktueller RC-Zustand
_state = {
    "forward": 0,  # b
    "right": 0,    # a
}

MOVE_SPEED = 40   # kannst du anpassen (0..100)

def _apply_rc():
    """
    Sendet RC an die Drohne (wie in deinem Script):
    flight.rc(a=right, b=forward, c=up, d=yaw)
    """
    if ds.ep_drone is None:
        return

    ds.ep_drone.flight.rc(
        a=_state["right"],
        b=_state["forward"],
        c=0,
        d=0
    )

def set_key(key: str, pressed: bool):
    """
    key: 'w','s','a','d'
    pressed: True bei keydown, False bei keyup
    """
    if key == "w":
        _state["forward"] = MOVE_SPEED if pressed else 0
    elif key == "s":
        _state["forward"] = -MOVE_SPEED if pressed else 0
    elif key == "a":
        _state["right"] = -MOVE_SPEED if pressed else 0
    elif key == "d":
        _state["right"] = MOVE_SPEED if pressed else 0

def stop_all():
    _state["forward"] = 0
    _state["right"] = 0
    _apply_rc()

async def control_loop(stop_event: asyncio.Event, hz: int = 20):

    dt = 1.0 / hz
    while not stop_event.is_set():
        _apply_rc()
        await asyncio.sleep(dt)
