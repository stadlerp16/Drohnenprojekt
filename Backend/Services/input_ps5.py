from Services.flightExekutor import set_rc

MOVE_SPEED = 40
UP_SPEED = 40
YAW_SPEED = 40
DEADZONE = 0.08

def dz(v: float, d: float = DEADZONE) -> float:
    return 0.0 if abs(v) < d else v

def set_gamepad(lx: float, ly: float, rx: float, l2: float, r2: float):

    lx = dz(lx)
    ly = dz(ly)
    rx = dz(rx)
    up = dz(r2 - l2)

    a = int(lx * MOVE_SPEED)
    b = int(-ly * MOVE_SPEED)
    c = int(up * UP_SPEED)
    d = int(rx * YAW_SPEED)

    set_rc(a, b, c, d)
