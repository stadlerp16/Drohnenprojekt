from Services.flightExekutor import set_rc

MOVE_SPEED = 40
UP_SPEED = 40
YAW_SPEED = 40
DEADZONE = 0.08


def dz(v: float, d: float = DEADZONE) -> float:
    return 0.0 if abs(v) < d else v


def clamp_int(x: float, mn: int, mx: int) -> int:
    xi = int(x)
    return mn if xi < mn else mx if xi > mx else xi


def set_touch(lx: float, ly: float, rx: float, ry: float):

    lx = dz(lx)
    ly = dz(ly)
    rx = dz(rx)
    ry = dz(ry)

    a = rx * MOVE_SPEED

    b = -ry * MOVE_SPEED

    c = -ly * UP_SPEED

    d = lx * YAW_SPEED

    set_rc(
        clamp_int(a, -100, 100),
        clamp_int(b, -100, 100),
        clamp_int(c, -100, 100),
        clamp_int(d, -100, 100),
    )
