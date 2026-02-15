from Services.flightExekutor import set_rc

MOVE_SPEED = 40
UP_SPEED = 40
YAW_SPEED = 40

# interner Keyboard-State
_k = {"a": 0, "b": 0, "c": 0, "d": 0}


def set_key(key: str, pressed: bool):
    if key == "w":
        _k["b"] = MOVE_SPEED if pressed else 0
    elif key == "s":
        _k["b"] = -MOVE_SPEED if pressed else 0

    elif key == "a":
        _k["a"] = -MOVE_SPEED if pressed else 0
    elif key == "d":
        _k["a"] = MOVE_SPEED if pressed else 0

    elif key in ("ArrowUp", "up"):
        _k["c"] = UP_SPEED if pressed else 0
    elif key in ("ArrowDown", "down"):
        _k["c"] = -UP_SPEED if pressed else 0

    elif key in ("ArrowLeft", "left"):
        _k["d"] = -YAW_SPEED if pressed else 0
    elif key in ("ArrowRight", "right"):
        _k["d"] = YAW_SPEED if pressed else 0

    set_rc(_k["a"], _k["b"], _k["c"], _k["d"])
