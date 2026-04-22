from __future__ import annotations

import math
import asyncio
from datetime import datetime
import Services.DrohneVerwaltung.drohneService as drohne_service
from typing import List

# --- Globaler Flug-Status ---
is_logging_allowed = False
current_flight_start = None
last_completed_flight = {"start": None, "end": None}
current_pos = {"x": 0, "y": 0}
route_history = [{"x": 0, "y": 0}]
total_distance_cm = 0.0

# Für zeitbasierte Geschwindigkeitsintegration
_last_telemetry_time: datetime | None = None


def reset_tracking():
    global current_pos, route_history, total_distance_cm, _last_telemetry_time
    current_pos = {"x": 0, "y": 0}
    route_history = [{"x": 0, "y": 0}]
    total_distance_cm = 0.0
    _last_telemetry_time = None


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
    """
    Berechnet die zurückgelegte Strecke seit dem letzten Aufruf
    anhand der echten Geschwindigkeitsvektoren (cm/s) × Δt (s).
    Gibt die Delta-Distanz in cm zurück.
    """
    global _last_telemetry_time, total_distance_cm, current_pos, route_history

    now = datetime.now()

    if _last_telemetry_time is None or not is_logging_allowed:
        _last_telemetry_time = now
        return 0.0

    dt = (now - _last_telemetry_time).total_seconds()
    _last_telemetry_time = now

    # Plausibilitätsprüfung: zu große Zeitlücken ignorieren (z. B. nach Pause)
    if dt <= 0 or dt > 1.0:
        return 0.0

    # 3D-Distanz: sqrt(vx² + vy² + vz²) × Δt
    speed = round(math.sqrt((vgx or 0)**2 + (vgy or 0)**2 + (vgz or 0)**2) / 10, 2)
    delta_dist = speed * dt

    # Schwellwert: Rauschen unter 2 cm/s ignorieren
    if speed < 2.0:
        return 0.0

    total_distance_cm += delta_dist

    # Position in 2D (x/y) ebenfalls integrieren für Pfad-Tracking
    new_x = current_pos["x"] + vgx * dt
    new_y = current_pos["y"] + vgy * dt
    current_pos = {"x": round(new_x, 1), "y": round(new_y, 1)}
    new_p = {"x": round(new_x, 1), "y": round(new_y, 1)}
    if route_history[-1] != new_p:
        route_history.append(new_p)

    return delta_dist


def update_position_keyboard(key: str, duration: float):
    """Fallback für Keyboard-Steuerung ohne echte Velocity-Daten."""
    px_per_sec = 40
    new_x, new_y = current_pos["x"], current_pos["y"]
    if key in ["w"]:
        new_y -= px_per_sec * duration
    elif key in ["s"]:
        new_y += px_per_sec * duration
    elif key in ["a"]:
        new_x -= px_per_sec * duration
    elif key in ["d"]:
        new_x += px_per_sec * duration
    _update_distance(new_x, new_y)


def update_position_analog(lx: float, ly: float):
    """Fallback für Analog-Steuerung ohne echte Velocity-Daten."""
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
    global _last_telemetry_time
    drone = drohne_service.ep_drone
    dur = round((datetime.now() - current_flight_start).total_seconds(), 1) if current_flight_start else 0.0

    current_height = 0
    vgx, vgy, vgz = 0, 0, 0

    if drone:
        try:
            current_height = drone.get_status(name="h") or 0
            vgx = drone.get_status("vgx") or 0
            vgy = drone.get_status("vgy") or 0
            vgz = drone.get_status("vgz") or 0

            # Distanz aus echten Velocity-Daten integrieren
            _integrate_velocity(vgx, vgy, vgz)
        except:
            pass

    data = {
        "connected": drone is not None,
        "is_logging": is_logging_allowed,
        "flight_duration": dur,
        "total_distance_cm": round(total_distance_cm, 1),
        "height_cm": current_height,
        "position": current_pos,
        "path": route_history,
    }

    vgx = safe_status("vgx", 0)
    vgy = safe_status("vgy", 0)
    vgz = safe_status("vgz", 0)

    try:
        speed = round(math.sqrt((vgx or 0) ** 2 + (vgy or 0) ** 2 + (vgz or 0) ** 2), 2)
    except Exception:
        speed = None
    if drone:
        try:
            data.update({
                "battery": drone.get_status(name="bat"),
                "speed": round(math.sqrt((vgx or 0)**2 + (vgy or 0)**2 + (vgz or 0)**2) / 10, 2),
                "pitch": drone.get_status(name="pitch"),
                "roll": drone.get_status(name="roll"),
                "yaw": drone.get_status(name="yaw"),
            })
        except:
            pass

    return data


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
                direction='l',
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