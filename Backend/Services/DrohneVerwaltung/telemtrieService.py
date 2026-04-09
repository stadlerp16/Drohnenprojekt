import math
import Services.DrohneVerwaltung.drohneService as drohne_service
from typing import List

def get_telemetry() -> dict:
    drone = drohne_service.ep_drone
    current_drone_ip = drohne_service.current_drone_ip

    if drone is None:
        return {
            "connected": False,
            "ip": None,
            "battery": None,
            "height": None,
            "speed": None,
            "pitch": None,
            "roll": None,
            "yaw": None,
            "error": "Keine Drohne verbunden"
        }

    def safe_status(name: str, default=None):
        try:
            return drone.get_status(name=name)
        except Exception as e:
            print(f"[Telemetry] Fehler bei {name}: {e}")
            return default

    battery = safe_status("bat")
    height = safe_status("h")

    pitch = safe_status("pitch")
    roll = safe_status("roll")
    yaw = safe_status("yaw")

    vgx = safe_status("vgx", 0)
    vgy = safe_status("vgy", 0)
    vgz = safe_status("vgz", 0)

    try:
        speed = round(math.sqrt((vgx or 0) ** 2 + (vgy or 0) ** 2 + (vgz or 0) ** 2), 2)
    except Exception:
        speed = None

    return {
        "connected": True,
        "ip": current_drone_ip,
        "battery": battery,
        "height": height,
        "speed": speed,
        "pitch": pitch,
        "roll": roll,
        "yaw": yaw,
        "vgx": vgx,
        "vgy": vgy,
        "vgz": vgz
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