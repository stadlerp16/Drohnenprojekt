from __future__ import annotations

import math
import asyncio
from datetime import datetime
import Services.DrohneVerwaltung.drohneService as drohne_service

# --- Globaler Flug-Status ---
is_logging_allowed = False
current_flight_start = None
last_completed_flight = {"start": None, "end": None}
current_pos = {"x": 0, "y": 0}
route_history = [{"x": 0, "y": 0}]
total_distance_cm = 0.0

_last_telemetry_time: datetime | None = None


def reset_tracking():
    global current_pos, route_history, total_distance_cm, _last_telemetry_time
    current_pos = {"x": 0, "y": 0}
    route_history = [{"x": 0, "y": 0}]
    total_distance_cm = 0.0
    _last_telemetry_time = None


def _safe_get_status(drone, key: str, default=0):
    try:
        value = drone.get_status(key)
        return value if value is not None else default
    except Exception:
        return default


def get_height(drone) -> float:
    tof = _safe_get_status(drone, "tof", 0)
    return tof


def get_velocity_cm_s(drone):
    """
    Deine Messung wirkt so, als würden vgx/vgy/vgz in dm/s kommen.
    Darum: RAW-Wert * 10 = cm/s.
    """
    vgx_raw = _safe_get_status(drone, "vgx", 0)
    vgy_raw = _safe_get_status(drone, "vgy", 0)
    vgz_raw = _safe_get_status(drone, "vgz", 0)

    vgx = vgx_raw * 10
    vgy = vgy_raw * 10
    vgz = vgz_raw * 10

    speed = math.sqrt(vgx ** 2 + vgy ** 2 + vgz ** 2)

    return vgx, vgy, vgz, round(speed, 2)


def _update_distance(new_x, new_y):
    global total_distance_cm, current_pos

    dx = new_x - current_pos["x"]
    dy = new_y - current_pos["y"]
    dist = math.sqrt(dx ** 2 + dy ** 2)

    total_distance_cm += dist
    current_pos = {"x": new_x, "y": new_y}

    new_p = {"x": round(new_x, 1), "y": round(new_y, 1)}

    if route_history[-1] != new_p:
        route_history.append(new_p)


def _integrate_velocity(vgx: float, vgy: float, vgz: float) -> float:
    global _last_telemetry_time, total_distance_cm, current_pos, route_history

    now = datetime.now()

    if _last_telemetry_time is None or not is_logging_allowed:
        _last_telemetry_time = now
        return 0.0

    dt = (now - _last_telemetry_time).total_seconds()
    _last_telemetry_time = now

    if dt <= 0 or dt > 1.0:
        return 0.0

    speed = math.sqrt(vgx ** 2 + vgy ** 2 + vgz ** 2)

    if speed < 2.0:
        return 0.0

    delta_dist = speed * dt
    total_distance_cm += delta_dist

    new_x = current_pos["x"] + vgx * dt
    new_y = current_pos["y"] + vgy * dt

    current_pos = {"x": round(new_x, 1), "y": round(new_y, 1)}

    new_p = {"x": round(new_x, 1), "y": round(new_y, 1)}

    if route_history[-1] != new_p:
        route_history.append(new_p)

    return delta_dist


def update_position_keyboard(key: str, duration: float):
    px_per_sec = 40

    new_x = current_pos["x"]
    new_y = current_pos["y"]

    if key == "w":
        new_y -= px_per_sec * duration
    elif key == "s":
        new_y += px_per_sec * duration
    elif key == "a":
        new_x -= px_per_sec * duration
    elif key == "d":
        new_x += px_per_sec * duration

    _update_distance(new_x, new_y)


def update_position_analog(lx: float, ly: float):
    px_per_frame = 2

    new_x = current_pos["x"] + (lx * px_per_frame)
    new_y = current_pos["y"] - (ly * px_per_frame)

    _update_distance(new_x, new_y)


async def start_takeoff_timer(duration: float = 2.0):
    global is_logging_allowed

    is_logging_allowed = False
    await asyncio.sleep(duration)
    is_logging_allowed = True


def get_telemetry() -> dict:
    drone = drohne_service.ep_drone

    dur = round((datetime.now() - current_flight_start).total_seconds(), 1) if current_flight_start else 0.0

    battery = 0
    height = 0
    speed = 0
    pitch = 0
    roll = 0
    yaw = 0

    vgx = vgy = vgz = 0

    if drone:
        battery = _safe_get_status(drone, "bat", 0)

        tof = _safe_get_status(drone, "tof", 0)

        # Höhe: TOF bevorzugen, sonst h
        if tof > 0:
            height = tof

        # Geschwindigkeit
        vgx_raw = _safe_get_status(drone, "vgx", 0)
        vgy_raw = _safe_get_status(drone, "vgy", 0)
        vgz_raw = _safe_get_status(drone, "vgz", 0)

        # falls deine Werte dm/s sind:
        vgx = vgx_raw * 10
        vgy = vgy_raw * 10
        vgz = vgz_raw * 10

        speed = round(math.sqrt(vgx ** 2 + vgy ** 2 + vgz ** 2), 2)

        _integrate_velocity(vgx, vgy, vgz)

        pitch = _safe_get_status(drone, "pitch", 0)
        roll = _safe_get_status(drone, "roll", 0)
        yaw = _safe_get_status(drone, "yaw", 0)

    return {
        "connected": drone is not None,
        "is_logging": is_logging_allowed,

        # genau passend zu deinem Frontend
        "battery": battery,
        "current_height": height,
        "speed": speed,
        "pitch": pitch,
        "roll": roll,
        "yaw": yaw,
        "total_distance_cm": round(total_distance_cm, 1),
        "flight_duration": dur,

        # Zusatzwerte zum Prüfen
        "position": current_pos,
        "path": route_history,
    }


def set_matrix_string(matrix_str: str) -> bool:
    if drohne_service.ep_drone is None:
        print("[LED-Matrix] Drohne nicht verbunden")
        return False

    if not matrix_str or len(matrix_str) != 64:
        print("[LED-Matrix] Ungültiger String: muss genau 64 Zeichen haben")
        return False

    try:
        drohne_service.ep_drone.led.set_mled_graph(matrix_str)
        print("[LED-Matrix] String direkt gesetzt")
        return True
    except Exception as e:
        print(f"[LED-Matrix] Fehler: {e}")
        return False


def set_matrix_text(text: str, color: str = "r", scroll: bool = True) -> bool:
    if drohne_service.ep_drone is None:
        print("[LED-Matrix] Drohne nicht verbunden")
        return False

    if color not in ["r", "b", "p"]:
        color = "r"

    try:
        drohne_service.ep_drone.led.set_mled_bright(255)

        if scroll:
            drohne_service.ep_drone.led.set_mled_char_scroll(
                direction="l",
                color=color,
                freq=1.5,
                display_str=text
            )
            print(f"[LED-Matrix] Scroll-Text gesetzt: {text}")
        else:
            text = text[:1]
            drohne_service.ep_drone.led.set_mled_char(color, text)
            print(f"[LED-Matrix] Text gesetzt: {text}")

        return True

    except Exception as e:
        print(f"[LED-Matrix] Fehler: {e}")
        return False

