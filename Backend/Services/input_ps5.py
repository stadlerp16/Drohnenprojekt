from Services.flightExekutor import set_rc

MOVE_SPEED = 40
UP_SPEED = 40
YAW_SPEED = 40
DEADZONE = 0.08

def dz(v: float, d: float = DEADZONE) -> float:
    return 0.0 if abs(v) < d else v


def set_gamepad(lx: float = 0.0, ly: float = 0.0, rx: float = 0.0, l2: float = 0.0, r2: float = 0.0, **kwargs):
    # 1. Die Standardwerte (= 0.0) sorgen dafür, dass kein Fehler kommt, wenn ein Wert fehlt.
    # 2. Das **kwargs fängt alle extra Werte (wie 'ry') ab, damit es keinen Absturz gibt.

    lx = dz(lx)
    ly = dz(ly)
    rx = dz(rx)

    # r2 und l2 sind jetzt sicher vorhanden (entweder vom Controller oder als 0.0)
    up = dz(r2 - l2)

    a = int(lx * MOVE_SPEED)
    b = int(-ly * MOVE_SPEED)
    c = int(up * UP_SPEED)
    d = int(rx * YAW_SPEED)

    # Optional: Debug-Print um zu sehen, was ankommt
    # print(f"RC-Werte gesetzt: a={a}, b={b}, c={c}, d={d}")

    set_rc(a, b, c, d)